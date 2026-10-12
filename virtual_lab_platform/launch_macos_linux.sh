#!/bin/sh
set -eu
cd "$(dirname "$0")"

PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo "Python 3 est introuvable."
  echo "Installe Python 3 depuis https://www.python.org/downloads/macos/ puis relance ce script."
  exit 1
fi

VERSION=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "Python détecté : $VERSION"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || {
  echo "Virtual Lab nécessite Python 3.10 ou supérieur."
  echo "Installe une version récente depuis https://www.python.org/downloads/macos/."
  exit 1
}

echo "Démarrage de Virtual Lab sur http://127.0.0.1:${VIRTUAL_LAB_PORT:-8765}"
exec "$PYTHON" app.py
