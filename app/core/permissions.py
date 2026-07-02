"""Filtro de multi-tenancy para isolamento de dados por guarnição.

Garante que usuários só acessem dados da sua própria guarnição através
de filtros automáticos em queries e verificações de propriedade de recursos.
"""

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
