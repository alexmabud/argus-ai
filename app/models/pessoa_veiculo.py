"""Modelo de PessoaVeiculo — vínculo direto entre pessoa e veículo.

Define associação manual entre pessoa e veículo, registrada pelo
operador diretamente na ficha do abordado, independente de qualquer
abordagem (mesma filosofia de VinculoManual para pessoa-pessoa).
"""

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MultiTenantMixin, SoftDeleteMixin, TimestampMixin


class PessoaVeiculo(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    """Vínculo direto entre pessoa e veículo, cadastrado pelo operador.

    Diferente de AbordagemVeiculo (que materializa a presença de um
    veículo numa abordagem específica), este vínculo existe independente
    de qualquer abordagem — permite anotar "esse carro é dessa pessoa"
    direto na ficha, sem precisar criar uma abordagem pra isso.
    Não duplica dados de veículo: aponta pra um Veiculo já existente
    na tabela `veiculos` (a mesma usada pelas abordagens).

    Attributes:
        id: Identificador único.
        pessoa_id: ID da pessoa dona do vínculo (FK, CASCADE).
        veiculo_id: ID do veículo vinculado (FK, CASCADE).
        criado_por_id: ID do usuário que criou o vínculo (FK, nullable).
        guarnicao_id: Guarnição (herdado de MultiTenantMixin).
        pessoa: Relacionamento com Pessoa.
        veiculo: Relacionamento com Veiculo.

    Nota:
        - UNIQUE(pessoa_id, veiculo_id) evita duplicatas.
        - Soft delete via SoftDeleteMixin — "desvincular" reativa/desativa
          esta linha, nunca apaga fisicamente nem apaga o Veiculo em si.
    """

    __tablename__ = "pessoa_veiculos"

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id", ondelete="CASCADE"), index=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculos.id", ondelete="CASCADE"), index=True)
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    pessoa = relationship("Pessoa", lazy="selectin")
    veiculo = relationship("Veiculo", lazy="selectin")

    __table_args__ = (UniqueConstraint("pessoa_id", "veiculo_id", name="uq_pessoa_veiculo"),)
