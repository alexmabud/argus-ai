"""Testes unitários para o serviço RAG.

Valida montagem de prompt, descrição de abordagem e pipeline
de geração de relatório.
"""

from unittest.mock import MagicMock, patch

from app.services.rag_service import RAGService


class TestDescreverAbordagem:
    """Testes para geração de descrição textual da abordagem."""

    def test_abordagem_com_observacoes(self):
        """Deve incluir observações na descrição."""
        abordagem = MagicMock()
        abordagem.observacoes = "Indivíduo em atitude suspeita"
        abordagem.pessoas = []
        abordagem.veiculos = []

        # Criar instância sem __init__
        with patch.object(RAGService, "__init__", lambda self, *a, **kw: None):
            service = RAGService.__new__(RAGService)
            descricao = service._descrever_abordagem(abordagem)
            assert "Indivíduo em atitude suspeita" in descricao

    def test_abordagem_com_pessoas(self):
        """Deve incluir nomes das pessoas abordadas."""
        abordagem = MagicMock()
        abordagem.observacoes = None

        pessoa_mock = MagicMock()
        pessoa_mock.pessoa.nome = "João da Silva"
        abordagem.pessoas = [pessoa_mock]
        abordagem.veiculos = []

        with patch.object(RAGService, "__init__", lambda self, *a, **kw: None):
            service = RAGService.__new__(RAGService)
            descricao = service._descrever_abordagem(abordagem)
            assert "João da Silva" in descricao

    def test_abordagem_vazia(self):
        """Deve retornar texto padrão para abordagem sem dados."""
        abordagem = MagicMock()
        abordagem.observacoes = None
        abordagem.pessoas = []
        abordagem.veiculos = []

        with patch.object(RAGService, "__init__", lambda self, *a, **kw: None):
            service = RAGService.__new__(RAGService)
            descricao = service._descrever_abordagem(abordagem)
            assert descricao == "Abordagem policial"


class TestMontarPrompt:
    """Testes para montagem de prompt para o LLM."""

    def test_prompt_com_ocorrencias_e_legislacao(self):
        """Deve incluir seções de ocorrências e legislação no prompt."""
        abordagem = MagicMock()
        abordagem.id = 1

        oc = MagicMock()
        oc.numero_ocorrencia = "2024.00001"
        oc.texto_extraido = "Texto do BO"
        ocorrencias_ctx = [{"ocorrencia": oc, "similaridade": 0.85}]

        leg = MagicMock()
        leg.lei = "CP"
        leg.artigo = "157"
        leg.nome = "Roubo"
        leg.texto = "Subtrair coisa alheia..."
        legislacao_ctx = [{"legislacao": leg, "similaridade": 0.78}]

        with patch.object(RAGService, "__init__", lambda self, *a, **kw: None):
            service = RAGService.__new__(RAGService)
            prompt = service._montar_prompt(
                abordagem, "Descrição", ocorrencias_ctx, legislacao_ctx, ""
            )

            assert "2024.00001" in prompt
            assert "CP Art. 157" in prompt
            assert "EXCLUSIVAMENTE" in prompt

    def test_prompt_com_instrucao_usuario(self):
        """Deve incluir instrução adicional do usuário."""
        abordagem = MagicMock()
        abordagem.id = 1

        with patch.object(RAGService, "__init__", lambda self, *a, **kw: None):
            service = RAGService.__new__(RAGService)
            prompt = service._montar_prompt(abordagem, "Descrição", [], [], "Foque em trânsito")
            assert "Foque em trânsito" in prompt
