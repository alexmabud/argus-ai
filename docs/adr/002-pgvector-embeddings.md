# ADR 002 — pgvector para Embeddings Vetoriais

## Status
Aceito

## Contexto
O sistema precisa de busca por similaridade semântica (textos de ocorrência e legislação) e facial (reconhecimento de pessoas). As opções avaliadas foram: pgvector (PostgreSQL), Pinecone, Weaviate, FAISS.

## Decisão
Usar pgvector como banco vetorial integrado ao PostgreSQL, evitando infraestrutura adicional.

### Embeddings
- **Texto (384-dim)**: SentenceTransformers `paraphrase-multilingual-MiniLM-L12-v2` para busca semântica em português
- **Face (512-dim)**: InsightFace `buffalo_l` para reconhecimento facial

### Busca
- Operador `<=>` (distância cosseno) para similaridade
- Índices IVFFlat para performance em escala
- Threshold configurável (texto: 0.3, face: 0.6)

## Consequências
- Sem infraestrutura adicional (tudo no PostgreSQL)
- Queries SQL padrão com joins entre vetores e dados relacionais
- Performance adequada para volumes de guarnição (milhares, não milhões)
- Limitação: escala massiva exigiria banco vetorial dedicado
