#!/bin/bash
# setup_oracle.sh — Setup inicial da VM Oracle Cloud (ARM A1 / Ubuntu 22.04)
# Uso: bash setup_oracle.sh
# Executa como root ou com sudo

set -euo pipefail

echo "==> [1/7] Atualizando sistema..."
apt-get update -y && apt-get upgrade -y

echo "==> [2/7] Instalando dependências base..."
apt-get install -y \
  curl git make unzip \
  ca-certificates gnupg lsb-release \
  rclone

echo "==> [3/7] Instalando Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker ubuntu || true

echo "==> [4/7] Criando estrutura de diretórios no block storage..."
# Certifique-se que o block storage está montado em /data antes de rodar este script
# Para montar: sudo mount /dev/sdb /data (ajuste o device conforme Oracle)
mkdir -p /data/fotos
mkdir -p /data/postgres
mkdir -p /data/backups
chmod 755 /data/fotos /data/postgres /data/backups

echo "==> [5/7] Criando entrada no fstab para mount automático..."
# Adicione manualmente a linha do seu device em /etc/fstab se ainda não fez
# Exemplo: /dev/sdb /data ext4 defaults,nofail 0 2
echo "ATENÇÃO: verifique /etc/fstab para garantir mount automático do block storage"

echo "==> [6/7] Configurando firewall (ufw)..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
# MinIO console — opcional, remova se não quiser exposto
# ufw allow 9001/tcp
ufw --force enable

echo "==> [7/7] Clonando repositório Argus AI..."
read -rp "Cole a URL do repositório git: " REPO_URL
git clone "$REPO_URL" /opt/argus_ai
chown -R ubuntu:ubuntu /opt/argus_ai

echo ""
echo "✓ Setup concluído!"
echo ""
echo "Próximos passos:"
echo "  1. cd /opt/argus_ai"
echo "  2. cp .env.production.example .env"
echo "  3. Edite o .env com suas credenciais reais"
echo "  4. docker compose -f docker-compose.prod.yml up -d"
echo "  5. docker compose -f docker-compose.prod.yml exec api python -m scripts.seed"
echo "  6. Configure rclone: rclone config  (veja scripts/backup_rclone.sh)"
