#!/bin/bash
# Empacota o jogo com a biblioteca Python do Mage Core e instala no console.
#
#   ./instalar.sh [host-ssh] [pasta-do-sdk]
#   padrão: r36s e ../r36s-a11y-sdk (clone de github.com/gogabs/r36s-a11y-sdk)
#
# Não reinicia nada: o Luma percebe o jogo novo sozinho. Com o jogo aberto,
# não instala, porque ele carrega os sons sob demanda da pasta instalada.
set -euo pipefail
HOST=${1:-r36s}
HERE=$(cd "$(dirname "$0")" && pwd)
SDK=${2:-$HERE/../r36s-a11y-sdk}
SDK_PY="$SDK/python/r36s_a11y"
if [ ! -d "$SDK_PY" ]; then
  if [ "$#" -ge 2 ]; then
    echo "Mage Core não encontrado no caminho solicitado: $SDK"; exit 1
  fi
  SDK_PY="$HERE/r36s_a11y"
fi
# A Canoa precisa do som por ouvido (ears.py); um clone antigo do Mage Core não tem.
if [ ! -f "$SDK_PY/ears.py" ] && [ -f "$HERE/r36s_a11y/ears.py" ]; then
  echo "O Mage Core em $SDK_PY ainda não tem o som por ouvido; usando a cópia do jogo."
  SDK_PY="$HERE/r36s_a11y"
fi
[ -d "$SDK_PY" ] || { echo "Mage Core não encontrado."; exit 1; }
echo "Mage Core selecionado: $SDK_PY"

if ssh "$HOST" 'for p in /proc/[0-9]*; do readlink "$p/cwd"; done 2>/dev/null | grep -Eq "^/(roms|opt)/a11y/games/canoa(/|$)"'; then
  echo "O Canoa está aberto no console. Feche o jogo e rode de novo."
  exit 1
fi

PKG=$(mktemp -d)
trap 'rm -rf "$PKG"' EXIT
mkdir -p "$PKG/canoa"
cp -r "$HERE/game.json" "$HERE/main.py" "$HERE/canoa" "$HERE/sounds" "$SDK_PY" "$PKG/canoa/"
find "$PKG" -name __pycache__ -prune -exec rm -rf {} +

tar -C "$PKG" -czf - canoa | ssh "$HOST" '
  set -e; mkdir -p /roms/a11y/games; cd /roms/a11y/games
  rm -rf .canoa.novo && mkdir .canoa.novo
  tar -xzmf - -C .canoa.novo
  rm -rf canoa && mv .canoa.novo/canoa . && rmdir .canoa.novo
  rm -rf /opt/a11y/games/canoa
  echo "instalado: $(ls canoa/sounds | wc -l) sons"; df -h /roms | tail -1'
