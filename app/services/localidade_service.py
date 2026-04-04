"""Service de Localidade — criação e busca com validação hierárquica.

Encapsula regras de negócio para localidades: impede duplicatas,
valida hierarquia (cidade precisa de estado pai, bairro precisa de cidade pai)
e normaliza nomes para busca.
"""

import unicodedata

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError, ValidacaoError
from app.models.localidade import Localidade
from app.repositories.localidade_repo import LocalidadeRepository
from app.schemas.localidade import LocalidadeCreate


def _normalizar(nome: str) -> str:
    """Normaliza texto para busca: remove acentos e converte para minúsculas.

    Args:
        nome: Texto original.

    Returns:
        Texto sem acentos em minúsculas.
    """
    return "".join(
        c
        for c in unicodedata.normalize("NFD", nome.strip().lower())
        if unicodedata.category(c) != "Mn"
    )


class LocalidadeService:
    """Service de Localidade com validação de hierarquia e deduplicação.

    Attributes:
        db: Sessão assíncrona do banco de dados.
        repo: Repository de localidades.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Inicializa o service com a sessão do banco.

        Args:
            db: Sessão assíncrona SQLAlchemy.
        """
        self.db = db
        self.repo = LocalidadeRepository(db)

    async def listar_estados(self) -> list[Localidade]:
        """Retorna todos os 27 estados ordenados por nome.

        Returns:
            Lista de estados.
        """
        return await self.repo.listar_estados()

    async def autocomplete(
        self,
        tipo: str,
        parent_id: int,
        q: str | None = None,
    ) -> list[Localidade]:
        """Autocomplete de cidades ou bairros filtrados por texto, ou lista todos.

        Quando q é None ou vazio, retorna todas as localidades filhas do parent_id.
        Quando q é fornecido, filtra por nome normalizado com ILIKE.

        Args:
            tipo: 'cidade' ou 'bairro'.
            parent_id: ID do estado (para cidades) ou cidade (para bairros).
            q: Texto digitado pelo usuário (opcional).

        Returns:
            Lista de localidades correspondentes.
        """
        q_normalizado = _normalizar(q) if q else None
        return await self.repo.autocomplete(tipo=tipo, parent_id=parent_id, q=q_normalizado)

    async def criar(self, data: LocalidadeCreate) -> Localidade:
        """Cria nova cidade ou bairro após validar hierarquia e duplicata.

        Normaliza o nome para busca. Valida que o parent_id corresponde
        ao tipo correto (cidade precisa de pai estado, bairro de pai cidade).
        Impede duplicatas pelo nome normalizado + parent_id + tipo.

        Args:
            data: Dados da nova localidade (nome, tipo, parent_id).

        Returns:
            Localidade criada.

        Raises:
            NaoEncontradoError: Quando parent_id não existe.
            ValidacaoError: Quando hierarquia é inválida.
            ConflitoDadosError: Quando já existe localidade com mesmo nome e pai.
        """
        nome_normalizado = _normalizar(data.nome)

        # Validar pai
        pai = await self.repo.get(data.parent_id)
        if not pai:
            raise NaoEncontradoError("Localidade pai")

        # Validar hierarquia
        if data.tipo == "cidade" and pai.tipo != "estado":
            raise ValidacaoError("Uma cidade deve ter um estado como pai.")
        if data.tipo == "bairro" and pai.tipo != "cidade":
            raise ValidacaoError("Um bairro deve ter uma cidade como pai.")

        # Verificar duplicata
        existente = await self.repo.buscar_por_nome_e_parent(
            nome_normalizado, data.tipo, data.parent_id
        )
        if existente:
            raise ConflitoDadosError(
                f"{data.tipo.capitalize()} '{data.nome}' já cadastrada neste local."
            )

        localidade = Localidade(
            nome=nome_normalizado,
            nome_exibicao=data.nome.strip(),
            tipo=data.tipo,
            parent_id=data.parent_id,
        )
        self.db.add(localidade)
        await self.db.flush()
        return localidade
