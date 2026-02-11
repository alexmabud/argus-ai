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

        if hasattr(model_class, "guarnicao_id"):
            return query.where(model_class.guarnicao_id == user.guarnicao_id)
        return query

    @staticmethod
    def check_ownership(resource, user):
        """Verifica se recurso pertence à guarnição do usuário.

        Lança exceção se recurso pertence a outra guarnição. Essencial
        para proteger endpoints que retornam recursos específicos.

        Args:
            resource: Objeto de recurso a verificar.
            user: Objeto usuário com atributo guarnicao_id.

        Raises:
            AcessoNegadoError: Se recurso pertence a outra guarnição.
        """

        if hasattr(resource, "guarnicao_id"):
            if resource.guarnicao_id != user.guarnicao_id:
                raise AcessoNegadoError("Recurso de outra guarnição")
