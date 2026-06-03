"""Regressão: nenhum SQL bruto com f-string ou formatação de string.

Garante que novas queries não usem interpolação direta de strings em SQL,
o que abriria vetores de SQL injection. O único text() permitido é com
bind params nomeados (ex: ':param').
"""

import ast
import re
from pathlib import Path


# Arquivos/pastas a ignorar (migrações e conftest têm padrões legítimos)
_IGNORAR = {
    "alembic",
    "migrations",
    ".venv",
    "__pycache__",
    ".git",
    "tests",
}

_PADROES_PERIGOSOS = [
    # f-string em SQL
    re.compile(r'(?:execute|text)\s*\(\s*f["\']'),
    # .format() em SQL
    re.compile(r'(?:execute|text)\s*\(.*\.format\s*\('),
    # % em SQL (interpolação estilo printf)
    re.compile(r'(?:execute|text)\s*\(.*%\s*[(\w]'),
]


def _coletar_arquivos_python() -> list[Path]:
    """Retorna arquivos .py da pasta app/ excluindo pastas ignoradas.

    Returns:
        Lista de Paths dos arquivos Python da aplicação.
    """
    raiz = Path(__file__).parent.parent.parent / "app"
    arquivos = []
    for path in raiz.rglob("*.py"):
        partes = set(path.parts)
        if partes & _IGNORAR:
            continue
        arquivos.append(path)
    return arquivos


def test_sem_sql_bruto_por_regex():
    """Nenhum arquivo de app/ deve usar f-string/format/% em text() ou execute().

    Detecta padrões comuns de SQL injection por interpolação de strings.
    Falha com lista de arquivos e linhas problemáticas para facilitar fix.
    """
    violacoes: list[str] = []
    for path in _coletar_arquivos_python():
        try:
            linhas = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i, linha in enumerate(linhas, start=1):
            for padrao in _PADROES_PERIGOSOS:
                if padrao.search(linha):
                    violacoes.append(f"{path.relative_to(Path.cwd())}:{i}: {linha.strip()}")

    assert not violacoes, (
        "SQL bruto detectado (f-string/format/% em execute/text):\n"
        + "\n".join(violacoes)
    )
