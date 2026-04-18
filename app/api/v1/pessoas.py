"""Router de CRUD de Pessoas com busca fuzzy e CPF criptografado.

Fornece endpoints para criação, listagem, detalhe, atualização e
soft delete de pessoas, além de adição de endereços. Implementa
busca fuzzy por nome (pg_trgm) e busca por CPF (hash SHA-256).
"""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user, get_current_user_with_guarnicao
from app.models.usuario import Usuario
from app.schemas.abordagem import AbordagemDetail, VeiculoAbordagemRead
from app.schemas.pessoa import (
    EnderecoCreate,
    EnderecoRead,
    EnderecoUpdate,
    PessoaCreate,
    PessoaDetail,
    PessoaRead,
    PessoaUpdate,
    VinculoRead,
)
from app.schemas.pessoa_observacao import (
    PessoaObservacaoCreate,
    PessoaObservacaoRead,
    PessoaObservacaoUpdate,
)
from app.schemas.veiculo import VeiculoRead
from app.schemas.vinculo_manual import VinculoManualCreate, VinculoManualRead
from app.services.abordagem_service import AbordagemService
from app.services.audit_service import AuditService
from app.services.pessoa_observacao_service import PessoaObservacaoService
from app.services.pessoa_service import PessoaService

router = APIRouter(prefix="/pessoas", tags=["Pessoas"])


def _to_pessoa_read(pessoa, service: PessoaService) -> PessoaRead:
    """Converte model Pessoa para schema PessoaRead com CPF mascarado.

    Args:
        pessoa: Instância de Pessoa do banco.
        service: Instância de PessoaService para mascarar CPF.

    Returns:
        PessoaRead com cpf_masked preenchido.
    """
    return PessoaRead(
        id=pessoa.id,
        nome=pessoa.nome,
        cpf_masked=service.mask_cpf(pessoa),
        data_nascimento=pessoa.data_nascimento,
        apelido=pessoa.apelido,
        foto_principal_url=pessoa.foto_principal_url,
        observacoes=pessoa.observacoes,
        guarnicao_id=pessoa.guarnicao_id,
        criado_em=pessoa.criado_em,
        atualizado_em=pessoa.atualizado_em,
    )


@router.post("/", response_model=PessoaRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def criar_pessoa(
    request: Request,
    data: PessoaCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user_with_guarnicao),
) -> PessoaRead:
    """Cria nova pessoa com CPF criptografado.

    Cria registro de pessoa, criptografa CPF com Fernet (AES-256)
    e gera hash SHA-256 para buscas. Verifica unicidade de CPF.

    Args:
        request: Objeto Request do FastAPI.
        data: Dados de criação (nome, cpf, nascimento, apelido, observacoes).
        db: Sessão do banco de dados.
        user: Usuário autenticado com guarnição atribuída.

    Returns:
        PessoaRead com dados da pessoa criada.

    Raises:
        ConflitoDadosError: Se CPF já cadastrado na guarnição.

    Status Code:
        201: Pessoa criada com sucesso.
        403: Usuário sem guarnição.
        409: CPF duplicado.
        429: Rate limit (30/min).
    """
    service = PessoaService(db)
    pessoa = await service.criar(
        data,
        user_id=user.id,
        guarnicao_id=user.guarnicao_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_pessoa_read(pessoa, service)


@router.get("/", response_model=list[PessoaRead])
@limiter.limit("30/minute")
async def listar_pessoas(
    request: Request,
    nome: str | None = Query(None, description="Busca fuzzy por nome (pg_trgm)"),
    cpf: str | None = Query(None, description="Busca exata por CPF (hash SHA-256)"),
    apelido: str | None = Query(None, description="Busca por apelido"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[PessoaRead]:
    """Lista pessoas com filtros opcionais.

    Suporta busca fuzzy por nome (pg_trgm), busca exata por CPF
    via hash SHA-256, ou listagem paginada da guarnição.

    Args:
        request: Objeto Request do FastAPI.
        nome: Termo para busca fuzzy por nome.
        cpf: CPF para busca exata via hash.
        apelido: Apelido para busca.
        skip: Registros a pular (paginação).
        limit: Máximo de resultados (1-100).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de PessoaRead.
    """
    service = PessoaService(db)
    pessoas = await service.buscar(
        nome=nome, cpf=cpf, apelido=apelido, skip=skip, limit=limit, user=user
    )
    return [_to_pessoa_read(p, service) for p in pessoas]


@router.get("/{pessoa_id}", response_model=PessoaDetail)
@limiter.limit("30/minute")
async def detalhe_pessoa(
    request: Request,
    pessoa_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PessoaDetail:
    """Obtém detalhes completos de uma pessoa.

    Retorna pessoa com endereços, contagem de abordagens e
    vínculos com outras pessoas (eager loaded).

    Args:
        pessoa_id: ID da pessoa.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PessoaDetail com relacionamentos.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.
    """
    service = PessoaService(db)
    pessoa = await service.buscar_detalhe(pessoa_id, user)

    # Audit log — acesso a dados sensíveis (CPF descriptografado)
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="READ",
        recurso="pessoa",
        recurso_id=pessoa.id,
    )

    # Montar vínculos a partir de ambas direções de relacionamento
    vinculos = []
    for rel in pessoa.relacionamentos_como_a:
        vinculos.append(
            VinculoRead(
                pessoa_id=rel.pessoa_id_b,
                nome=rel.pessoa_b.nome if rel.pessoa_b else "",
                frequencia=rel.frequencia,
                ultima_vez=rel.ultima_vez,
                foto_principal_url=rel.pessoa_b.foto_principal_url if rel.pessoa_b else None,
            )
        )
    for rel in pessoa.relacionamentos_como_b:
        vinculos.append(
            VinculoRead(
                pessoa_id=rel.pessoa_id_a,
                nome=rel.pessoa_a.nome if rel.pessoa_a else "",
                frequencia=rel.frequencia,
                ultima_vez=rel.ultima_vez,
                foto_principal_url=rel.pessoa_a.foto_principal_url if rel.pessoa_a else None,
            )
        )

    # Carregar vínculos manuais
    vinculos_manuais_db = await service.listar_vinculos_manuais(pessoa_id, user)
    vinculos_manuais = [
        VinculoManualRead(
            id=vm.id,
            pessoa_vinculada_id=vm.pessoa_vinculada_id,
            nome=vm.pessoa_vinculada.nome if vm.pessoa_vinculada else "",
            foto_principal_url=vm.pessoa_vinculada.foto_principal_url
            if vm.pessoa_vinculada
            else None,
            tipo=vm.tipo,
            descricao=vm.descricao,
            criado_em=vm.criado_em,
        )
        for vm in vinculos_manuais_db
    ]

    return PessoaDetail(
        id=pessoa.id,
        nome=pessoa.nome,
        cpf_masked=service.mask_cpf(pessoa),
        cpf=service.decrypt_cpf(pessoa),
        data_nascimento=pessoa.data_nascimento,
        apelido=pessoa.apelido,
        foto_principal_url=pessoa.foto_principal_url,
        observacoes=pessoa.observacoes,
        guarnicao_id=pessoa.guarnicao_id,
        criado_em=pessoa.criado_em,
        atualizado_em=pessoa.atualizado_em,
        enderecos=[EnderecoRead.model_validate(e) for e in pessoa.enderecos],
        abordagens_count=len(pessoa.abordagens),
        relacionamentos=vinculos,
        vinculos_manuais=vinculos_manuais,
    )


@router.patch("/{pessoa_id}", response_model=PessoaRead)
@limiter.limit("30/minute")
async def atualizar_pessoa(
    request: Request,
    pessoa_id: int,
    data: PessoaUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PessoaRead:
    """Atualiza dados de uma pessoa existente.

    Permite atualização parcial (PATCH). Se CPF alterado, re-criptografa
    com Fernet e recalcula hash SHA-256.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa a atualizar.
        data: Dados de atualização parcial.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PessoaRead com dados atualizados.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.
        ConflitoDadosError: Se novo CPF já cadastrado.

    Status Code:
        200: Pessoa atualizada com sucesso.
        404: Pessoa não encontrada.
        409: CPF duplicado.
        429: Rate limit (30/min).
    """
    service = PessoaService(db)
    pessoa = await service.atualizar(
        pessoa_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="UPDATE",
        recurso="pessoa",
        recurso_id=pessoa.id,
        detalhes={"campos": [k for k, v in data.model_dump(exclude_unset=True).items()]},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return _to_pessoa_read(pessoa, service)


@router.delete("/{pessoa_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def deletar_pessoa(
    request: Request,
    pessoa_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Soft delete de pessoa (ativo=False).

    Marca a pessoa como inativa sem remoção física do banco.
    Registra auditoria da operação.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa a desativar.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.

    Status Code:
        204: Pessoa desativada com sucesso.
    """
    service = PessoaService(db)
    await service.desativar(pessoa_id, user)
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="DELETE",
        recurso="pessoa",
        recurso_id=pessoa_id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()


@router.post(
    "/{pessoa_id}/enderecos",
    response_model=EnderecoRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def adicionar_endereco(
    request: Request,
    pessoa_id: int,
    data: EnderecoCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> EnderecoRead:
    """Adiciona endereço a uma pessoa.

    Se latitude/longitude informadas, cria ponto PostGIS para
    análise geoespacial.

    Args:
        pessoa_id: ID da pessoa.
        data: Dados do endereço (texto, coordenadas, datas).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        EnderecoRead criado.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.

    Status Code:
        201: Endereço adicionado.
    """
    service = PessoaService(db)
    endereco = await service.adicionar_endereco(pessoa_id, data, user)
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="CREATE",
        recurso="endereco",
        recurso_id=endereco.id,
        detalhes={"pessoa_id": pessoa_id},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return EnderecoRead.model_validate(endereco)


@router.patch(
    "/{pessoa_id}/enderecos/{endereco_id}",
    response_model=EnderecoRead,
)
@limiter.limit("30/minute")
async def atualizar_endereco(
    request: Request,
    pessoa_id: int,
    endereco_id: int,
    data: EnderecoUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> EnderecoRead:
    """Atualiza endereço existente de uma pessoa.

    Permite atualização parcial de campos do endereço. Se coordenadas
    informadas, atualiza ponto PostGIS.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona do endereço.
        endereco_id: ID do endereço a atualizar.
        data: Dados de atualização parcial.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        EnderecoRead com dados atualizados.

    Raises:
        NaoEncontradoError: Se pessoa ou endereço não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.

    Status Code:
        200: Endereço atualizado.
        404: Pessoa ou endereço não encontrado.
        429: Rate limit (30/min).
    """
    service = PessoaService(db)
    endereco = await service.atualizar_endereco(
        pessoa_id,
        endereco_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="UPDATE",
        recurso="endereco",
        recurso_id=endereco_id,
        detalhes={"pessoa_id": pessoa_id},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return EnderecoRead.model_validate(endereco)


@router.get("/{pessoa_id}/abordagens", response_model=list[AbordagemDetail])
@limiter.limit("30/minute")
async def listar_abordagens_pessoa(
    request: Request,
    pessoa_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[AbordagemDetail]:
    """Lista abordagens de uma pessoa com detalhes completos.

    Retorna abordagens com pessoas e veículos vinculados,
    ordenadas por data/hora decrescente, com paginação.

    Args:
        pessoa_id: ID da pessoa.
        skip: Registros a pular (padrão 0).
        limit: Máximo de resultados (padrão 20, máx 100).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de AbordagemDetail com pessoas e veículos.
    """
    pessoa_service = PessoaService(db)
    abordagem_service = AbordagemService(db)

    all_abordagens = await abordagem_service.listar_por_pessoa(pessoa_id, user.guarnicao_id)
    abordagens = all_abordagens[skip : skip + limit]

    result = []
    for ab in abordagens:
        pessoas = []
        for ap in ab.pessoas:
            p = ap.pessoa
            pessoas.append(
                PessoaRead(
                    id=p.id,
                    nome=p.nome,
                    cpf_masked=pessoa_service.mask_cpf(p),
                    data_nascimento=p.data_nascimento,
                    apelido=p.apelido,
                    foto_principal_url=p.foto_principal_url,
                    observacoes=p.observacoes,
                    guarnicao_id=p.guarnicao_id,
                    criado_em=p.criado_em,
                    atualizado_em=p.atualizado_em,
                )
            )
        veiculos = [
            VeiculoAbordagemRead(
                **VeiculoRead.model_validate(av.veiculo).model_dump(),
                pessoa_id=av.pessoa_id,
            )
            for av in ab.veiculos
        ]
        result.append(
            AbordagemDetail(
                id=ab.id,
                data_hora=ab.data_hora,
                latitude=ab.latitude,
                longitude=ab.longitude,
                endereco_texto=ab.endereco_texto,
                observacao=ab.observacao,
                usuario_id=ab.usuario_id,
                guarnicao_id=ab.guarnicao_id,
                origem=ab.origem,
                criado_em=ab.criado_em,
                atualizado_em=ab.atualizado_em,
                pessoas=pessoas,
                veiculos=veiculos,
                fotos=[],
                passagens=[],
            )
        )
    return result


@router.post(
    "/{pessoa_id}/vinculos-manuais",
    response_model=VinculoManualRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def criar_vinculo_manual(
    request: Request,
    pessoa_id: int,
    data: VinculoManualCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> VinculoManualRead:
    """Cria vínculo manual entre duas pessoas.

    Permite registrar relacionamentos conhecidos operacionalmente
    que não constam em abordagens (ex: 'Irmão', 'Sócio').

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona do vínculo.
        data: Dados do vínculo (pessoa_vinculada_id, tipo, descricao).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        VinculoManualRead com dados do vínculo criado.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa vinculada é de outra guarnição.
        ConflitoDadosError: Se vínculo já cadastrado.

    Status Code:
        201: Vínculo criado.
        403: Acesso negado.
        404: Pessoa não encontrada.
        409: Vínculo duplicado.
        422: Dados inválidos (tipo ausente, etc).
        429: Rate limit.
    """
    service = PessoaService(db)
    vinculo = await service.criar_vinculo_manual(
        pessoa_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    vinculada = vinculo.pessoa_vinculada
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="CREATE",
        recurso="vinculo_manual",
        recurso_id=vinculo.id,
        detalhes={"pessoa_id": pessoa_id, "pessoa_vinculada_id": data.pessoa_vinculada_id},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return VinculoManualRead(
        id=vinculo.id,
        pessoa_vinculada_id=vinculo.pessoa_vinculada_id,
        nome=vinculada.nome if vinculada else "",
        foto_principal_url=vinculada.foto_principal_url if vinculada else None,
        tipo=vinculo.tipo,
        descricao=vinculo.descricao,
        criado_em=vinculo.criado_em,
    )


@router.delete(
    "/{pessoa_id}/vinculos-manuais/{vinculo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def remover_vinculo_manual(
    request: Request,
    pessoa_id: int,
    vinculo_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Remove vínculo manual (soft delete).

    Marca o vínculo como inativo sem remoção física. Registra auditoria.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona do vínculo.
        vinculo_id: ID do vínculo a remover.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Raises:
        NaoEncontradoError: Se vínculo não existe ou não pertence à guarnição.

    Status Code:
        204: Vínculo removido.
        404: Vínculo não encontrado.
    """
    service = PessoaService(db)
    await service.remover_vinculo_manual(
        vinculo_id,
        pessoa_id,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="DELETE",
        recurso="vinculo_manual",
        recurso_id=vinculo_id,
        detalhes={"pessoa_id": pessoa_id},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Observações da Pessoa
# ---------------------------------------------------------------------------


@router.get(
    "/{pessoa_id}/observacoes",
    response_model=list[PessoaObservacaoRead],
)
@limiter.limit("30/minute")
async def listar_observacoes(
    request: Request,
    pessoa_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[PessoaObservacaoRead]:
    """Lista observações ativas de uma pessoa, da mais recente para a mais antiga.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de PessoaObservacaoRead.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.
    """
    service = PessoaObservacaoService(db)
    observacoes = await service.listar(pessoa_id, user)
    return [PessoaObservacaoRead.model_validate(o) for o in observacoes]


@router.post(
    "/{pessoa_id}/observacoes",
    response_model=PessoaObservacaoRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def criar_observacao(
    request: Request,
    pessoa_id: int,
    data: PessoaObservacaoCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PessoaObservacaoRead:
    """Cria nova observação vinculada a uma pessoa.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa.
        data: Dados da observação (texto).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PessoaObservacaoRead com dados da observação criada.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.

    Status Code:
        201: Observação criada.
    """
    service = PessoaObservacaoService(db)
    obs = await service.criar(
        pessoa_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(obs)
    return PessoaObservacaoRead.model_validate(obs)


@router.patch(
    "/{pessoa_id}/observacoes/{obs_id}",
    response_model=PessoaObservacaoRead,
)
@limiter.limit("30/minute")
async def atualizar_observacao(
    request: Request,
    pessoa_id: int,
    obs_id: int,
    data: PessoaObservacaoUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PessoaObservacaoRead:
    """Atualiza o texto de uma observação existente.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona da observação.
        obs_id: ID da observação.
        data: Novo texto da observação.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PessoaObservacaoRead com texto atualizado.

    Raises:
        NaoEncontradoError: Se observação não existe.
        AcessoNegadoError: Se observação de outra guarnição.
    """
    service = PessoaObservacaoService(db)
    obs = await service.atualizar(
        obs_id,
        pessoa_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(obs)
    return PessoaObservacaoRead.model_validate(obs)


@router.delete(
    "/{pessoa_id}/observacoes/{obs_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def deletar_observacao(
    request: Request,
    pessoa_id: int,
    obs_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Soft delete de uma observação.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona da observação.
        obs_id: ID da observação.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Raises:
        NaoEncontradoError: Se observação não existe.
        AcessoNegadoError: Se observação de outra guarnição.

    Status Code:
        204: Observação removida.
    """
    service = PessoaObservacaoService(db)
    await service.deletar(
        obs_id,
        pessoa_id,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
