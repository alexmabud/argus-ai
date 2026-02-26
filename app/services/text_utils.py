"""Utilitários de chunking de texto para processamento de documentos.

Fornece funções para dividir textos de Boletins de Ocorrência (BO)
em chunks semânticos por seção, com fallback para divisão por
parágrafos com overlap. Usado no pipeline RAG para preparar contexto
e no processamento de PDFs.
"""

import re


def chunk_text_semantico(texto: str) -> list[dict]:
    """Divide texto de BO por seções semânticas estruturais.

    Reconhece cabeçalhos típicos de Boletins de Ocorrência (histórico,
    envolvidos, providências, objetos, local, conclusão) via regex.
    Se menos de 2 seções forem encontradas, faz fallback para
    chunk_text_paragrafos.

    Args:
        texto: Texto completo extraído do PDF.

    Returns:
        Lista de dicts com chaves: texto, tipo ("secao_bo" ou "paragrafo"),
        posicao (índice sequencial).
    """
    secoes_bo = [
        r"(?i)(hist[óo]rico|relato|narrativa|descri[çc][ãa]o dos fatos)",
        r"(?i)(envolvidos?|autor|v[íi]tima|testemunha|conduzido)",
        r"(?i)(provid[êe]ncias|encaminhamento|destino)",
        r"(?i)(objetos?|apreens[ãa]o|material)",
        r"(?i)(local|endere[çc]o|cena do crime)",
        r"(?i)(conclus[ãa]o|desfecho|resultado)",
    ]

    texto_limpo = texto.strip()
    if not texto_limpo:
        return []

    secoes_encontradas = []
    for pattern in secoes_bo:
        for match in re.finditer(pattern, texto_limpo):
            secoes_encontradas.append(match.start())

    if len(secoes_encontradas) < 2:
        return chunk_text_paragrafos(texto_limpo)

    secoes_encontradas.sort()
    secoes_encontradas.append(len(texto_limpo))

    chunks: list[dict] = []
    for i in range(len(secoes_encontradas) - 1):
        inicio = secoes_encontradas[i]
        fim = secoes_encontradas[i + 1]
        trecho = texto_limpo[inicio:fim].strip()
        if len(trecho) > 50:
            chunks.append(
                {
                    "texto": trecho,
                    "tipo": "secao_bo",
                    "posicao": i,
                }
            )

    return chunks if chunks else chunk_text_paragrafos(texto_limpo)


def chunk_text_paragrafos(
    texto: str,
    max_tokens: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """Divide texto em chunks por parágrafos com overlap.

    Fallback para textos sem estrutura de BO. Agrupa parágrafos até
    atingir max_tokens palavras, depois cria novo chunk mantendo
    overlap palavras do chunk anterior para preservar contexto.

    Args:
        texto: Texto para dividir em chunks.
        max_tokens: Número máximo de palavras por chunk (aproximação
            de tokens — português ~1.3 tokens/palavra).
        overlap: Número de palavras do final do chunk anterior a
            manter no início do próximo para continuidade.

    Returns:
        Lista de dicts com chaves: texto, tipo ("paragrafo"),
        posicao (índice sequencial).
    """
    paragrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
    if not paragrafos:
        paragrafos = [p.strip() for p in texto.split("\n") if p.strip()]

        if not paragrafos:
            return (
                [{"texto": texto.strip(), "tipo": "paragrafo", "posicao": 0}]
                if texto.strip()
                else []
            )

        chunks: list[dict] = []

        buffer = ""

        buffer_words = 0

    for paragrafo in paragrafos:
        words = len(paragrafo.split())
        if buffer_words + words > max_tokens and buffer:
            chunks.append(
                {
                    "texto": buffer.strip(),
                    "tipo": "paragrafo",
                    "posicao": len(chunks),
                }
            )
            overlap_text = " ".join(buffer.split()[-overlap:])
            buffer = overlap_text + "\n\n" + paragrafo
            buffer_words = len(buffer.split())
        else:
            buffer = buffer + "\n\n" + paragrafo if buffer else paragrafo
            buffer_words += words

    if buffer.strip():
        chunks.append(
            {
                "texto": buffer.strip(),
                "tipo": "paragrafo",
                "posicao": len(chunks),
            }
        )

    return chunks
