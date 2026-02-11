import factory

from app.core.security import hash_senha
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


class GuarnicaoFactory(factory.Factory):
    class Meta:
        model = Guarnicao

    nome = factory.Sequence(lambda n: f"Guarnicao {n}")
    unidade = factory.Sequence(lambda n: f"Unidade {n}")
    codigo = factory.Sequence(lambda n: f"UNI-{n:03d}")


class UsuarioFactory(factory.Factory):
    class Meta:
        model = Usuario

    nome = factory.Sequence(lambda n: f"Usuario {n}")
    matricula = factory.Sequence(lambda n: f"MAT{n:05d}")
    senha_hash = factory.LazyFunction(lambda: hash_senha("senha123"))
    guarnicao_id = 1
    is_admin = False
