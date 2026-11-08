#!/usr/bin/env bash
# Prepara o WSL para o Test Hub. Pode rodar quantas vezes precisar: o que já existe é pulado.
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$raiz"

info() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
falha() { printf '\n\033[1;31mERRO: %s\033[0m\n' "$*" >&2; exit 1; }

grep -qi microsoft /proc/version || falha "Isto aqui é para rodar dentro do WSL."
case "$raiz" in
  /mnt/*) falha "O repo está em $raiz. Mova para o Linux (ex.: ~/test-hub): em /mnt/c o Docker e o git ficam lentos e dá problema de permissão." ;;
esac

info "Pacotes do sistema"
sudo apt-get update -qq
sudo apt-get install -y -qq git curl ca-certificates make unzip

if ! command -v gh >/dev/null; then
  info "GitHub CLI"
  sudo install -d -m 755 /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
  sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq gh
fi

export PATH="$HOME/.local/bin:$PATH"
# shellcheck disable=SC2016
grep -qs '.local/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

if ! command -v uv >/dev/null; then
  info "uv"
  curl -fsSL https://astral.sh/uv/install.sh | sh
fi

if ! command -v claude >/dev/null; then
  info "Claude Code"
  curl -fsSL https://claude.ai/install.sh | bash
fi

if ! docker info >/dev/null 2>&1; then
  if [ -e "/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe" ]; then
    falha "Docker Desktop instalado, mas sem resposta aqui. Abra ele, ative Settings > Resources > WSL Integration para esta distro e rode de novo."
  fi
  if [ "$(ps -p 1 -o comm=)" != "systemd" ]; then
    info "Ativando systemd no WSL"
    printf '[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf >/dev/null
    echo "Agora rode 'wsl --shutdown' no PowerShell, abra o WSL de novo e rode este script outra vez."
    exit 0
  fi
  if ! command -v dockerd >/dev/null; then
    info "Docker Engine"
    curl -fsSL https://get.docker.com | sudo sh
  fi
  sudo systemctl enable --now docker
  if ! id -nG "$USER" | grep -qw docker; then
    sudo usermod -aG docker "$USER"
    echo "Docker instalado. Feche este terminal, abra outro e rode este script de novo (grupo docker)."
    exit 0
  fi
  docker info >/dev/null 2>&1 || falha "Docker instalado, mas não respondeu. Veja: sudo systemctl status docker"
fi

info "Identidade do git"
if [ -z "$(git config --global user.name || true)" ]; then
  read -rp "Nome para os commits: " nome
  git config --global user.name "$nome"
fi
if [ -z "$(git config --global user.email || true)" ]; then
  read -rp "E-mail para os commits (o repo é público): " email
  git config --global user.email "$email"
fi
git config --global init.defaultBranch main
git config --global core.autocrlf input

info "Dependências Python (a partir do uv.lock)"
uv sync --frozen

info "Git e pre-commit"
[ -d .git ] || git init -q -b main
uv run pre-commit install --install-hooks
[ -f .env ] || cp .env.example .env

info "Verificações"
make check

info "Subindo o ambiente completo"
docker compose up -d --build --wait --wait-timeout 180
uv run pytest -m "integration or e2e" -q
docker compose ps
docker compose down

info "Pronto"
cat <<'FIM'
Próximos passos:
  1. gh auth login
  2. claude   (dentro desta pasta)
FIM
