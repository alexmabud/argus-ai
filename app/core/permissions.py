from fastapi import HTTPException, status


class TenantFilter:
    """Garante que usuário só acessa dados da sua guarnição."""

    @staticmethod
    def apply(query, model_class, user):
        """Adiciona filtro de guarnição em qualquer query."""
        if hasattr(model_class, "guarnicao_id"):
            return query.where(model_class.guarnicao_id == user.guarnicao_id)
        return query

    @staticmethod
    def check_ownership(resource, user):
        """Verifica se recurso pertence à guarnição do usuário."""
        if hasattr(resource, "guarnicao_id"):
            if resource.guarnicao_id != user.guarnicao_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado — recurso de outra guarnição",
                )
