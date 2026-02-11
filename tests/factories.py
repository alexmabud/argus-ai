"""Factories para geração de dados de teste.

Fornece factories baseadas em factory_boy para criar instâncias de modelos
com dados aleatórios mas válidos, facilitando a criação de fixtures e dados
de teste sem duplicação de código.
"""

import factory

from app.core.security import hash_senha
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


class GuarnicaoFactory(factory.Factory):
    """Factory para criar instâncias de guarnição para testes.

    Gera guarnições com dados aleatórios mas sequenciais e válidos,
    facilitando a criação de múltiplas instâncias sem conflitos de chave única.

    Attributes:
        nome: Nome sequencial da guarnição (ex: "Guarnicao 1").
        unidade: Unidade sequencial (ex: "Unidade 1").
        codigo: Código sequencial único (ex: "UNI-001").
    """

    class Meta:
        model = Guarnicao

    nome = factory.Sequence(lambda n: f"Guarnicao {n}")
    unidade = factory.Sequence(lambda n: f"Unidade {n}")
    codigo = factory.Sequence(lambda n: f"UNI-{n:03d}")


class UsuarioFactory(factory.Factory):
    """Factory para criar instâncias de usuário para testes.

    Gera usuários com dados aleatórios mas válidos para testes, com
    senhas hasheadas padrão e associação a uma guarnição.

    Attributes:
        nome: Nome sequencial do usuário (ex: "Usuario 1").
        matricula: Matrícula sequencial única (ex: "MAT00001").
        senha_hash: Hash da senha padrão "senha123" para todos os testes.
        guarnicao_id: ID da guarnição padrão (1).
        is_admin: Flag de administrador (False por padrão).
    """

    class Meta:
        model = Usuario

    nome = factory.Sequence(lambda n: f"Usuario {n}")
    matricula = factory.Sequence(lambda n: f"MAT{n:05d}")
    senha_hash = factory.LazyFunction(lambda: hash_senha("senha123"))
    guarnicao_id = 1
    is_admin = False
