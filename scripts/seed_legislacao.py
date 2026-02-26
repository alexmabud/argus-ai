"""Script de seed para popular legislação com embeddings.

Insere artigos do Código Penal, Lei de Drogas, Código de Trânsito,
Lei Maria da Penha e Estatuto do Desarmamento na tabela de legislação.
Gera embeddings via SentenceTransformers e armazena no pgvector.

Uso:
    python -m scripts.seed_legislacao
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed_legislacao")

# Legislação essencial para operações policiais
# ruff: noqa: E501
LEGISLACAO_DATA = [
    # Código Penal (CP)
    {
        "lei": "CP",
        "artigo": "121",
        "nome": "Homicídio simples",
        "texto": "Matar alguém. Pena - reclusão, de seis a vinte anos.",
    },
    {
        "lei": "CP",
        "artigo": "129",
        "nome": "Lesão corporal",
        "texto": "Ofender a integridade corporal ou a saúde de outrem. Pena - detenção, de três meses a um ano.",
    },
    {
        "lei": "CP",
        "artigo": "155",
        "nome": "Furto",
        "texto": "Subtrair, para si ou para outrem, coisa alheia móvel. Pena - reclusão, de um a quatro anos, e multa.",
    },
    {
        "lei": "CP",
        "artigo": "157",
        "nome": "Roubo",
        "texto": "Subtrair coisa móvel alheia, para si ou para outrem, mediante grave ameaça ou violência a pessoa, ou depois de havê-la, por qualquer meio, reduzido à impossibilidade de resistência. Pena - reclusão, de quatro a dez anos, e multa.",
    },
    {
        "lei": "CP",
        "artigo": "158",
        "nome": "Extorsão",
        "texto": "Constranger alguém, mediante violência ou grave ameaça, e com o intuito de obter para si ou para outrem indevida vantagem econômica, a fazer, tolerar que se faça ou deixar de fazer alguma coisa. Pena - reclusão, de quatro a dez anos, e multa.",
    },
    {
        "lei": "CP",
        "artigo": "171",
        "nome": "Estelionato",
        "texto": "Obter, para si ou para outrem, vantagem ilícita, em prejuízo alheio, induzindo ou mantendo alguém em erro, mediante artifício, ardil, ou qualquer outro meio fraudulento. Pena - reclusão, de um a cinco anos, e multa.",
    },
    {
        "lei": "CP",
        "artigo": "180",
        "nome": "Receptação",
        "texto": "Adquirir, receber, transportar, conduzir ou ocultar, em proveito próprio ou alheio, coisa que sabe ser produto de crime, ou influir para que terceiro, de boa-fé, a adquira, receba ou oculte. Pena - reclusão, de um a quatro anos, e multa.",
    },
    {
        "lei": "CP",
        "artigo": "147",
        "nome": "Ameaça",
        "texto": "Ameaçar alguém, por palavra, escrito ou gesto, ou qualquer outro meio simbólico, de causar-lhe mal injusto e grave. Pena - detenção, de um a seis meses, ou multa.",
    },
    {
        "lei": "CP",
        "artigo": "213",
        "nome": "Estupro",
        "texto": "Constranger alguém, mediante violência ou grave ameaça, a ter conjunção carnal ou a praticar ou permitir que com ele se pratique outro ato libidinoso. Pena - reclusão, de seis a dez anos.",
    },
    {
        "lei": "CP",
        "artigo": "311",
        "nome": "Adulteração de sinal identificador de veículo",
        "texto": "Adulterar ou remarcar número de chassi ou qualquer sinal identificador de veículo automotor, de seu componente ou equipamento. Pena - reclusão, de três a seis anos, e multa.",
    },
    {
        "lei": "CP",
        "artigo": "330",
        "nome": "Desobediência",
        "texto": "Desobedecer a ordem legal de funcionário público. Pena - detenção, de quinze dias a seis meses, e multa.",
    },
    {
        "lei": "CP",
        "artigo": "331",
        "nome": "Desacato",
        "texto": "Desacatar funcionário público no exercício da função ou em razão dela. Pena - detenção, de seis meses a dois anos, ou multa.",
    },
    # Lei de Drogas (Lei 11.343/06)
    {
        "lei": "Lei 11343/06",
        "artigo": "28",
        "nome": "Porte de drogas para consumo pessoal",
        "texto": "Quem adquirir, guardar, tiver em depósito, transportar ou trouxer consigo, para consumo pessoal, drogas sem autorização ou em desacordo com determinação legal ou regulamentar será submetido às seguintes penas: I - advertência sobre os efeitos das drogas; II - prestação de serviços à comunidade; III - medida educativa de comparecimento a programa ou curso educativo.",
    },
    {
        "lei": "Lei 11343/06",
        "artigo": "33",
        "nome": "Tráfico de drogas",
        "texto": "Importar, exportar, remeter, preparar, produzir, fabricar, adquirir, vender, expor à venda, oferecer, ter em depósito, transportar, trazer consigo, guardar, prescrever, ministrar, entregar a consumo ou fornecer drogas, ainda que gratuitamente, sem autorização ou em desacordo com determinação legal ou regulamentar. Pena - reclusão de 5 a 15 anos e pagamento de 500 a 1.500 dias-multa.",
    },
    {
        "lei": "Lei 11343/06",
        "artigo": "35",
        "nome": "Associação para o tráfico",
        "texto": "Associarem-se duas ou mais pessoas para o fim de praticar, reiteradamente ou não, qualquer dos crimes previstos nos arts. 33, caput e § 1º, e 34 desta Lei. Pena - reclusão, de 3 a 10 anos, e pagamento de 700 a 1.200 dias-multa.",
    },
    # Código de Trânsito Brasileiro (CTB)
    {
        "lei": "CTB",
        "artigo": "165",
        "nome": "Dirigir sob influência de álcool",
        "texto": "Dirigir sob a influência de álcool ou de qualquer outra substância psicoativa que determine dependência. Infração gravíssima (multa 10x), suspensão do direito de dirigir por 12 meses, retenção do veículo até apresentação de condutor habilitado e recolhimento do documento de habilitação.",
    },
    {
        "lei": "CTB",
        "artigo": "306",
        "nome": "Embriaguez ao volante (crime)",
        "texto": "Conduzir veículo automotor com capacidade psicomotora alterada em razão da influência de álcool ou de outra substância psicoativa que determine dependência. Pena - detenção, de seis meses a três anos, multa e suspensão ou proibição de se obter a permissão ou a habilitação para dirigir veículo automotor.",
    },
    {
        "lei": "CTB",
        "artigo": "309",
        "nome": "Dirigir sem habilitação",
        "texto": "Dirigir veículo automotor, em via pública, sem a devida Permissão para Dirigir ou Habilitação ou, ainda, se cassado o direito de dirigir, gerando perigo de dano. Pena - detenção, de seis meses a um ano, ou multa.",
    },
    # Estatuto do Desarmamento (Lei 10.826/03)
    {
        "lei": "Lei 10826/03",
        "artigo": "12",
        "nome": "Posse irregular de arma de fogo",
        "texto": "Possuir ou manter sob sua guarda arma de fogo, acessório ou munição, de uso permitido, em desacordo com determinação legal ou regulamentar, no interior de sua residência ou dependência desta, ou, ainda no seu local de trabalho, desde que seja o titular ou o responsável legal do estabelecimento ou empresa. Pena – detenção, de 1 a 3 anos, e multa.",
    },
    {
        "lei": "Lei 10826/03",
        "artigo": "14",
        "nome": "Porte ilegal de arma de fogo de uso permitido",
        "texto": "Portar, deter, adquirir, fornecer, receber, ter em depósito, transportar, ceder, ainda que gratuitamente, emprestar, remeter, empregar, manter sob guarda ou ocultar arma de fogo, acessório ou munição, de uso permitido, sem autorização e em desacordo com determinação legal ou regulamentar. Pena – reclusão, de 2 a 4 anos, e multa.",
    },
    {
        "lei": "Lei 10826/03",
        "artigo": "16",
        "nome": "Posse ou porte ilegal de arma de fogo de uso restrito",
        "texto": "Possuir, deter, portar, adquirir, fornecer, receber, ter em depósito, transportar, ceder, ainda que gratuitamente, emprestar, remeter, empregar, manter sob sua guarda ou ocultar arma de fogo, acessório ou munição de uso proibido ou restrito, sem autorização e em desacordo com determinação legal ou regulamentar. Pena – reclusão, de 3 a 6 anos, e multa.",
    },
    # Lei Maria da Penha (Lei 11.340/06)
    {
        "lei": "Lei 11340/06",
        "artigo": "5",
        "nome": "Violência doméstica e familiar contra a mulher",
        "texto": "Para os efeitos desta Lei, configura violência doméstica e familiar contra a mulher qualquer ação ou omissão baseada no gênero que lhe cause morte, lesão, sofrimento físico, sexual ou psicológico e dano moral ou patrimonial: I - no âmbito da unidade doméstica; II - no âmbito da família; III - em qualquer relação íntima de afeto.",
    },
    {
        "lei": "Lei 11340/06",
        "artigo": "22",
        "nome": "Medidas protetivas de urgência ao agressor",
        "texto": "Constatada a prática de violência doméstica e familiar contra a mulher, o juiz poderá aplicar, de imediato, ao agressor, em conjunto ou separadamente, as seguintes medidas protetivas de urgência: I - suspensão da posse ou restrição do porte de armas; II - afastamento do lar; III - proibição de aproximação da ofendida; IV - proibição de contato; V - proibição de frequentar determinados lugares; VI - restrição ou suspensão de visitas aos dependentes menores; VII - prestação de alimentos provisionais ou provisórios.",
    },
]


async def seed() -> None:
    """Executa seed de legislação com geração de embeddings.

    Conecta ao banco, insere artigos via UPSERT (lei+artigo)
    e gera embeddings em batch via SentenceTransformers.
    """
    from sqlalchemy import select

    from app.database.session import AsyncSessionLocal
    from app.models.legislacao import Legislacao
    from app.services.embedding_service import EmbeddingService

    logger.info("Iniciando seed de legislação...")

    # Carregar modelo de embeddings
    embedding_service = EmbeddingService()

    async with AsyncSessionLocal() as db:
        criados = 0
        atualizados = 0

        for item in LEGISLACAO_DATA:
            # Verificar se já existe (UPSERT por lei+artigo)
            result = await db.execute(
                select(Legislacao).where(
                    Legislacao.lei == item["lei"],
                    Legislacao.artigo == item["artigo"],
                )
            )
            existente = result.scalar_one_or_none()

            if existente:
                existente.nome = item["nome"]
                existente.texto = item["texto"]
                existente.ativo = True
                atualizados += 1
            else:
                legislacao = Legislacao(
                    lei=item["lei"],
                    artigo=item["artigo"],
                    nome=item["nome"],
                    texto=item["texto"],
                )
                db.add(legislacao)
                criados += 1

            await db.flush()

        # Gerar embeddings em batch
        logger.info("Gerando embeddings para %d artigos...", len(LEGISLACAO_DATA))

        result = await db.execute(
            select(Legislacao).where(
                Legislacao.ativo == True  # noqa: E712
            )
        )
        todas = result.scalars().all()

        textos = [f"{leg.lei} Art. {leg.artigo}: {leg.texto}" for leg in todas]
        embeddings = embedding_service.gerar_embeddings_batch(textos)

        for leg, emb in zip(todas, embeddings):
            leg.embedding = emb

        await db.commit()

        logger.info(
            "Seed concluído: %d criados, %d atualizados, %d embeddings gerados",
            criados,
            atualizados,
            len(todas),
        )


if __name__ == "__main__":
    asyncio.run(seed())
