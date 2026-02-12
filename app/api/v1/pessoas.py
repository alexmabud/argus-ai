"""Router de CRUD de Pessoas com busca fuzzy e CPF criptografado.

Fornece endpoints para criação, listagem, detalhe, atualização e
soft delete de pessoas, além de adição de endereços. Implementa
busca fuzzy por nome (pg_trgm) e busca por CPF (hash SHA-256).
"""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.pessoa import (
    EnderecoCreate,
    EnderecoRead,
    PessoaCreate,
    PessoaDetail,
    PessoaRead,
    PessoaUpdate,
    VinculoRead,
)
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
    user: Usuario = Depends(get_current_user),
) -> PessoaRead:
    """Cria nova pessoa com CPF criptografado.

    Cria registro de pessoa, criptografa CPF com Fernet (AES-256)
    e gera hash SHA-256 para buscas. Verifica unicidade de CPF.

    Args:
        request: Objeto Request do FastAPI.
        data: Dados de criação (nome, cpf, nascimento, apelido, observacoes).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PessoaRead com dados da pessoa criada.

    Raises:
        ConflitoDadosError: Se CPF já cadastrado na guarnição.

    Status Code:
        201: Pessoa criada com sucesso.
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
async def detalhe_pessoa(
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

    # Montar vínculos a partir de ambas direções de relacionamento
    vinculos = []
    for rel in pessoa.relacionamentos_como_a:
        vinculos.append(
            VinculoRead(
                pessoa_id=rel.pessoa_id_b,
                nome=rel.pessoa_b.nome if rel.pessoa_b else "",
                frequencia=rel.frequencia,
                ultima_vez=rel.ultima_vez,
            )
        )
    for rel in pessoa.relacionamentos_como_b:
        vinculos.append(
            VinculoRead(
                pessoa_id=rel.pessoa_id_a,
                nome=rel.pessoa_a.nome if rel.pessoa_a else "",
                frequencia=rel.frequencia,
                ultima_vez=rel.ultima_vez,
            )
        )

    return PessoaDetail(
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
        enderecos=[EnderecoRead.model_validate(e) for e in pessoa.enderecos],
        abordagens_count=len(pessoa.abordagens),
        relacionamentos=vinculos,
    )


@router.put("/{pessoa_id}", response_model=PessoaRead)
async def atualizar_pessoa(
    request: Request,
    pessoa_id: int,
    data: PessoaUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PessoaRead:
    """Atualiza parcialmente uma pessoa.

    Apenas campos enviados são atualizados. Se CPF for alterado,
    re-criptografa e re-gera hash.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa a atualizar.
        data: Campos a atualizar.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PessoaRead atualizada.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.
        ConflitoDadosError: Se novo CPF já cadastrado.
    """
    service = PessoaService(db)
    pessoa = await service.atualizar(
        pessoa_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_pessoa_read(pessoa, service)


@router.delete("/{pessoa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def desativar_pessoa(
    request: Request,
    pessoa_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Desativa uma pessoa (soft delete).

    Marca pessoa como inativa sem remoção física. Registra auditoria.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa a desativar.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.

    Status Code:
        204: Pessoa desativada.
    """
    service = PessoaService(db)
    await service.desativar(
        pessoa_id,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/{pessoa_id}/enderecos",
    response_model=EnderecoRead,
    status_code=status.HTTP_201_CREATED,
)
async def adicionar_endereco(
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
    return EnderecoRead.model_validate(endereco)
