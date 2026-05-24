# 📊 Manual de Monitoramento — Argus AI

Guia para entender os alertas, ler o dashboard do Grafana e diagnosticar problemas em produção. Escrito em linguagem direta, sem assumir conhecimento prévio de Prometheus.

---

## 📍 Acessos rápidos

| O quê | Onde |
|---|---|
| Dashboard | https://arguseye.duckdns.org/grafana |
| Login Grafana | `admin` / senha em `.env` do servidor (`GF_ADMIN_PASSWORD`) |
| Alertas | sidebar → 🔔 **Alerting** → **Alert rules** |
| SSH no servidor | `ssh argus` (alias em `~/.ssh/config`) |
| Backup das chaves SSH | Google Drive → cofre Cryptomator → pasta `Chaves Argus` |

---

## 📱 Como os alertas chegam no Telegram

Cada alerta dispara uma mensagem com **emoji + título + descrição + horário**.
Quando volta ao normal, vem uma mensagem `✅ RESOLVIDO`.

| Emoji | Significado |
|---|---|
| 🔴 | `critical` — algo grave, ação imediata |
| ⚠️ | `warning` — atenção, mas não urgente |
| ✅ | resolvido |

São **15 regras de alerta** ativas, divididas em 4 grupos.

---

## 🖥️ Grupo 1: Infraestrutura da VM (5 alertas)

### ⚠️ CPU Alta
- **Dispara**: CPU média > **85%** por **5 minutos**
- **Significa**: a VM tá trabalhando duro. Pode ser worker processando lote de fotos, importação de PDF, ou algo travado em loop
- **Investigar**: `ssh argus` + `htop`, ou painel "CPU ao longo do tempo" no Grafana

### 🔴 CPU Crítica
- **Dispara**: CPU > **95%** por **10 minutos**
- **Significa**: sistema engasgando — APIs ficam lentas, timeouts
- **Ação**: urgente. Reiniciar o serviço culpado ou subir uma VM mais potente

### ⚠️ RAM Alta
- **Dispara**: RAM usada > **90%** por **5 minutos**
- **Significa**: pouco espaço sobrando. Próximo passo é OOM-killer matar containers
- **Investigar**: `docker stats` pra achar o container que comeu RAM (workers normalmente usam ~1.3GiB cada)

### ⚠️ Disco de Fotos Cheio
- **Dispara**: `/mnt/fotos` > **80%** por **2 minutos**
- **Significa**: volume das fotos enchendo (hoje em ~5%, com folga grande)
- **Ação**: pedir aumento de volume na Oracle Cloud ou rodar limpeza conforme regras LGPD

### 🔴 Disco do Sistema Crítico
- **Dispara**: `/` (raiz) > **90%** por **2 minutos**
- **Significa**: disco onde rodam Docker, SO e logs. Se encher, **TUDO PARA**
- **Ação emergência**: `docker system prune` (limpa imagens antigas), `sudo journalctl --vacuum-size=100M` (corta logs)

---

## 🌐 Grupo 2: Aplicação API (3 alertas)

### 🔴 API Offline
- **Dispara**: endpoint `/metrics` da API não responde por **3 minutos**
- **Significa**: **NINGUÉM consegue usar o app** (mobile nem web)
- **Ação**: `ssh argus` + `docker logs argus-ai-api-1` pra ver porque crashou. Subir: `docker compose -f docker-compose.prod.yml up -d api`

### ⚠️ Alta Taxa de Erros HTTP 5xx
- **Dispara**: mais de **5%** das requisições retornam erro 5xx por **5 minutos**
- **Significa**: API no ar mas falhando muito. Pode ser banco indisponível, exceção não tratada, dependência externa fora (R2, Telegram, MinIO)
- **Investigar**: `docker logs argus-ai-api-1 --tail 100` procurando tracebacks. Painel "Latência por endpoint" mostra qual rota está falhando mais

### ⚠️ Latência Alta na API
- **Dispara**: 95% das requisições demoram mais de **5 segundos** por **5 minutos**
- **Significa**: API responde mas lenta. Causas: query SQL não otimizada, embedding/face recognition demorando, RAM cheia causando swap
- **Investigar**: painel "Latência por endpoint" identifica a rota culpada. `EXPLAIN ANALYZE` na query problemática

---

## 🔌 Grupo 3: Dependências (3 alertas)

### 🔴 PostgreSQL Offline
- **Dispara**: `pg_up == 0` por **2 minutos**
- **Significa**: banco caiu. API funciona mas TODA query falha — usuários veem erro 500 ao salvar abordagens, ocorrências, fotos
- **Ação**: `docker logs argus-ai-db-1` e `docker compose -f docker-compose.prod.yml up -d db`

### 🔴 Redis Offline
- **Dispara**: `redis_up == 0` por **2 minutos**
- **Significa**: worker `arq` não consegue processar fila. Uploads de PDF, embeddings, reconhecimento facial param
- **Ação**: `docker compose -f docker-compose.prod.yml up -d redis`

### ⚠️ Worker arq Parado
- **Dispara**: nenhum comando Redis processado por **10 minutos** com Redis no ar
- **Significa**: containers `argus-ai-worker-*` caíram ou travaram. Tasks em fila não são consumidas
- **Ação**: `docker logs argus-ai-worker-1` + `docker compose -f docker-compose.prod.yml restart worker worker-2`

---

## 💾 Grupo 4: Disco, Storage e Backup (4 alertas)

### ⚠️ Disco de Fotos vai encher em 7 dias
- **Dispara**: projeção linear (últimas 6h) indica disco zerar em menos de 7 dias
- **Significa**: ritmo atual de crescimento é alto. Aviso antecipado pro alerta crítico de 80%
- **Ação**: expandir volume antes que encha

### 🔴 MinIO Offline
- **Dispara**: `probe_success{blackbox-minio} == 0` por **3 minutos**
- **Significa**: storage de fotos/PDFs fora. Upload falha
- **Ação**: `docker logs argus-ai-minio-1` + `docker compose -f docker-compose.prod.yml up -d minio`

### ⚠️ Certificado SSL Expirando
- **Dispara**: cert TLS expira em menos de **15 dias**
- **Significa**: Caddy renova automaticamente — se não renovou, algo travou
- **Ação**: `docker logs argus-ai-caddy-1 | grep -i acme`

### 🔴 Backup do Postgres Atrasado
- **Dispara**: mais de **26h** sem novo dump em `/backups`
- **Significa**: container `db-backup` parou ou `pg_dump` está falhando
- **Ação**: `docker logs argus-ai-db-backup-1` pra ver mensagem de erro

---

## 🩺 Como diagnosticar usando o dashboard

O Telegram é seu **alarme**; o dashboard é seu **raio-X**. Você só abre o dashboard quando recebe alerta ou alguém reclama. Em operação saudável, ~1x por semana pra ver tendências.

### Cenário 1: "tá lento"

1. **Latência por endpoint (p95)** → identifica qual rota está acima de 1s
2. **CPU/RAM ao longo do tempo** → diz se é VM saturada ou query específica
3. **Conexões PostgreSQL** → pool cheio (>70) sugere queries travando

### Cenário 2: "tá dando erro"

1. **Requests por minuto** → linha amarela "Erros 5xx/min" subindo = bug em produção
2. **Latência por endpoint** → cruzar com erros pra identificar rota
3. Gráfico todo zerado por 3min → API caiu, alerta dispara

### Cenário 3: "tá tudo lento e o site engasga"

1. **CPU ao longo do tempo** → 80-100% sustentado = sobrecarga
2. **RAM ao longo do tempo** → linha verde encostando na amarela = sem memória, OOM iminente
3. **Comandos Redis/s** → se zerou, worker `arq` morreu

### Cenário 4: "tá lento mas CPU/RAM tão baixos"

Provavelmente é **query SQL lenta** ou **dependência externa** (R2, Telegram, MinIO). Olhar **Conexões PostgreSQL** — se `active` ou `idle in transaction` subiu sem motivo, tem query travando o pool.

---

## 📈 Glossário dos painéis

### Latência por endpoint (p95)

**O que é p95**: pega 100 requisições, ordena da mais rápida pra mais lenta, mostra o tempo da 95ª. "95% dos usuários esperam até X ms".

| p95 | Avaliação |
|---|---|
| < 200ms | 🟢 Rápido — imperceptível |
| 200ms – 1s | 🟡 OK — perceptível mas tolerável |
| 1s – 5s | 🟠 Lento — usuário irrita |
| > 5s por 5min | 🔴 Alerta dispara |

### Requests por minuto

Duas linhas:
- 🟢 **Total req/min** — todas as requisições
- 🟡 **Erros 5xx/min** — só os erros do servidor

Amarelo zerado = saudável. Amarelo proporcional ≥5% = alerta dispara.

### Conexões PostgreSQL (6 caixinhas)

Cada caixa = **um estado de conexão**, vindo de `pg_stat_activity_count by state`:

| Estado | O que significa |
|---|---|
| `active` | Sessões executando query AGORA |
| `idle` | Conexões no pool, ociosas — **normal** |
| `idle in transaction` | ⚠️ Segurando transação aberta sem fazer nada — **vaza pool** se ficar alto |
| `idle in transaction (aborted)` | ⚠️ Pior: transação deu erro mas não fez ROLLBACK |
| `fastpath function call` | Função interna do PG (debug, raro) |
| `disabled` | Conexão desabilitada (manutenção, raro) |

**Sinais de problema**:
- `active` alto sustentado = muita carga real
- `idle in transaction` > 0 por minutos = **bug** no código (`commit`/`rollback` esquecido)

### Comandos Redis/s

`rate(redis_commands_processed_total[5m])` — quantos comandos Redis por segundo.

Como o Argus **não usa Redis como cache** (só como fila do `arq` worker), esse número reflete atividade do worker.

| Valor | Interpretação |
|---|---|
| 0 sustentado por 10min | 🔴 Worker morreu (alerta dispara) |
| 3-5 ops/s | 🟢 Normal idle — polling da fila vazia |
| 20-100 ops/s | 🟢 Worker processando lote |
| > 1000 ops/s | 🟡 Pico ou bug de loop |

### CPU / RAM ao longo do tempo

Histórico do uso da VM nas últimas 24h (ajustável no canto superior direito). Cruze com horários dos alertas pra ver se algo subiu antes do problema.

### Crescimento do disco de fotos

Verde = espaço usado. Amarelo = capacidade total. Inclinação da linha verde mostra a velocidade de enchimento. Alerta `Disco vai encher em 7d` usa essa tendência.

---

## 🔧 Procedimentos comuns

### Conectar no servidor

```bash
ssh argus
# alias configurado em ~/.ssh/config apontando pra ubuntu@<IP_DA_VM>
```

### Ver logs de um container

```bash
docker logs argus-ai-api-1 --tail 100             # últimas 100 linhas
docker logs argus-ai-api-1 -f                     # follow em tempo real
docker logs argus-ai-api-1 --since 10m            # últimos 10 minutos
```

### Reiniciar um service

```bash
cd ~/argus-ai
docker compose -f docker-compose.prod.yml restart api          # uma só
docker compose -f docker-compose.prod.yml up -d api worker     # subir múltiplos
```

### Subir tudo do zero

```bash
cd ~/argus-ai
docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d
```

### Ver status de tudo

```bash
docker ps --filter "name=argus-" --format "table {{.Names}}\t{{.Status}}"
```

### Ver uso de recursos

```bash
docker stats --no-stream                           # CPU/RAM por container
df -h /mnt/banco /mnt/fotos /                      # uso de disco
free -h                                            # RAM do host
```

---

## 🛑 Silenciar alertas durante manutenção

Antes de fazer manutenção planejada (que vai gerar alertas falsos):

1. Grafana sidebar → 🔔 **Alerting** → **Silences** → **New silence**
2. Filtrar por label (ex.: `severity=critical`) ou alerta específico
3. Definir janela de tempo (ex.: 30 min)
4. Salvar

Os alertas continuam disparando internamente mas não enviam Telegram durante a janela.

---

## 🆘 Onde buscar mais ajuda

- Logs da app: `docker logs argus-ai-api-1`
- Logs do worker: `docker logs argus-ai-worker-1`
- Logs do Postgres: `docker logs argus-ai-db-1`
- Logs do Grafana (se algum alerta sumir): `docker logs argus-grafana`
- Documentação Prometheus PromQL: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Documentação Grafana Alerting: https://grafana.com/docs/grafana/latest/alerting/
