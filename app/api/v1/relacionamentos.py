"""Router de consulta de relacionamentos entre pessoas.

Fornece endpoint para consulta de vínculos materializados entre
pessoas abordadas juntas, com frequência e histórico temporal.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.pessoa import VinculoRead
from app.services.relacionamento_service import RelacionamentoService

router = APIRouter(prefix="/relacionamentos", tags=["Relacionamentos"])


@router.get("/pessoa/{pessoa_id}", response_model=list[VinculoRead])
async def listar_vinculos_pessoa(
    pessoa_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[VinculoRead]:
    """Lista vínculos de uma pessoa com outras pessoas.

    Retorna todos os vínculos materializados onde a pessoa aparece
    como pessoa_a ou pessoa_b, ordenados por frequência decrescente
    (vínculos mais fortes primeiro).

    Args:
        pessoa_id: ID da pessoa para consultar vínculos.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de VinculoRead com pessoa_id, nome, frequência e última vez.
    """
    service = RelacionamentoService(db)
    relacionamentos = await service.buscar_vinculos(pessoa_id)

    vinculos = []
    for rel in relacionamentos:
        if rel.pessoa_id_a == pessoa_id:
            vinculos.append(
                VinculoRead(
                    pessoa_id=rel.pessoa_id_b,
                    nome=rel.pessoa_b.nome if rel.pessoa_b else "Desconhecido",
                    frequencia=rel.frequencia,
                    ultima_vez=rel.ultima_vez,
                )
            )
        else:
            vinculos.append(
                VinculoRead(
                    pessoa_id=rel.pessoa_id_a,
                    nome=rel.pessoa_a.nome if rel.pessoa_a else "Desconhecido",
                    frequencia=rel.frequencia,
                    ultima_vez=rel.ultima_vez,
                )
            )

    return vinculos
