#!/usr/bin/env bash
# Publica en el repositorio los archivos indicados. Reintenta si otro proceso se adelanta; NUNCA usa --force.
# Uso: scripts/guardar_datos.sh "Mensaje del commit" ruta1 [ruta2 ...]
set -euo pipefail
mensaje="$1"; shift
rama="${GITHUB_REF_NAME:-main}"
git config user.name "agentes-bot"
git config user.email "agentes-bot@users.noreply.github.com"
git add -- "$@"
if git diff --staged --quiet; then
  echo "Sin cambios que guardar."
  exit 0
fi
git commit -m "$mensaje"
for intento in 1 2 3 4 5; do
  if git pull --rebase origin "$rama"; then
    if git push origin "HEAD:$rama"; then
      echo "Guardado en el intento $intento."
      exit 0
    fi
  else
    echo "Conflicto al integrar cambios remotos; se cancela el rebase y se reintenta."
    git rebase --abort || true
  fi
  sleep $((intento * 5))
done
echo "::error::No se pudo publicar tras 5 intentos (sin forzar nada). Los datos de esta ejecucion no se han guardado."
exit 1
