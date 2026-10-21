#!/usr/bin/env bash
# Ejecuta un comando hasta 3 veces (para fallos de red pasajeros). Es seguro repetir: la escritura es atomica y no duplica operaciones.
# Uso: scripts/reintentar.sh comando [argumentos...]
for intento in 1 2 3; do
  if "$@"; then
    exit 0
  fi
  echo "Intento $intento fallido."
  [ "$intento" -lt 3 ] && sleep $((intento * 20))
done
echo "::error::El comando fallo 3 veces: $*"
exit 1
