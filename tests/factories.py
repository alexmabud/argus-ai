"""Factories para geração de dados de teste.

Fornece factories baseadas em factory_boy para criar instâncias de modelos
com dados aleatórios mas válidos, facilitando a criação de fixtures e dados
de teste sem duplicação de código.
"""

from datetime import UTC, datetime

import factory

from app.core.security import hash_senha
from app.models.abordagem import Abordagem
from app.models.foto import Foto
from app.models.guarnicao import Guarnicao
from app.models.passagem import Passagem
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.veiculo import Veiculo


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


class PessoaFactory(factory.Factory):
    """Factory para criar instâncias de pessoa para testes.

    Gera pessoas com nomes sequenciais e guarnicao_id padrão.
    CPF não é gerado por padrão — testar criptografia manualmente.

    Attributes:
        nome: Nome sequencial (ex: "Pessoa 1").
        guarnicao_id: ID da guarnição padrão (1).
    """

    class Meta:
        model = Pessoa

    nome = factory.Sequence(lambda n: f"Pessoa {n}")
    guarnicao_id = 1


class VeiculoFactory(factory.Factory):
    """Factory para criar instâncias de veículo para testes.

    Gera veículos com placas sequenciais no padrão Mercosul e dados básicos.

    Attributes:
        placa: Placa sequencial (ex: "TST0A01").
        modelo: Modelo padrão ("Gol").
        cor: Cor padrão ("Branco").
        guarnicao_id: ID da guarnição padrão (1).
    """

    class Meta:
        model = Veiculo

    placa = factory.Sequence(lambda n: f"TST{n:01d}A{n:02d}")
    modelo = "Gol"
    cor = "Branco"
    guarnicao_id = 1


class AbordagemFactory(factory.Factory):
    """Factory para criar instâncias de abordagem para testes.

    Gera abordagens com data/hora UTC e coordenadas padrão do Rio de Janeiro.

    Attributes:
        data_hora: Data/hora UTC atual.
        latitude: Latitude padrão (-22.9068 — Rio de Janeiro).
        longitude: Longitude padrão (-43.1729 — Rio de Janeiro).
        endereco_texto: Endereço padrão de teste.
        usuario_id: ID do usuário padrão (1).
        guarnicao_id: ID da guarnição padrão (1).
    """

    class Meta:
        model = Abordagem

    data_hora = factory.LazyFunction(lambda: datetime.now(UTC))
    latitude = -22.9068
    longitude = -43.1729
    endereco_texto = "Av. Brasil, 1000 - Centro, Rio de Janeiro"
    usuario_id = 1
    guarnicao_id = 1


class PassagemFactory(factory.Factory):
    """Factory para criar instâncias de passagem (tipo penal) para testes.

    Gera passagens com artigos sequenciais do Código Penal.

    Attributes:
        lei: Lei padrão ("CP" — Código Penal).
        artigo: Artigo sequencial (ex: "121", "122", ...).
        nome_crime: Nome do crime sequencial.
    """

    class Meta:
        model = Passagem

    lei = "CP"
    artigo = factory.Sequence(lambda n: str(121 + n))
    nome_crime = factory.Sequence(lambda n: f"Crime Tipo {n}")


class FotoFactory(factory.Factory):
    """Factory para criar instâncias de foto para testes.

    Gera fotos com URLs sequenciais e tipo padrão "rosto".

    Attributes:
        arquivo_url: URL sequencial da foto em S3.
        tipo: Tipo padrão ("rosto").
        data_hora: Data/hora UTC atual.
    """

    class Meta:
        model = Foto

    arquivo_url = factory.Sequence(lambda n: f"https://r2.example.com/fotos/foto_{n}.jpg")
    tipo = "rosto"
    data_hora = factory.LazyFunction(lambda: datetime.now(UTC))
