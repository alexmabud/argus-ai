"""Router de consulta unificada cross-domain.

Fornece endpoint de busca simultânea em pessoas, veículos e
abordagens através de um único termo de busca, consolidando
resultados em uma resposta unificada.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.abordagem import AbordagemRead
from app.schemas.consulta import ConsultaUnificadaResponse
from app.schemas.pessoa import PessoaRead
from app.schemas.veiculo import VeiculoRead
from app.services.consulta_service import ConsultaService
from app.services.pessoa_service import PessoaService

router = APIRouter(prefix="/consultas", tags=["Consultas"])


@router.get("/", response_model=ConsultaUnificadaResponse)
async def consulta_unificada(
    q: str = Query(..., min_length=2, max_length=500, description="Termo de busca"),
    tipo: str | None = Query(
        None,
        description="Tipo de entidade: pessoa, veiculo, abordagem (ou None para todas)",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> ConsultaUnificadaResponse:
    """Busca unificada em pessoas, veículos e abordagens.

    Distribui a busca conforme o tipo solicitado ou busca em todas
    as entidades simultaneamente. Aplica filtro multi-tenant automático.

    Estratégias de busca por entidade:
    - Pessoa: busca fuzzy por nome (pg_trgm) + busca exata por CPF (hash).
    - Veículo: busca parcial por placa (ILIKE normalizado).
    - Abordagem: busca por endereço texto (ILIKE).

    Args:
        q: Termo de busca (mínimo 2 caracteres).
        tipo: Filtrar por tipo de entidade (opcional).
        skip: Registros a pular por entidade (paginação).
        limit: Máximo de resultados por entidade (1-100, padrão 20).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        ConsultaUnificadaResponse com listas de pessoas, veículos,
        abordagens e total de resultados.
    """
    service = ConsultaService(db)
    resultados = await service.busca_unificada(q=q, tipo=tipo, skip=skip, limit=limit, user=user)

    pessoas_read = []
    for p in resultados["pessoas"]:
        pessoas_read.append(
            PessoaRead(
                id=p.id,
                nome=p.nome,
                cpf_masked=PessoaService.mask_cpf(p.cpf_encrypted) if p.cpf_encrypted else None,
                data_nascimento=p.data_nascimento,
                apelido=p.apelido,
                foto_principal_url=p.foto_principal_url,
                observacoes=p.observacoes,
                guarnicao_id=p.guarnicao_id,
                criado_em=p.criado_em,
                atualizado_em=p.atualizado_em,
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
