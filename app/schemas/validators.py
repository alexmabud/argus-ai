"""Validators reutilizáveis para schemas Pydantic.

Fornece normalização de texto digitado pelo usuário para padronização
operacional (MAIÚSCULAS), aplicável via tipo anotado em qualquer schema.
Usado nos campos de texto livre de pessoa, endereço, abordagem e veículo.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BeforeValidator


def to_upper(v: str | None) -> str | None:
    """Normaliza texto para MAIÚSCULAS, removendo espaços nas pontas.

    Usado em campos de texto livre digitados pelo usuário (nomes, endereços,
    observações) para manter padrão visual e operacional. O .upper() do Python
    respeita acentos (ex: "joão" -> "JOÃO").

    Args:
        v: Valor de texto informado, ou None.

    Returns:
        Texto em maiúsculas sem espaços nas pontas. None permanece None.
        Valores não-string são repassados intactos para o Pydantic reportar
        o erro de tipo normalmente (evita AttributeError em .strip()).
    """
    if not isinstance(v, str):
        return v
    return v.strip().upper()


UpperStr = Annotated[str | None, BeforeValidator(to_upper)]
"""Tipo para campo de texto OPCIONAL normalizado para MAIÚSCULAS."""

UpperStrReq = Annotated[str, BeforeValidator(to_upper)]
"""Tipo para campo de texto OBRIGATÓRIO normalizado para MAIÚSCULAS.

Preserva a validação de obrigatoriedade: None é rejeitado e as constraints
de comprimento (min_length/max_length) continuam aplicadas sobre o valor já
normalizado.
"""
