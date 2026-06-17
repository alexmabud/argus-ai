# Guia de Estudos — Argus AI
> Arquivo pessoal para entender o projeto do zero. Escrito em português, de forma simples.

---

## O que é o Argus AI?

É um sistema de apoio para equipes de patrulhamento policial. Pensa assim:

> **Problema:** Um policial faz centenas de abordagens por mês. Fica impossível lembrar de tudo. Quem foi abordado junto com quem? Aquela pessoa tem ocorrências antigas? Qual carro apareceu mais vezes na mesma área?
>
> **Solução:** O Argus AI é a **memória digital da guarnição**. Registra abordagens em menos de 40 segundos, reconhece rostos, faz buscas por voz, funciona sem internet, e usa IA para cruzar dados automaticamente.

---

## Conceitos Fundamentais (leia antes de tudo)

| Conceito | O que é | Não confundir com |
|----------|---------|-------------------|
| **Abordagem** | Registro de uma parada policial no campo (quem, onde, quando) | Ocorrência |
| **Ocorrência** | PDF oficial de um boletim de ocorrência importado do sistema | Abordagem |
| **Pessoa** | Pessoa que foi abordada (CPF criptografado) | Usuário do sistema |
| **Guarnição** | Equipe/viatura (é a unidade de isolamento dos dados) | Batalhão |
| **Batalhão (BPM)** | Agrupa várias guarnições | Guarnição |
| **Relacionamento** | Link automático entre pessoas que aparecem juntas | Vínculo Manual |
| **Vínculo Manual** | Link criado pelo usuário (ex: "cônjuge", "comparsa") | Relacionamento automático |

---

## A Arquitetura em Camadas

O projeto segue uma **arquitetura em camadas estrita**. Cada camada tem uma responsabilidade e **nunca pula camadas**:

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (PWA)                                                 │
│  HTML + Alpine.js + Tailwind                                    │
│  Faz chamadas HTTP para o backend                               │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP (JSON)
┌──────────────────────▼──────────────────────────────────────────┐
│  ROUTERS  (app/api/v1/)                                         │
│  Recebe a requisição HTTP, valida com Pydantic, chama o Service │
│  NUNCA tem lógica de negócio                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ chama
┌──────────────────────▼──────────────────────────────────────────┐
│  SERVICES  (app/services/)                                      │
│  Toda a lógica de negócio fica aqui                             │
│  NUNCA importa FastAPI (pode ser testado isoladamente)          │
└──────────────────────┬──────────────────────────────────────────┘
                       │ chama
┌──────────────────────▼──────────────────────────────────────────┐
│  REPOSITORIES  (app/repositories/)                              │
│  Só faz queries no banco de dados                               │
│  Aplica filtros de multi-tenancy e soft delete automaticamente  │
└──────────────────────┬──────────────────────────────────────────┘
                       │ usa
┌──────────────────────▼──────────────────────────────────────────┐
│  MODELS  (app/models/)                                          │
│  Definições das tabelas do banco (SQLAlchemy ORM)               │
│  Usa mixins para não repetir código                             │
└──────────────────────┬──────────────────────────────────────────┘
                       │ persiste em
┌──────────────────────▼──────────────────────────────────────────┐
│  POSTGRESQL 16                                                  │
│  + pgvector (busca por vetores/IA)                              │
│  + PostGIS (queries geoespaciais)                               │
│  + pg_trgm (busca fuzzy em nomes)                               │
└─────────────────────────────────────────────────────────────────┘
```

**Por que separar assim?**
- Posso testar o Service sem precisar de HTTP
- Posso trocar o banco sem mudar o Service
- Fica muito mais fácil de achar bugs (erro de lógica = Service, erro de query = Repository)

---

## Estrutura de Arquivos Completa

```
argus_ai/
│
├── app/                    ← TODO o backend Python (11.000+ linhas)
│   ├── main.py             ← Ponto de entrada da aplicação
│   ├── config.py           ← Configurações (variáveis de ambiente)
│   ├── dependencies.py     ← Injeção de dependência do FastAPI
│   ├── worker.py           ← Configuração do worker de background
│   │
│   ├── api/                ← CAMADA 1: Routers HTTP
│   │   ├── health.py       ← Endpoint /health (monitoramento)
│   │   └── v1/             ← API versionada em v1
│   │       ├── router.py   ← Junta todos os routers em um só
│   │       ├── auth.py     ← Login, registro, refresh, perfil
│   │       ├── pessoas.py  ← CRUD de pessoas abordadas
│   │       ├── veiculos.py ← CRUD de veículos
│   │       ├── abordagens.py ← CRUD de abordagens
│   │       ├── fotos.py    ← Upload de fotos, busca facial, OCR placa
│   │       ├── consultas.py ← Busca unificada
│   │       ├── ocorrencias.py ← Upload de PDF + busca semântica
│   │       ├── analytics.py ← Métricas do dashboard
│   │       ├── localidades.py ← Autocomplete de cidades/bairros
│   │       ├── sync.py     ← Sincronização offline em lote
│   │       └── admin.py    ← Gerenciamento de usuários/equipes
│   │
│   ├── models/             ← CAMADA 4: Tabelas do banco
│   │   ├── base.py         ← Mixins reutilizáveis (Timestamp, SoftDelete, MultiTenant)
│   │   ├── usuario.py      ← Policial/usuário do sistema
│   │   ├── guarnicao.py    ← Equipe/guarnição (raiz do multi-tenancy)
│   │   ├── bpm.py          ← Batalhão (agrupa guarnições)
│   │   ├── pessoa.py       ← Pessoa abordada (entidade central)
│   │   ├── endereco.py     ← Endereço com coordenada GPS (PostGIS)
│   │   ├── veiculo.py      ← Veículo (placa normalizada)
│   │   ├── abordagem.py    ← Registro de abordagem
│   │   ├── foto.py         ← Foto com embedding facial (512 dimensões)
│   │   ├── ocorrencia.py   ← PDF de ocorrência (embedding de texto 384 dim)
│   │   ├── localidade.py   ← Hierarquia geográfica (estado/cidade/bairro)
│   │   ├── relacionamento.py ← Link automático entre pessoas
│   │   ├── vinculo_manual.py ← Link manual criado pelo usuário
│   │   ├── pessoa_observacao.py ← Notas operacionais sobre uma pessoa
│   │   └── audit_log.py   ← Trilha de auditoria imutável
│   │
│   ├── schemas/            ← Pydantic: valida entrada e formata saída
│   │   ├── auth.py         ← LoginRequest, TokenResponse, etc.
│   │   ├── pessoa.py       ← PessoaCreate, PessoaResponse, etc.
│   │   ├── abordagem.py    ← AbordagemCreate, AbordagemResponse
│   │   ├── foto.py         ← FotoCreate, FacialSearchRequest
│   │   ├── ocorrencia.py   ← OcorrenciaCreate, OcorrenciaResponse
│   │   ├── consulta.py     ← UnifiedSearchRequest/Response
│   │   ├── sync.py         ← SyncBatchRequest (fila offline)
│   │   └── analytics.py    ← DashboardResponse, MetricsResponse
│   │
│   ├── services/           ← CAMADA 2: Lógica de negócio (22 serviços)
│   │   ├── auth_service.py ← Registro, login, refresh de token
│   │   ├── pessoa_service.py ← CRUD + criptografia de CPF
│   │   ├── veiculo_service.py ← CRUD de veículos
│   │   ├── abordagem_service.py ← CRUD + auto-vincula pessoas
│   │   ├── relacionamento_service.py ← UPSERT automático de relacionamentos
│   │   ├── vinculo_manual_service.py ← Links manuais
│   │   ├── pessoa_observacao_service.py ← Notas sobre pessoas
│   │   ├── ocorrencia_service.py ← Upload de PDF + extração
│   │   ├── embedding_service.py ← SentenceTransformers (384 dim) + cache Redis
│   │   ├── face_service.py ← InsightFace (512 dim)
│   │   ├── ocr_service.py  ← EasyOCR para placas
│   │   ├── foto_service.py ← Gerenciamento de fotos
│   │   ├── consulta_service.py ← Busca unificada (agrega resultados)
│   │   ├── storage_service.py ← Upload/download S3/MinIO/R2
│   │   ├── geocoding_service.py ← Reverter coordenada em endereço
│   │   ├── analytics_service.py ← Métricas e agregações do dashboard
│   │   ├── audit_service.py ← Registra toda ação no log imutável
│   │   ├── sync_service.py ← Deduplicação da fila offline (client_id)
│   │   ├── localidade_service.py ← Autocomplete geográfico
│   │   ├── usuario_admin_service.py ← Ciclo de vida de usuários
│   │   ├── equipe_service.py ← Gerenciamento de guarnições
│   │   └── bpm_service.py  ← Gerenciamento de batalhões
│   │
│   ├── repositories/       ← CAMADA 3: Acesso ao banco de dados
│   │   ├── base.py         ← CRUD genérico + soft delete + multi-tenancy
│   │   ├── pessoa_repo.py  ← Busca fuzzy por nome (pg_trgm), lookup CPF
│   │   ├── veiculo_repo.py ← Busca por placa
│   │   ├── abordagem_repo.py ← Queries + geoespacial (PostGIS)
│   │   ├── foto_repo.py    ← Similaridade vetorial (pgvector)
│   │   ├── ocorrencia_repo.py ← Busca semântica (pgvector)
│   │   ├── relacionamento_repo.py ← Links automáticos
│   │   ├── localidade_repo.py ← Lookup geográfico
│   │   └── audit_repo.py   ← Inserção de audit log (append-only)
│   │
│   ├── core/               ← Funcionalidades transversais (usado em todo lugar)
│   │   ├── security.py     ← JWT: criar/validar tokens, hash de senha
│   │   ├── crypto.py       ← Criptografia Fernet AES-256 (CPF)
│   │   ├── exceptions.py   ← Exceções customizadas da aplicação
│   │   ├── middleware.py   ← Logging, cabeçalhos de segurança HTTP
│   │   ├── rate_limit.py   ← Limite de requisições (slowapi)
│   │   ├── permissions.py  ← Verificação de papéis/permissões
│   │   └── upload_validation.py ← Validação de tipo e tamanho de arquivo
│   │
│   ├── tasks/              ← Jobs pesados rodando em background (arq worker)
│   │   ├── pdf_processor.py ← Extrai texto do PDF (PyMuPDF) e gera embedding
│   │   ├── face_processor.py ← Gera embedding facial 512 dim (InsightFace)
│   │   └── thumbnail_backfill.py ← Regenera thumbnails (Pillow)
│   │
│   ├── database/
│   │   └── session.py      ← Fábrica de conexões async com o PostgreSQL
│   │
│   └── utils/
│       ├── imaging.py      ← Gera thumbnails, converte formatos
│       └── s3.py           ← Helpers de upload S3
│
├── frontend/               ← PWA offline-first (HTML + Alpine.js)
│   ├── index.html          ← Shell do app (único HTML)
│   ├── manifest.json       ← Permite instalar como app no celular
│   ├── sw.js               ← Service Worker (cache + sync offline)
│   │
│   ├── js/
│   │   ├── app.js          ← App Alpine.js: roteamento e estado global
│   │   ├── api.js          ← Cliente HTTP (fetch + gerenciamento de JWT)
│   │   ├── auth.js         ← Armazena token no localStorage
│   │   ├── db.js           ← IndexedDB via Dexie.js (fila offline)
│   │   ├── sync.js         ← Gerencia o envio da fila quando voltar online
│   │   │
│   │   ├── pages/          ← Telas do aplicativo
│   │   │   ├── login.js
│   │   │   ├── abordagem-nova.js    ← Formulário rápido (< 40 seg)
│   │   │   ├── abordagem-detalhe.js ← Detalhes de uma abordagem
│   │   │   ├── consulta.js          ← Busca unificada
│   │   │   ├── pessoa-detalhe.js    ← Ficha da pessoa + relacionamentos
│   │   │   ├── dashboard.js         ← Gráficos com ApexCharts
│   │   │   ├── ocorrencias.js       ← Upload de PDF + listagem
│   │   │   ├── perfil.js            ← Editor de perfil do usuário
│   │   │   └── admin-usuarios.js    ← Admin: gerenciar usuários
│   │   │
│   │   └── components/     ← Módulos reutilizáveis de UI
│   │       ├── camera.js   ← Captura com WebRTC
│   │       ├── gps.js      ← API de Geolocalização (GPS automático)
│   │       ├── voice.js    ← Web Speech API (ditado por voz)
│   │       ├── ocr-placa.js ← Chama endpoint de OCR (EasyOCR)
│   │       ├── autocomplete.js ← Busca fuzzy com datalist
│   │       ├── offline-indicator.js ← Badge online/offline
│   │       └── sync-queue.js ← Contador de itens pendentes
│
├── tests/                  ← Testes automatizados (55+ arquivos)
│   ├── conftest.py         ← Fixtures + setup do banco de teste
│   ├── factories.py        ← FactoryBoy: gera dados falsos para teste
│   ├── unit/               ← Testa services e utils isoladamente
│   ├── integration/        ← Testa endpoints HTTP completos
│   └── repositories/       ← Testa as queries do banco
│
├── alembic/                ← Controle de versão do banco de dados
│   ├── env.py              ← Config do Alembic (lê os models automaticamente)
│   └── versions/           ← Cada arquivo = uma mudança no banco
│       ├── 001_softdelete.py
│       ├── 002_thumbnail.py
│       └── ...
│
├── scripts/                ← Scripts utilitários
│   ├── generate_encryption_key.py ← Gera chave Fernet (rode uma vez no deploy)
│   ├── anonimizar_dados.py ← LGPD: anonimiza dados com +5 anos
│   ├── reset_usuario.py    ← Reseta senha de um usuário
│   ├── backfill_thumbnails.py ← Regenera thumbnails de fotos antigas
│   └── deploy.sh           ← Script de deploy
│
├── docs/
│   ├── adr/                ← Decisões de arquitetura documentadas
│   │   ├── 001-offline-first.md   ← Por que usar IndexedDB
│   │   ├── 002-pgvector.md        ← Por que guardar embeddings no Postgres
│   │   └── 003-multi-tenancy.md   ← Como funciona o isolamento de dados
│   ├── API.md              ← Referência completa da API
│   ├── DEPLOY.md           ← Guia de deploy
│   └── LGPD.md             ← Conformidade com a lei
│
├── docker-compose.yml      ← Levanta 5 serviços (db, redis, minio, api, worker)
├── Dockerfile              ← Container da API
├── pyproject.toml          ← Dependências Python (95+)
├── Makefile                ← Atalhos de comandos (make dev, make test, etc)
├── .env.example            ← Template de variáveis de ambiente (80+ vars)
├── ARGUS_AI_SPEC.md        ← Especificação técnica completa
└── CLAUDE.md               ← Convenções de desenvolvimento

```

---

## Os Mixins — Código que Toda Tabela Herda

Em `app/models/base.py` existem 3 "mixins" (classes que você herda para ganhar funcionalidades prontas):

### TimestampMixin
```python
# Todo model que herda isso ganha automaticamente:
criado_em: datetime    # quando foi criado
atualizado_em: datetime  # quando foi atualizado pela última vez
```
**Por que:** Saber quando cada registro foi criado é básico para auditoria e ordenação.

---

### SoftDeleteMixin
```python
# Todo model que herda isso NÃO deleta dados, só marca como inativo:
ativo: bool = True           # False = deletado
desativado_em: datetime      # quando foi desativado
desativado_por_id: UUID      # quem desativou
```
**Por que:** LGPD exige que dados policiais sejam preservados. Nunca deletamos nada permanentemente. Se você "deletar" uma pessoa, ela fica com `ativo=False` e reaparece se necessário.

---

### MultiTenantMixin
```python
# Isola os dados por guarnição:
guarnicao_id: UUID   # dados dessa guarnição não aparecem para outras
```
**Por que:** A Guarnição A não pode ver os dados da Guarnição B. O filtro é aplicado automaticamente no Repository.

---

## Os 3 Bancos de Extensão do PostgreSQL

O projeto usa PostgreSQL 16 com 3 extensões especiais:

```
┌─────────────────────────────────────────────────────────────────┐
│  PostgreSQL 16                                                  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  pgvector    │  │   PostGIS    │  │      pg_trgm         │  │
│  │              │  │              │  │                      │  │
│  │ Armazena     │  │ Armazena     │  │ Busca fuzzy em       │  │
│  │ embeddings   │  │ coordenadas  │  │ texto (nomes)        │  │
│  │ de IA        │  │ GPS          │  │                      │  │
│  │              │  │              │  │ Ex: "João Silvo"     │  │
│  │ Fotos: 512   │  │ "Raio de     │  │ acha "João Silva"    │  │
│  │ dimensões    │  │ 500m do      │  │                      │  │
│  │              │  │ ponto X"     │  │ Tolerante a erros    │  │
│  │ Textos: 384  │  │              │  │ de digitação         │  │
│  │ dimensões    │  │ Mapa de      │  │                      │  │
│  │              │  │ calor        │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Como Funciona a IA no Sistema

O sistema tem **3 recursos de IA ativos**:

### 1. Embeddings de Ocorrências em PDF (base para busca semântica)
```
Policial faz upload de um PDF de ocorrência
    ↓
PDF vai para o arq worker (background)
    ↓
PyMuPDF extrai o texto do PDF
    ↓
SentenceTransformers converte o texto em 384 números (embedding)
    ↓
Esses 384 números são salvos no pgvector (coluna Ocorrencia.embedding)
```
> ⚠️ **Estado atual:** o embedding é **gerado e armazenado**, mas ainda **não há endpoint**
> que faça busca por similaridade de ocorrências. A busca atual (`GET /ocorrencias/buscar`)
> é textual: por nome, número RAP ou data. O método de busca vetorial já existe no
> repositório (`buscar_similares`), pronto para quando a feature for exposta.

### 2. Reconhecimento Facial
```
Foto é enviada
    ↓
InsightFace detecta o rosto na foto
    ↓
Converte o rosto em 512 números (embedding facial)
    ↓
Esses 512 números são salvos no pgvector (tabela fotos)
    ↓
Quando busca por rosto (POST /fotos/buscar-rosto)
    ↓
A foto de busca vira 512 números
    ↓
pgvector encontra fotos com rostos parecidos (distância < 0.6)
    ↓
Retorna as pessoas identificadas
```

### 3. OCR de Placas
```
Foto de veículo é enviada
    ↓
EasyOCR extrai o texto da placa
    ↓
Texto normalizado (remove espaços, maiúsculas)
    ↓
Retorna placa ex: "ABC1234" ou "ABC1D23" (Mercosul)
```

> **Nota:** não há geração de texto por LLM no sistema. As variáveis `LLM_PROVIDER`,
> `ANTHROPIC_API_KEY` e `OLLAMA_*` existem no `.env.example` mas estão **reservadas / sem
> uso** — não há `llm_service` nem `rag_service` no código.

---

## A Criptografia do CPF

O CPF é dado sensível (LGPD). O sistema usa **duas colunas** para um CPF:

```
┌─────────────────────────────────────────────────────────────────┐
│  Tabela: pessoas                                                │
│                                                                 │
│  cpf_encrypted = "gAAAAAB..."  (AES-256 Fernet)                │
│  ← Só consegue ler com a chave ENCRYPTION_KEY                  │
│  ← Exibido como "***.***.***-45" para o usuário                │
│                                                                 │
│  cpf_hash = "a3f4b2c1..."      (SHA-256)                       │
│  ← Não dá para descriptografar (é um hash)                     │
│  ← Usado para buscar: WHERE cpf_hash = hash('123.456.789-00')  │
│  ← Tem índice único (garante que não duplica CPF)              │
└─────────────────────────────────────────────────────────────────┘
```

**Por que duas colunas?**
- `cpf_encrypted`: Para quando precisar mostrar o CPF completo (caso específico)
- `cpf_hash`: Para buscas eficientes sem descriptografar

---

## Como Funciona a Autenticação (JWT)

```
1. Usuário faz POST /auth/login com usuário e senha
    ↓
2. Sistema verifica a senha com bcrypt
    ↓
3. Gera um session_id único e salva no banco (coluna usuarios.session_id)
    ↓
4. Gera dois tokens JWT:
   - access_token: válido por 8 horas (para requisições normais)
   - refresh_token: válido por 30 dias (para renovar o access_token)
    ↓
5. O session_id fica dentro do JWT (evita login duplo)
    ↓
6. Em toda requisição: valida JWT + compara session_id com o banco
    ↓
7. Se o usuário logar em outro device: session_id muda, o antigo é invalidado
```

**Sessão Exclusiva:** Um usuário só pode estar logado em um device por vez. Se logar em outro, o anterior é deslogado automaticamente.

---

## Como Funciona o Offline-First

O sistema funciona **sem internet**. Veja o fluxo:

```
Policial abre o app (sem internet)
    ↓
Service Worker já tem os assets em cache (funciona normalmente)
    ↓
Policial registra uma abordagem
    ↓
api.js tenta enviar para o servidor → FALHA (sem internet)
    ↓
sync.js intercepta o erro
    ↓
db.js salva a abordagem no IndexedDB (banco local no navegador)
    ↓
Cada item recebe um client_id (UUID único)
    ↓
sync-queue.js mostra "3 itens pendentes" no canto da tela
    ↓
Quando o internet voltar:
    ↓
Service Worker dispara o evento 'online'
    ↓
sync.js pega todos os itens do IndexedDB
    ↓
Faz POST /api/v1/sync/batch com todos de uma vez
    ↓
Backend verifica client_id de cada item (evita duplicatas)
    ↓
Processa e retorna quais foram salvos com sucesso
    ↓
sync.js remove os itens sincronizados do IndexedDB
```

---

## Como Funciona o Multi-Tenancy

Cada guarnição só vê os próprios dados:

```python
# No BaseRepository, toda query filtra por guarnicao_id:
SELECT * FROM pessoas
WHERE guarnicao_id = 'uuid-da-guarnicao'  ← filtro automático
AND ativo = true                           ← soft delete automático

# O service passa o guarnicao_id do usuário logado
# O repository aplica o filtro
# O router nunca precisa se preocupar com isso
```

---

## Como Funciona o Relacionamento Automático

Quando duas pessoas aparecem na mesma abordagem:

```
Abordagem registrada com Pessoa A e Pessoa B
    ↓
AbordagemService chama RelacionamentoService.materializar()
    ↓
UPSERT na tabela relacionamentos_pessoas:
  - Se não existia: cria com frequencia=1
  - Se já existia: incrementa frequencia, atualiza ultima_ocorrencia
    ↓
Resultado: A e B têm um relacionamento com frequencia=2
    ↓
Na ficha da pessoa: mostra "apareceu 2x com João Silva"
```

---

## O Background Worker (arq)

Algumas operações são pesadas demais para o usuário esperar (5-30 segundos). Essas vão para o worker:

```
Requisição HTTP chega → Router responde "processando..."
    ↓
Job é enviado para a fila Redis
    ↓
Worker (processo separado) pega o job
    ↓
Processa (PDF, embedding, face)
    ↓
Salva resultado no banco
    ↓
Próxima vez que o usuário abrir: resultado já está lá
```

**Jobs disponíveis:**
- `processar_pdf_task`: Extrai texto do PDF + gera embedding de 384 dim
- `processar_face_task`: Gera embedding facial de 512 dim (InsightFace)
- `gerar_thumbnail_backfill_task`: Regenera thumbnails de fotos antigas

---

## Os Comandos do Makefile

```bash
make dev          # Sobe banco + Redis + MinIO + API (hot reload)
make worker       # Sobe o worker de background
make test         # Roda todos os testes com cobertura
make lint         # Verifica código com ruff + mypy
make format       # Formata código com ruff
make migrate      # Aplica as migrations pendentes no banco
make migrate-create msg="descricao"  # Cria nova migration (autogenerate)
make seed         # Placeholder — não há dados de seed no projeto hoje
make docker-up    # Sobe os containers Docker
make docker-down  # Para os containers
make docker-logs  # Ver logs em tempo real
make encrypt-key  # Gera nova chave Fernet (use no primeiro deploy)
make init-db      # Cria as tabelas diretamente (sem Alembic)
make anonimizar   # LGPD: anonimiza dados com +5 anos
```

> 📖 Para entender a fundo os modos de execução (`make dev` x `docker compose up`),
> como os volumes guardam os dados, e como sincronizar a base da VM para testar
> localmente, veja **[docs/ambiente-local.md](ambiente-local.md)**.

---

## Fluxo Completo: Registrar uma Abordagem

Vamos rastrear o que acontece do clique até o banco:

```
[1] Policial abre app no celular
      ↓
[2] frontend/js/pages/abordagem-nova.js
    Formulário: nome, CPF, placa, localização (GPS automático), foto

[3] gps.js captura coordenadas automaticamente
    camera.js captura foto

[4] javascript faz:
    api.js → POST /api/v1/abordagens
    (com JWT no header Authorization: Bearer ...)

[5] app/api/v1/abordagens.py (Router)
    Valida token JWT (dependency: get_current_user)
    Valida body com Pydantic (schema AbordagemCreate)
    Chama: await abordagem_service.create(data, usuario_id, guarnicao_id)

[6] app/services/abordagem_service.py
    Verifica se as pessoas existem (ou cria)
    Verifica se os veículos existem (ou cria)
    Chama audit_service.log("criar_abordagem", ...)
    Chama abordagem_repo.create(abordagem_data)
    Chama relacionamento_service.materializar(pessoas_ids)

[7] app/repositories/abordagem_repo.py
    Cria Abordagem (com guarnicao_id automático)
    Cria AbordagemPessoa (tabela M:N)
    Cria AbordagemVeiculo (tabela M:N)
    Commit no banco

[8] PostgreSQL salva tudo
    tabelas: abordagens, abordagem_pessoa, abordagem_veiculo

[9] Service retorna AbordagemResponse
    Router serializa com Pydantic
    Frontend recebe JSON: { "id": "uuid", "data_hora": "...", ... }

[10] Se havia foto:
     Foto vai para arq worker
     Worker processa: InsightFace gera 512 números
     Salva embedding na tabela fotos
```

---

## As Tecnologias e Por Que Foram Escolhidas

### FastAPI — Framework Web
**O que faz:** Cria os endpoints HTTP da API.
**Por que:** É assíncrono (async/await), gera documentação automática (Swagger), usa Pydantic nativamente para validação, e é muito rápido.

### SQLAlchemy 2.0 Async — ORM
**O que faz:** Mapeia classes Python para tabelas do banco.
**Por que:** Versão 2.0 tem suporte completo a async, o que é essencial para o sistema não travar enquanto espera o banco responder.

### Pydantic v2 — Validação
**O que faz:** Valida dados de entrada e formata saídas da API.
**Por que:** Se o frontend mandar um CPF inválido, o Pydantic rejeita antes de chegar no Service. Integrado nativamente com FastAPI.

### Alembic — Migrations
**O que faz:** Controla as mudanças no esquema do banco.
**Por que:** Cada mudança no banco é um arquivo versionado. Permite reverter mudanças e aplicar em produção com segurança.

### arq — Background Worker
**O que faz:** Executa jobs pesados fora do ciclo HTTP.
**Por que:** Processar um PDF ou um rosto demora 10-30 segundos. Se fizesse na requisição HTTP, o usuário ficaria esperando. Com arq, a resposta é imediata e o processamento acontece em background.

### Redis — Cache e Fila
**O que faz:** Armazena dados temporários e serve como fila para o arq.
**Por que:** Dois usos: (1) cacheia os embeddings do SentenceTransformers (evita processar o mesmo texto duas vezes), (2) serve como fila de mensagens para o arq worker.

### pgvector — Busca Vetorial
**O que faz:** Extensão do PostgreSQL que armazena vetores e faz buscas de similaridade.
**Por que:** Mantém os dados de IA no mesmo banco que os dados operacionais. Simplifica backup, replicação e garante ACID. Alternativa seria um banco vetorial separado (Pinecone, Weaviate), mas adiciona complexidade.

### PostGIS — Geoespacial
**O que faz:** Extensão do PostgreSQL para coordenadas e geometrias.
**Por que:** Permite queries como "mostre todas as abordagens num raio de 500m desse ponto" ou "mapa de calor por bairro".

### SentenceTransformers — Embeddings de Texto
**O que faz:** Converte texto em um vetor de 384 números que captura o significado semântico.
**Por que:** Modelo multilíngue (funciona em português), leve o suficiente para rodar em CPU, e gera embeddings de qualidade para busca semântica.

### InsightFace — Reconhecimento Facial
**O que faz:** Detecta rostos em fotos e gera um vetor de 512 números por rosto.
**Por que:** Open-source, roda localmente (sem depender de API externa), e tem boa acurácia com modelo buffalo_l.

### EasyOCR — Reconhecimento de Texto em Imagens
**O que faz:** Lê texto de imagens, usado para extrair placas de veículos.
**Por que:** Suporta português, roda localmente, e é simples de usar.

### Alpine.js — Frontend Reativo
**O que faz:** Adiciona reatividade ao HTML sem precisar de React/Vue.
**Por que:** Muito leve (15kb), não precisa de build step, funciona com CDN. Perfeito para PWA onde tamanho do bundle importa.

### Dexie.js — IndexedDB Wrapper
**O que faz:** Simplifica o uso do IndexedDB (banco local do navegador).
**Por que:** API nativa do IndexedDB é muito verbosa. Dexie oferece Promise-based API simples.

### Fernet (cryptography) — Criptografia
**O que faz:** Criptografia AES-256 bidirecional (você pode descriptografar).
**Por que:** CPF precisa ser armazenado de forma que, se necessário, possa ser revelado (ex: para o titular dos dados pedir seus dados — LGPD Art. 18). SHA-256 sozinho não permitiria isso.

---

## Os Schemas Pydantic — O Contrato da API

Schemas definem o formato exato das requisições e respostas. Existe um padrão:

```python
# Sempre tem 3 tipos de schema para cada entidade:

class PessoaCreate(BaseModel):
    # Dados que o cliente ENVIA para criar
    nome: str
    cpf: str | None
    data_nascimento: date | None

class PessoaUpdate(BaseModel):
    # Dados que o cliente ENVIA para atualizar (tudo opcional)
    nome: str | None = None
    data_nascimento: date | None = None

class PessoaResponse(BaseModel):
    # Dados que o servidor RETORNA (nunca retorna CPF completo)
    id: UUID
    nome: str
    cpf_mascarado: str  # "***.***.***-00"
    criado_em: datetime
```

---

## Os Testes — Como Funciona

```
tests/
├── conftest.py        ← Define fixtures compartilhadas (banco de teste, usuário logado, etc)
├── factories.py       ← Cria dados falsos (FactoryBoy)
│
├── unit/              ← Testa serviços isoladamente (sem banco real)
│   └── test_auth.py   ← Testa o AuthService diretamente
│
├── integration/       ← Testa a API completa (com banco real)
│   └── test_api_auth.py ← Faz POST /auth/login e verifica resposta
│
└── repositories/      ← Testa queries do banco
    └── test_ocorrencia_repo.py
```

**Como rodar:**
```bash
make test              # Roda todos
pytest tests/unit/     # Só unit tests
pytest tests/integration/test_api_auth.py  # Um arquivo específico
pytest -k "test_login" # Testa funções com "test_login" no nome
```

---

## O Docker — Os 5 Serviços

```
docker-compose.yml

┌─────────────────────────────────────────────────────────────────┐
│  db       → PostgreSQL 16 com pgvector + PostGIS + pg_trgm     │
│             Porta: 5432                                         │
│             Dados persistem em volume Docker                    │
├─────────────────────────────────────────────────────────────────┤
│  redis    → Redis 7                                             │
│             Porta: 6379                                         │
│             Cache de embeddings + fila do arq                  │
├─────────────────────────────────────────────────────────────────┤
│  minio    → MinIO (S3 compatível)                               │
│             Porta: 9000 (API) + 9001 (Console web)             │
│             Armazena fotos e PDFs em desenvolvimento           │
├─────────────────────────────────────────────────────────────────┤
│  api      → FastAPI + Uvicorn                                   │
│             Porta: 8000                                         │
│             Hot reload em desenvolvimento                       │
├─────────────────────────────────────────────────────────────────┤
│  worker   → arq worker                                          │
│             Sem porta exposta                                   │
│             Processa jobs pesados (PDF, face, embedding)        │
└─────────────────────────────────────────────────────────────────┘
```

Em **produção**, MinIO é substituído pelo Cloudflare R2 (mais barato e gerenciado).

---

## As Variáveis de Ambiente Mais Importantes

```bash
# Banco de dados
DATABASE_URL=postgresql+asyncpg://argus:senha@localhost:5432/argus_db

# Redis (cache + fila)
REDIS_URL=redis://localhost:6379

# Segurança
SECRET_KEY=<string longa aleatória>     # Para assinar os JWT
ENCRYPTION_KEY=<chave Fernet>           # Para criptografar CPF

# Storage
S3_ENDPOINT=http://minio:9000           # MinIO local
S3_PUBLIC_URL=http://localhost:9000     # URL pública para o browser

# IA — embeddings locais (busca de ocorrências + reconhecimento facial)
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2  # SentenceTransformers
FACE_SIMILARITY_THRESHOLD=0.6                          # Limiar do reconhecimento facial
# LLM_PROVIDER / ANTHROPIC_API_KEY / OLLAMA_* existem no .env.example mas estão
# RESERVADAS — não há serviço LLM no código hoje

# Configurações
ACCESS_TOKEN_EXPIRE_MINUTES=480         # 8 horas
REFRESH_TOKEN_EXPIRE_DAYS=30            # 30 dias
DATA_RETENTION_DAYS=1825                # 5 anos (LGPD)
```

---

## As Decisões de Arquitetura (ADRs)

Na pasta `docs/adr/` ficam documentados os "porquês" das grandes decisões:

### ADR 001 — Por que Offline-First?
**Problema:** Policiais patrulham áreas sem sinal de internet.
**Decisão:** IndexedDB no frontend + `/sync/batch` idempotente no backend.
**Detalhe importante:** Cada item offline tem um `client_id` (UUID). O backend verifica antes de inserir — se o mesmo `client_id` já existe, ignora (evita duplicata ao reenviar).

### ADR 002 — Por que pgvector em vez de banco vetorial separado?
**Problema:** Precisamos de busca semântica nos PDFs e reconhecimento facial.
**Decisão:** Guardar embeddings no próprio PostgreSQL (extensão pgvector).
**Por que não Pinecone/Weaviate:** Adicionaria um serviço extra para manter. Com pgvector, um SELECT já pode filtrar por guarnição E buscar por similaridade na mesma query.

### ADR 003 — Como isolar dados por guarnição?
**Problema:** Guarnição A não pode ver dados da Guarnição B.
**Decisão:** Coluna `guarnicao_id` em todas as tabelas relevantes + filtro no BaseRepository.
**Por que não Row-Level Security do Postgres:** Mais simples de debugar e testar na camada Python.

---

## Como Estudar Este Projeto (Roteiro Sugerido)

### Semana 1 — Entender a base
1. Leia `ARGUS_AI_SPEC.md` (visão geral completa)
2. Rode `make dev` e abra `http://localhost:8000/docs` (Swagger auto-gerado)
3. Leia `app/models/base.py` (os 3 mixins)
4. Leia `app/models/pessoa.py` (modelo central)
5. Leia `app/models/abordagem.py` (o registro mais importante)

### Semana 2 — Entender a camada de dados
1. Leia `app/repositories/base.py` (CRUD genérico)
2. Leia `app/repositories/pessoa_repo.py` (busca fuzzy + CPF hash)
3. Leia `app/repositories/foto_repo.py` (pgvector similarity)
4. Leia `alembic/versions/` (como o banco evolui)

### Semana 3 — Entender a lógica de negócio
1. Leia `app/services/auth_service.py` (login completo)
2. Leia `app/services/abordagem_service.py` (registro completo)
3. Leia `app/services/relacionamento_service.py` (auto-links)
4. Leia `app/services/embedding_service.py` (como a IA funciona)

### Semana 4 — Entender o frontend
1. Leia `frontend/js/app.js` (roteamento)
2. Leia `frontend/js/api.js` (como chama o backend)
3. Leia `frontend/js/db.js` + `sync.js` (offline)
4. Leia `frontend/js/pages/abordagem-nova.js` (formulário principal)

### A qualquer hora
- Rode `make test` e leia os testes — eles explicam o comportamento esperado
- Use `http://localhost:8000/docs` para experimentar os endpoints
- Leia `docs/adr/` para entender os "porquês"

---

## Tabela de Referência Rápida

| Se quiser entender... | Leia... |
|----------------------|---------|
| Por que o sistema existe | `README.md` + topo deste arquivo |
| A estrutura completa | `ARGUS_AI_SPEC.md` |
| Como adicionar endpoint | `app/api/v1/pessoas.py` (modelo) |
| Como adicionar lógica | `app/services/pessoa_service.py` (modelo) |
| Como fazer query no banco | `app/repositories/pessoa_repo.py` (modelo) |
| Como criar tabela nova | `app/models/pessoa.py` + `make migrate` |
| Como funciona o login | `app/core/security.py` + `app/services/auth_service.py` |
| Como funciona a IA | `app/services/embedding_service.py` + `app/services/face_service.py` |
| Como funciona offline | `frontend/js/sync.js` + `app/services/sync_service.py` |
| Como funciona multi-tenancy | `app/models/base.py` + `app/repositories/base.py` |
| Como funciona LGPD | `app/core/crypto.py` + `scripts/anonimizar_dados.py` |
| Como rodar testes | `tests/conftest.py` + `make test` |
| Como fazer deploy | `docs/DEPLOY.md` + `scripts/deploy.sh` |

---

*Arquivo criado em 2026-05-13 para estudo pessoal do projeto Argus AI.*
