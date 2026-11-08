#!/usr/bin/env bash
# Cria o repositório PÚBLICO no GitHub (ADR-004), envia a main e liga a branch protection.
# Uso: scripts/publicar-github.sh [nome-do-repo]
set -euo pipefail

nome="${1:-test-hub}"
cd "$(dirname "${BASH_SOURCE[0]}")/.."

gh auth status >/dev/null || { echo "Rode 'gh auth login' antes."; exit 1; }
git rev-parse HEAD >/dev/null 2>&1 || { echo "Faça o primeiro commit antes."; exit 1; }

dono="$(gh api user --jq .login)"
if ! git remote get-url origin >/dev/null 2>&1; then
  gh repo create "$nome" --public --source . --remote origin --push
else
  git push -u origin main
fi

gh api -X PUT "repos/$dono/$nome/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["quality", "test", "build", "e2e"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON

echo "Branch protection ligada em $dono/$nome. A partir de agora, tudo entra por PR."
