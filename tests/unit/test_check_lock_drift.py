"""Testes unitários do script check_lock_drift (``scripts/check_lock_drift.py``).

Valida a detecção de pisos de pyproject.toml não satisfeitos por
requirements.lock (achado #20/2026-07-13), usando arquivos sintéticos em
diretório temporário — sem depender do pyproject.toml/requirements.lock
reais do projeto.
"""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_lock_drift.py"
_spec = importlib.util.spec_from_file_location("check_lock_drift", _SCRIPT)
check_lock_drift_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_lock_drift_mod)


def _escrever_arquivos(tmp_path: Path, pyproject_deps: str, lock_content: str) -> None:
    """Escreve pyproject.toml e requirements.lock sintéticos e aponta o módulo para eles."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        f'[project]\nname = "fake"\nversion = "0.0.0"\ndependencies = {pyproject_deps}\n',
        encoding="utf-8",
    )
    lock = tmp_path / "requirements.lock"
    lock.write_text(lock_content, encoding="utf-8")
    check_lock_drift_mod.PYPROJECT = pyproject
    check_lock_drift_mod.LOCK = lock


class TestCheckLockDrift:
    """Testes de check_lock_drift()."""

    def test_lock_satisfaz_pisos_retorna_lista_vazia(self, tmp_path: Path) -> None:
        """Nenhuma violação quando a versão travada atende ao piso declarado."""
        _escrever_arquivos(
            tmp_path,
            pyproject_deps='["pillow>=12.3.0"]',
            lock_content="pillow==12.3.0 \\\n    --hash=sha256:aaaa\n",
        )
        assert check_lock_drift_mod.check_lock_drift() == []

    def test_lock_abaixo_do_piso_gera_violacao(self, tmp_path: Path) -> None:
        """Versão travada abaixo do piso declarado é reportada."""
        _escrever_arquivos(
            tmp_path,
            pyproject_deps='["pillow>=12.3.0"]',
            lock_content="pillow==12.2.0 \\\n    --hash=sha256:aaaa\n",
        )
        violacoes = check_lock_drift_mod.check_lock_drift()
        assert len(violacoes) == 1
        assert "pillow" in violacoes[0]
        assert "12.3.0" in violacoes[0]
        assert "12.2.0" in violacoes[0]

    def test_pacote_ausente_do_lock_gera_violacao(self, tmp_path: Path) -> None:
        """Dependência declarada em pyproject.toml mas ausente do lock é reportada."""
        _escrever_arquivos(
            tmp_path,
            pyproject_deps='["fastapi>=0.100.0"]',
            lock_content="pillow==12.3.0 \\\n    --hash=sha256:aaaa\n",
        )
        violacoes = check_lock_drift_mod.check_lock_drift()
        assert len(violacoes) == 1
        assert "fastapi" in violacoes[0]
        assert "ausente" in violacoes[0]

    def test_pacote_com_extras_no_lock_e_reconhecido(self, tmp_path: Path) -> None:
        """Linhas do lock com extras entre colchetes (ex.: sqlalchemy[asyncio]) são parseadas."""
        _escrever_arquivos(
            tmp_path,
            pyproject_deps='["sqlalchemy[asyncio]>=2.0.50"]',
            lock_content="sqlalchemy[asyncio]==2.0.50 \\\n    --hash=sha256:aaaa\n",
        )
        assert check_lock_drift_mod.check_lock_drift() == []

    def test_lock_acima_do_piso_nao_e_violacao(self, tmp_path: Path) -> None:
        """Versão travada mais nova que o piso (comum, dado pip-compile) não é violação."""
        _escrever_arquivos(
            tmp_path,
            pyproject_deps='["pillow>=12.2.0"]',
            lock_content="pillow==12.3.0 \\\n    --hash=sha256:aaaa\n",
        )
        assert check_lock_drift_mod.check_lock_drift() == []
