# Argus AI — Plano de Recuperação de Desastre

> Última revisão: 2026-05-27
> Responsável: Alex Abud

Este documento descreve como recuperar o Argus AI em diferentes cenários
de falha. Mantenha-o **impresso ou salvo offline** — em uma emergência,
pode ser que você não tenha acesso à VM nem ao cofre de senhas.

---

## 1. Mapa de Backup

### O que está sendo salvo, onde e com que frequência

| Item | Frequência | Oracle Object Storage | Google Drive | Retenção |
|---|---|:---:|:---:|---|
| Dump do banco (`argus_*.dump`) | Diário (07h BRT pelo `db-backup`, replicado às 03h pelas nuvens) | ✅ | ✅ | 7 dias |
| `.env` criptografado (GPG AES256) | Diário | ✅ | ✅ | 7 dias |
| Grafana (`/mnt/banco/grafana` em tar.gz) | Diário | ✅ | ✅ | 7 dias |
| Fotos/uploads (`/mnt/fotos`) | Diário (espelho via `rclone sync`) | ❌ | ✅ | espelhado |
| Backup local na VM (`/mnt/banco/backups`) | Diário (container `db-backup`) | — | — | 7 dias |

### Localizações físicas

- **Oracle Object Storage**
  - Bucket: `argus-backups`
  - Region: `sa-saopaulo-1`
  - Endpoint S3: `https://grjzkxyb1rpa.compat.objectstorage.sa-saopaulo-1.oraclecloud.com`
  - Acesso via console: `cloud.oracle.com` → Storage → Object Storage → Buckets → argus-backups

- **Google Drive pessoal** (`alexmabud@gmail.com`)
  - Pasta raiz: `/Argus_Backups/`
  - Subpastas: `banco/`, `env/`, `grafana/`, `fotos/`

- **Credenciais e senhas** (armazenadas no cofre de senhas offline do operador)
  - Access Key + Secret Key do Oracle Object Storage
  - Senha de descriptografia do `.env` (GPG simétrico)

---

## 2. Cenários de Recuperação

### Cenário A — Dado específico foi perdido/corrompido (ex: tabela deletada)

**Impacto**: parcial. Tudo o que aconteceu entre o último backup (~03h)
e o problema é perdido.

**Como recuperar**:

1. Identifica a data do último backup íntegro.
2. SSH na VM e roda:
   ```bash
   sudo /home/ubuntu/argus-ai/scripts/restore_from_backup.sh
   ```
3. Escolhe `Oracle` ou `Google Drive` como origem.
4. Escolhe a data (formato `YYYYMMDD`).
5. Escolhe item `1` (apenas banco).
6. Confirma quando pedir.

**Tempo estimado**: ~5 minutos.

---

### Cenário B — VM Oracle Cloud foi terminada (ou está inacessível)

**Impacto**: total. VM, fotos locais e dumps locais perdidos. **Mas** os
backups estão em Oracle Object Storage e Google Drive, independentes da VM.

**Como recuperar**:

#### B.1 — Criar nova VM
1. Console Oracle Cloud → Compute → Instances → Create Instance
2. Imagem: Ubuntu 22.04 LTS ARM (Always Free)
3. Shape: VM.Standard.A1.Flex (4 OCPU, 24GB RAM)
4. Storage: 200GB boot + 100GB block volume montado em `/mnt/fotos`
5. Habilita SSH com sua chave pública

#### B.2 — Setup base na nova VM
```bash
# 1. Instalar dependências
sudo apt update && sudo apt install -y docker.io docker-compose-plugin rclone gnupg git

# 2. Clonar o projeto
cd ~
git clone https://github.com/alexmabud/argus-ai.git
cd argus-ai

# 3. Criar diretórios de dados
sudo mkdir -p /mnt/banco/{pgdata,redis,backups,grafana,prometheus,textfile}
sudo mkdir -p /mnt/fotos
```

#### B.3 — Restaurar `.env`
```bash
# Configura rclone seguindo scripts/setup_rclone.sh (passos 2 e 3)
# (precisa das credenciais guardadas no cofre de senhas: chaves Oracle + senha GPG)

# Baixa o .env cifrado mais recente
rclone copy gdrive:Argus_Backups/env/ /tmp/

# Descobre o mais recente e decifra
LATEST=$(ls -t /tmp/env_*.gpg | head -1)
gpg --output ~/argus-ai/.env --decrypt "$LATEST"
# Senha: a do cofre de senhas (entrada do GPG do Argus)
chmod 600 ~/argus-ai/.env
```

#### B.4 — Subir a stack
```bash
cd ~/argus-ai
docker compose -f docker-compose.prod.yml up -d db redis  # primeiro DB e Redis
sleep 30
```

#### B.5 — Restaurar banco
```bash
sudo ./scripts/restore_from_backup.sh
# Escolhe Google Drive, data mais recente, item 1 (banco)
```

#### B.6 — Restaurar Grafana
```bash
sudo ./scripts/restore_from_backup.sh
# Escolhe Google Drive, mesma data, item 3 (Grafana)
```

#### B.7 — Restaurar fotos
```bash
sudo ./scripts/restore_from_backup.sh
# Escolhe Google Drive, item 4 (fotos)
# Aviso: pode levar tempo conforme volume
```

#### B.8 — Subir resto da stack
```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.monitoring.yml up -d
```

#### B.9 — Validações
- API respondendo: `curl http://localhost/health`
- Login funcionando (CPF descriptografando = `ENCRYPTION_KEY` correta)
- Fotos visíveis na PWA
- Grafana acessível com dashboards intactos

**Tempo estimado**: ~1-2 horas.

---

### Cenário C — Perdi acesso à conta Oracle Cloud

**Impacto**: parcial. Backups Oracle ficam inacessíveis, **mas Google Drive permanece**.

**Como recuperar**:
1. Use `Cenário B` com `gdrive:` como única origem.
2. As fotos só estão no Google Drive mesmo, então não muda nada nesse aspecto.

---

### Cenário D — Perdi acesso à conta Google

**Impacto**: parcial. Sem fotos do Google Drive, **mas banco e Grafana ainda no Oracle**.

**Como recuperar**:
1. Use `Cenário B` com `oracle:` como única origem.
2. Fotos ficam perdidas (a menos que ainda exista a VM original com `/mnt/fotos`).

---

### Cenário E — Perdi a senha do GPG

**Impacto**: catastrófico se também perdeu acesso à VM original.

- Sem a senha, **não é possível descifrar o `.env`**.
- Sem o `.env`, **não é possível ler os CPFs criptografados no banco**
  (`ENCRYPTION_KEY` está dentro do `.env`).
- A aplicação até sobe, mas os dados pessoais ficam ilegíveis.

**Mitigação preventiva**:
- Manter o cofre de senhas em mais de um lugar (sync na nuvem **e** cópia local offline)
- Backup adicional da senha do GPG em outro local seguro (ex: cofre físico)

**Se já aconteceu**:
- Se ainda tem acesso à VM antiga, copie o `.env` em texto puro de lá
- Caso contrário, dados criptografados são perdidos. **Sem solução técnica**

---

### Cenário F — Deploy falhou por disco cheio na VM

**Impacto**: produção fora do ar. O workflow de deploy (`.github/workflows/deploy.yml`)
faz `docker compose down` **antes** de buildar — se o build falhar (ex.: disco
cheio), os containers ficam parados até alguém corrigir manualmente. Não é
troca atômica de versão.

**Como identificar**: no log do Actions (aba Deploy da run), erro do tipo
`failed to extract layer ...: no space left on device` durante o passo
`exporting to image`.

**Como recuperar** (via `ssh argus`, dentro de `~/argus-ai`):

```bash
# 1. Confirmar o disco cheio e liberar espaço (não afeta volumes/dados)
df -h /
docker system prune -af
docker builder prune -af
df -h /   # deve sobrar vários GB

# 2. A última imagem boa geralmente continua taggeada (prune sem -a durante
#    o deploy não a remove). Confirme e reaproveite sem rebuildar:
docker images | grep argus-ai
docker tag argus-ai-api:latest argus-ai-app:latest   # nome esperado pelo compose

# 3. Sobe SEM --build (usa a imagem existente; evita rebuildar e estourar de novo)
docker compose -f docker-compose.prod.yml up -d
sleep 5
docker compose -f docker-compose.prod.yml exec -T api python -m alembic upgrade head

# 4. Confirmar
docker compose -f docker-compose.prod.yml ps
curl -sf http://localhost:80/health && echo "  OK"
```

Isso sobe só o `docker-compose.prod.yml` (sem o `docker-compose.monitoring.yml`)
porque `GF_ADMIN_PASSWORD`/tokens do Telegram só existem como GitHub Secrets,
injetados pelo workflow de deploy — não ficam salvos na VM. Depois de resolver
a causa raiz (ver `docs/DEPLOY.md`, seção "Imagem única") e mergear a correção,
deixe o próximo deploy automático religar o monitoring normalmente.

**Causas já corrigidas** (não deveriam voltar a acontecer, mas documentado
caso regrida):
- `api`/`worker`/`worker-2` buildavam 3 imagens idênticas em paralelo →
  agora compartilham uma `image:` só (`docker-compose.prod.yml`).
- A imagem carregava ~5 GB de libs CUDA/NVIDIA (`nvidia-*`, `triton`) que uma
  VM sem GPU nunca usa → removidas do venv em `Dockerfile.prod`.

---

## 3. Checklist Mensal de Validação

Faça essas verificações **uma vez por mês** para garantir que o backup
realmente funciona (backup não testado = teoria):

- [ ] Confirma que o backup das nuvens rodou nos últimos 7 dias:
  ```bash
  ssh argus 'tail -5 /var/log/argus_backup.log'
  ```
- [ ] Listagem dos backups no Oracle:
  ```bash
  rclone ls oracle:argus-backups/banco/
  ```
- [ ] Listagem dos backups no Google Drive:
  ```bash
  rclone ls gdrive:Argus_Backups/banco/
  ```
- [ ] Tamanho da pasta de fotos no Google Drive condiz com `/mnt/fotos`:
  ```bash
  rclone size gdrive:Argus_Backups/fotos/
  ssh argus 'du -sh /mnt/fotos'
  ```
- [ ] Testa decifragem do `.env` (NÃO sobrescreve o original):
  ```bash
  rclone copy gdrive:Argus_Backups/env/ /tmp/test_decrypt/
  gpg --output /tmp/test_decrypt/.env.decrypted --decrypt /tmp/test_decrypt/env_*.gpg
  head -3 /tmp/test_decrypt/.env.decrypted   # deve ver linhas de config
  rm -rf /tmp/test_decrypt
  ```
- [ ] Métrica Prometheus de "último backup nas nuvens" é recente:
  ```bash
  ssh argus 'cat /mnt/banco/textfile/backup_clouds.prom'
  # timestamp deve ser de ontem ou hoje
  ```

---

## 4. Alertas Automáticos

Há um alerta Grafana (`alert-backup-falhou`) que dispara se o backup
local (`argus_backup_last_success_timestamp_seconds`) ficar mais de 26h
sem atualizar.

**TODO**: adicionar alerta análogo para
`argus_backup_clouds_last_success_timestamp_seconds`. (Issue futura.)

---

## 5. Contatos de Emergência

- **Conta Oracle Cloud**: `alexmabud@gmail.com` (recuperação via email/2FA)
- **Conta Google Drive**: `alexmabud@gmail.com` (recuperação via email/2FA)
- **Repo GitHub**: `github.com/alexmabud/argus-ai`

---

## 6. Histórico de Restores Realizados

Anote aqui sempre que executar um restore (mesmo de teste):

| Data | Cenário | Origem | Item | Tempo | Resultado |
|---|---|---|---|---|---|
| (aguardando primeiro registro) | | | | | |
