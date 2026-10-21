#!/bin/bash
# Empacota o jogo com a biblioteca Python do Mage Core e instala no console.
#
#   ./instalar.sh [host-ssh] [pasta-do-sdk]
#   padrão: r36s e ../r36s-a11y-sdk (clone de github.com/gogabs/r36s-a11y-sdk)
#
# Não reinicia nada: o Luma percebe o jogo novo sozinho. Com o jogo aberto,
# não instala, porque ele carrega os sons sob demanda da pasta instalada.
# O jogo se chamava Canoa: o instalador apaga a pasta antiga e leva o recorde.
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
# O Rio Abaixo precisa do som por ouvido (ears.py); um clone antigo do Mage Core não tem.
if [ ! -f "$SDK_PY/ears.py" ] && [ -f "$HERE/r36s_a11y/ears.py" ]; then
  echo "O Mage Core em $SDK_PY ainda não tem o som por ouvido; usando a cópia do jogo."
  SDK_PY="$HERE/r36s_a11y"
fi
[ -d "$SDK_PY" ] || { echo "Mage Core não encontrado."; exit 1; }
echo "Mage Core selecionado: $SDK_PY"

if ssh "$HOST" 'for p in /proc/[0-9]*; do readlink "$p/cwd"; done 2>/dev/null | grep -Eq "^/(roms|opt)/a11y/games/(rio-abaixo|canoa)(/|$)"'; then
  echo "O Rio Abaixo está aberto no console. Feche o jogo e rode de novo."
  exit 1
fi

PKG=$(mktemp -d)
trap 'rm -rf "$PKG"' EXIT
mkdir -p "$PKG/rio-abaixo"
cp -r "$HERE/game.json" "$HERE/main.py" "$HERE/rio_abaixo" "$HERE/sounds" "$SDK_PY" "$PKG/rio-abaixo/"
find "$PKG" -name __pycache__ -prune -exec rm -rf {} +

tar -C "$PKG" -czf - rio-abaixo | ssh "$HOST" '
  set -e; mkdir -p /roms/a11y/games; cd /roms/a11y/games
  rm -rf .rio-abaixo.novo && mkdir .rio-abaixo.novo
  tar -xzmf - -C .rio-abaixo.novo
  rm -rf rio-abaixo && mv .rio-abaixo.novo/rio-abaixo . && rmdir .rio-abaixo.novo
  rm -rf canoa /opt/a11y/games/canoa /opt/a11y/games/rio-abaixo
  saves=$HOME/.local/share/r36s-a11y
  if [ -d "$saves/canoa" ] && [ ! -e "$saves/rio-abaixo" ]; then mv "$saves/canoa" "$saves/rio-abaixo"; fi
  echo "instalado: $(ls rio-abaixo/sounds | wc -l) sons"; df -h /roms | tail -1'
