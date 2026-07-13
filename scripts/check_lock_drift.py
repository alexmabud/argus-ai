"""Verifica se requirements.lock ainda satisfaz os pisos de pyproject.toml.

Detecta o caso em que uma dependência teve seu piso (`>=X.Y.Z`) elevado em
`pyproject.toml` (ex.: bump manual ou merge de PR do Dependabot) mas
`requirements.lock` não foi regenerado (`make lock`) — o build de produção
(`Dockerfile.prod`, via `pip install --require-hashes -r requirements.lock`)
continuaria instalando uma versão abaixo do piso declarado, sem que nenhum
teste ou lint acuse o problema (achado #20/2026-07-13).

Compara apenas PISOS (não faz diff bruto do lock inteiro): como
`pyproject.toml` usa `>=` sem teto, `pip-compile` naturalmente resolve
versões mais novas ao longo do tempo mesmo sem mudança nenhuma no
pyproject — isso é esperado e não é drift real (ver memória de projeto
sobre PRs do Dependabot). O único caso que importa é o lock ficar
*abaixo* do piso declarado.
"""

import re
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
LOCK = ROOT / "requirements.lock"

_LOCK_LINE_RE = re.compile(r"^([A-Za-z0-9_.\-]+)(\[[A-Za-z0-9_.,\-]+\])?==([A-Za-z0-9_.\-+]+)")


def _parse_lock_versions(lock_text: str) -> dict[str, str]:
    """Extrai {nome_normalizado: versão} de um requirements.lock com hashes.

    Args:
        lock_text: Conteúdo bruto de requirements.lock.

    Returns:
        Dicionário de nome de pacote normalizado (lowercase, `_`→`-`,
        sem extras) para a versão travada (string, ex. "2.0.50").
    """
    versions: dict[str, str] = {}
    for line in lock_text.splitlines():
        match = _LOCK_LINE_RE.match(line)
        if match:
            name = match.group(1).lower().replace("_", "-")
            versions[name] = match.group(3)
    return versions


def check_lock_drift() -> list[str]:
    """Compara pisos declarados em pyproject.toml contra requirements.lock.

    Considera as dependências base e o extra `vision` (o mesmo escopo usado
    por `make lock` / `Dockerfile.prod`).

    Returns:
        Lista de mensagens de violação (vazia se o lock satisfaz todos os
        pisos declarados).
    """
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = data["project"]
    deps = list(project.get("dependencies", []))
    deps.extend(project.get("optional-dependencies", {}).get("vision", []))

    lock_versions = _parse_lock_versions(LOCK.read_text(encoding="utf-8"))

    violations = []
    for dep in deps:
        req = Requirement(dep)
        name = req.name.lower().replace("_", "-")
        locked = lock_versions.get(name)
        if not locked:
            violations.append(
                f"{name}: declarado em pyproject.toml mas ausente em requirements.lock"
            )
            continue
        try:
            if not req.specifier.contains(Version(locked), prereleases=True):
                violations.append(
                    f"{name}: pyproject.toml exige {req.specifier}, "
                    f"mas requirements.lock trava {locked}"
                )
        except Exception as exc:  # versão malformada — sinaliza em vez de mascarar
            violations.append(f"{name}: erro ao comparar versão travada '{locked}': {exc}")

    return violations


def main() -> None:
    """Executa a checagem e sai com código de erro se houver violação de piso."""
    violations = check_lock_drift()
    if violations:
        print("ERRO: requirements.lock não satisfaz pisos de pyproject.toml:\n")
        for v in violations:
            print(f"  - {v}")
        print("\nRode `make lock` para regenerar requirements.lock e commite o resultado.")
        sys.exit(1)

    print("OK: requirements.lock satisfaz todos os pisos declarados em pyproject.toml")


if __name__ == "__main__":
    main()
