"""Filtro de multi-tenancy para isolamento de dados por guarnição.

Garante que usuários só acessem dados da sua própria guarnição através
de filtros automáticos em queries e verificações de propriedade de recursos.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AcessoNegadoError


class TenantFilter:
    """Filtro de multi-tenancy para isolamento de dados por guarnição.

    Implementa o padrão de multi-tenancy garantindo que cada usuário só
    tenha acesso a dados da sua guarnição. Aplica automaticamente em queries
    e verifica propriedade em recursos individuais.
    """

    @staticmethod
    def apply(query, model_class, user):
        """Adiciona filtro de guarnição a uma query SQLAlchemy.

        Se o model tem atributo guarnicao_id, filtra automaticamente para
        a guarnição do usuário autenticado.

        Args:
            query: Query SQLAlchemy a ser filtrada.
            model_class: Classe de model SQLAlchemy.
            user: Objeto usuário com atributo guarnicao_id.

        Returns:
            Query filtrada se model tem guarnicao_id, caso contrário retorna query original.
        """

        if hasattr(model_class, "guarnicao_id") and user.guarnicao_id is not None:
            return query.where(model_class.guarnicao_id == user.guarnicao_id)
        return query

    @staticmethod
    def check_ownership(resource, user):
        """Verifica se recurso pertence à guarnição do usuário.

        Lança exceção se recurso pertence a outra guarnição. Admins
        (is_admin=True) ignoram esta verificação e podem operar em
        qualquer guarnição.

        Args:
            resource: Objeto de recurso a verificar.
            user: Objeto usuário com atributo guarnicao_id.

        Raises:
            AcessoNegadoError: Se recurso pertence a outra guarnição.
        """
        if getattr(user, "is_admin", False):
            return

        if hasattr(resource, "guarnicao_id") and user.guarnicao_id is not None:
            if resource.guarnicao_id != user.guarnicao_id:
                raise AcessoNegadoError("Recurso de outra guarnição")


def filtros_abordagem(user) -> tuple[int | None, int | None]:
    """Resolve a cascata de visibilidade de abordagens para um usuário.

    Aplica a prioridade equipe > BPM > global a partir das flags
    ``isolamento_abordagens`` da guarnição e do BPM do usuário. Fonte única de
    verdade reutilizada por consultas e pelo controle de acesso a mídias de
    abordagem no storage.

    Args:
        user: Usuário autenticado com ``guarnicao`` (e ``guarnicao.bpm``)
            carregados — ambos relacionamentos são ``lazy="selectin"``.

    Returns:
        Tupla ``(guarnicao_id, bpm_id)``. No máximo um é não-None; ambos None
        significa acesso global.
    """
    if user.guarnicao and user.guarnicao.isolamento_abordagens:
        return (user.guarnicao_id, None)
    if user.guarnicao and user.guarnicao.bpm and user.guarnicao.bpm.isolamento_abordagens:
        return (None, user.guarnicao.bpm_id)
    return (None, None)


async def assert_pode_ver_foto_abordagem(db: AsyncSession, user, foto) -> None:
    """Autoriza o acesso a uma mídia de abordagem segundo a cascata de isolamento.

    Mídia de abordagem (``Foto`` sem ``pessoa_id``) segue a mesma visibilidade
    das abordagens em consultas/analytics: global por padrão, restrita à equipe
    ou ao BPM quando ``isolamento_abordagens`` está ativo. Mantém o storage
    consistente com o restante do sistema (evita 403 indevido quando o
    isolamento está desligado).

    Args:
        db: Sessão assíncrona do banco (para resolver o BPM da foto no modo BPM).
        user: Usuário autenticado com ``guarnicao``/``bpm`` carregados.
        foto: Registro ``Foto`` da mídia de abordagem (tem ``guarnicao_id``).

    Raises:
        AcessoNegadoError: Se a foto está fora do alcance de visibilidade do
            usuário (outra equipe sob isolamento de equipe, ou outro BPM sob
            isolamento de BPM).
    """
    guarnicao_id, bpm_id = filtros_abordagem(user)
    if guarnicao_id is not None:
        if foto.guarnicao_id != guarnicao_id:
            raise AcessoNegadoError("Recurso de outra guarnição")
        return
    if bpm_id is not None:
        from app.models.guarnicao import Guarnicao

        foto_bpm_id = (
            await db.execute(select(Guarnicao.bpm_id).where(Guarnicao.id == foto.guarnicao_id))
        ).scalar_one_or_none()
        if foto_bpm_id != bpm_id:
            raise AcessoNegadoError("Recurso de outra guarnição")
    # Sem isolamento: mídia de abordagem é global — acesso liberado.


def assert_scope(admin, alvo_guarnicao_id: int | None) -> None:
    """Valida o alcance de um admin delegado sobre uma guarnição alvo.

    Super-admin e admin global passam sempre. Delegado não-global só age sobre
    a própria guarnição (e nunca quando ele mesmo não tem guarnição).

    Args:
        admin: Usuário autenticado executando a ação (precisa de is_super_admin,
            admin_global e guarnicao_id).
        alvo_guarnicao_id: Guarnição do alvo (ou destino) da ação.

    Raises:
        AcessoNegadoError: 403 se a ação está fora do alcance do admin.
    """
    if admin.is_super_admin or admin.admin_global:
        return
    if admin.guarnicao_id is None or alvo_guarnicao_id != admin.guarnicao_id:
        raise AcessoNegadoError("Fora do alcance da sua equipe")
