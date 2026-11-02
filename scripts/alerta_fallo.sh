#!/usr/bin/env bash
# Alertas de fallo de los workflows SIN duplicados, usando Issues de GitHub (gratis; GitHub avisa por correo a quien vigila el repositorio).
#   scripts/alerta_fallo.sh abrir  "Titulo" "URL de la ejecucion"   -> abre UN issue; si ya hay uno abierto con ese titulo no crea otro
#   scripts/alerta_fallo.sh cerrar "Titulo" "URL de la ejecucion"   -> si el problema ya se arreglo, lo cierra con un comentario
# No configura ningun correo ni servicio externo. Necesita GH_TOKEN con permiso issues: write (el token del propio workflow).
set -euo pipefail
accion="${1:?accion: abrir|cerrar}"; titulo="${2:?titulo}"; url="${3:-sin enlace}"
abierto=$(gh issue list --state open --limit 100 --json number,title | jq -r --arg t "$titulo" 'map(select(.title==$t))|.[0].number // empty')
case "$accion" in
  abrir)
    if [ -n "$abierto" ]; then
      echo "Ya hay una alerta abierta (#$abierto): no se crea otra."
      exit 0
    fi
    gh issue create --title "$titulo" --body "El workflow ha fallado. Ejecucion: $url

Los datos del repositorio NO se han modificado por este fallo (las escrituras son atomicas y se verifican antes de publicar).
Esta alerta se cierra sola cuando una ejecucion posterior termine bien. No hace falta hacer nada si el fallo fue puntual (p. ej. la API del exchange)." >/dev/null
    echo "Alerta abierta."
    ;;
  cerrar)
    if [ -z "$abierto" ]; then
      echo "No hay alerta abierta."
      exit 0
    fi
    gh issue close "$abierto" --comment "Recuperado: una ejecucion posterior termino bien ($url)." >/dev/null
    echo "Alerta #$abierto cerrada."
    ;;
  *) echo "accion desconocida: $accion" >&2; exit 2 ;;
esac
