"""Router de consulta unificada cross-domain.

Fornece endpoint de busca simultânea em pessoas, veículos e
abordagens através de um único termo de busca, consolidando
resultados em uma resposta unificada. Também expõe endpoint
de localidades para autocomplete de bairro, cidade e estado.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.repositories.pessoa_repo import PessoaRepository
from app.schemas.abordagem import AbordagemRead
from app.schemas.consulta import (
    ConsultaUnificadaResponse,
    PessoaComEnderecoRead,
    PessoaComVeiculoRead,
    VeiculoInfo,
)
from app.schemas.veiculo import VeiculoRead
from app.services.consulta_service import ConsultaService
from app.services.pessoa_service import PessoaService

router = APIRouter(prefix="/consultas", tags=["Consultas"])


@router.get("/localidades")
async def listar_localidades(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna valores distintos de bairro, cidade e estado cadastrados.

    Utilizado pelo frontend para popular datalists de autocomplete nos
    campos de localização. Filtra por guarnição do usuário autenticado.

    Args:
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Dicionário com "bairros", "cidades" e "estados" — listas de strings
        distintas ordenadas alfabeticamente.
    """
    repo = PessoaRepository(db)
    return await repo.get_localidades(guarnicao_id=user.guarnicao_id)


@router.get("/", response_model=ConsultaUnificadaResponse)
async def consulta_unificada(
    q: str = Query(
        "",
        min_length=0,
        max_length=500,
        description="Termo de busca (obrigatório sem filtros de endereço)",
    ),
    tipo: str | None = Query(
        None,
        description="Tipo de entidade: pessoa, veiculo, abordagem (ou None para todas)",
    ),
    bairro: str | None = Query(None, max_length=200, description="Filtrar pessoas por bairro"),
    cidade: str | None = Query(None, max_length=200, description="Filtrar pessoas por cidade"),
    estado: str | None = Query(None, max_length=2, description="Filtrar pessoas por estado (UF)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> ConsultaUnificadaResponse:
    """Busca unificada em pessoas, veículos e abordagens.

    Distribui a busca conforme o tipo solicitado ou busca em todas
    as entidades simultaneamente. Aplica filtro multi-tenant automático.
    Quando bairro, cidade ou estado informados, filtra apenas pessoas por endereço.

    Estratégias de busca por entidade:
    - Pessoa: busca fuzzy por nome (pg_trgm) + busca exata por CPF (hash)
        + filtro por bairro/cidade/estado quando informados.
    - Veículo: busca parcial por placa (ILIKE normalizado).
    - Abordagem: busca por endereço texto (ILIKE).

    Args:
        q: Termo de busca (mínimo 2 caracteres).
        tipo: Filtrar por tipo de entidade (opcional).
        bairro: Filtrar pessoas por bairro do endereço (opcional).
        cidade: Filtrar pessoas por cidade do endereço (opcional).
        estado: Filtrar pessoas por estado UF do endereço (opcional).
        skip: Registros a pular por entidade (paginação).
        limit: Máximo de resultados por entidade (1-100, padrão 20).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        ConsultaUnificadaResponse com listas de pessoas, veículos,
        abordagens e total de resultados.
    """
    filtro_endereco = bairro or cidade or estado
    if not filtro_endereco and len(q) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                "Informe ao menos 2 caracteres no termo de busca ou utilize os filtros de endereço."
            ),
        )

    service = ConsultaService(db)
    resultados = await service.busca_unificada(
        q=q,
        tipo=tipo,
        bairro=bairro,
        cidade=cidade,
        estado=estado,
        skip=skip,
        limit=limit,
        user=user,
    )

    pessoas_read = []
    pessoas_com_endereco = resultados.get("pessoas_com_endereco", False)

    for item in resultados["pessoas"]:
        if pessoas_com_endereco:
            p, endereco_criado_em = item
        else:
            p, endereco_criado_em = item, None

        pessoas_read.append(
            PessoaComEnderecoRead(
                id=p.id,
                nome=p.nome,
                cpf_masked=PessoaService.mask_cpf(p) if p.cpf_encrypted else None,
                data_nascimento=p.data_nascimento,
                apelido=p.apelido,
                foto_principal_url=p.foto_principal_url,
                observacoes=p.observacoes,
                guarnicao_id=p.guarnicao_id,
                criado_em=p.criado_em,
                atualizado_em=p.atualizado_em,
                endereco_criado_em=endereco_criado_em,
            )
        )

    veiculos_read = [VeiculoRead.model_validate(v) for v in resultados["veiculos"]]
    abordagens_read = [AbordagemRead.model_validate(a) for a in resultados["abordagens"]]

    return ConsultaUnificadaResponse(
        pessoas=pessoas_read,
        veiculos=veiculos_read,
        abordagens=abordagens_read,
        total_resultados=resultados["total_resultados"],
    )


@router.get("/pessoas-por-veiculo", response_model=list[PessoaComVeiculoRead])
async def pessoas_por_veiculo(
    placa: str | None = Query(None, max_length=20, description="Placa parcial (ILIKE)"),
    modelo: str | None = Query(None, max_length=100, description="Modelo do veículo"),
    cor: str | None = Query(None, max_length=50, description="Cor do veículo (opcional)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[PessoaComVeiculoRead]:
    """Retorna fichas de abordados vinculados a um veículo.

    Resolve Veiculo → AbordagemVeiculo → AbordagemPessoa → Pessoa
    para encontrar todos os abordados que tiveram relação com o veículo
    buscado. Pelo menos um parâmetro (placa ou modelo) deve ser informado.

    Args:
        placa: Placa parcial para busca (opcional).
        modelo: Modelo do veículo para busca (opcional).
        cor: Cor do veículo — usada como filtro adicional ao modelo (opcional).
        skip: Registros a pular (paginação).
        limit: Máximo de resultados por página (1-100, padrão 20).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de PessoaComVeiculoRead com dados do abordado e do veículo vinculado.

    Raises:
        HTTPException 400: Se nenhum parâmetro de busca for informado.
    """
    if not placa and not modelo:
        raise HTTPException(status_code=400, detail="Informe placa ou modelo para buscar.")

    service = ConsultaService(db)
    rows = await service.pessoas_por_veiculo(
        placa=placa,
        modelo=modelo,
        cor=cor,
        skip=skip,
        limit=limit,
        user=user,
    )

    return [
        PessoaComVeiculoRead(
            id=row["pessoa"].id,
            nome=row["pessoa"].nome,
            cpf_masked=PessoaService.mask_cpf(row["pessoa"])
            if row["pessoa"].cpf_encrypted
            else None,
            data_nascimento=row["pessoa"].data_nascimento,
            apelido=row["pessoa"].apelido,
            foto_principal_url=row["pessoa"].foto_principal_url,
            observacoes=row["pessoa"].observacoes,
            guarnicao_id=row["pessoa"].guarnicao_id,
            criado_em=row["pessoa"].criado_em,
            atualizado_em=row["pessoa"].atualizado_em,
            veiculo_info=VeiculoInfo(
                placa=row["veiculo"].placa,
                modelo=row["veiculo"].modelo,
                cor=row["veiculo"].cor,
                ano=row["veiculo"].ano,
                foto_veiculo_url=row.get("foto_veiculo_url"),
            ),
        )
        for row in rows
    ]
