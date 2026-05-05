"""Model de BPM (Batalhão de Polícia Militar) — nível hierárquico acima das equipes.

Define a entidade que agrupa equipes (guarnições) por batalhão.
Um BPM contém N equipes. Usuário pertence a uma equipe, que pertence a um BPM.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Bpm(Base, TimestampMixin, SoftDeleteMixin):
    """Batalhão de Polícia Militar — agrupador de equipes.

    Representa a unidade administrativa superior que agrupa equipes
    operacionais. Exemplo: "14º BPM", "PMDF".

    Attributes:
        id: Identificador único.
        nome: Nome do batalhão (ex: "14º BPM"). Único no sistema.
        isolamento_abordagens: Se True, usuários do BPM veem apenas abordagens
            do próprio BPM. Se False (padrão), veem todas.
        guarnicoes: Equipes pertencentes a este BPM.
    """

    __tablename__ = "bpm"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), unique=True)
    isolamento_abordagens: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    guarnicoes = relationship(
        "Guarnicao",
        back_populates="bpm",
        lazy="noload",
    )
