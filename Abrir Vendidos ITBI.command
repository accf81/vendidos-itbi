#!/bin/bash
# Abre o app Vendidos ITBI no navegador
# Duplo clique neste arquivo para iniciar

cd "$(dirname "$0")"

# Verifica se porta 8765 já está em uso
if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1; then
  open http://localhost:8765
  exit 0
fi

# Inicia servidor local em background
python3 -m http.server 8765 &>/dev/null &
SERVER_PID=$!

# Aguarda servidor iniciar
sleep 1

# Abre no navegador padrão
open http://localhost:8765

echo "App rodando em http://localhost:8765"
echo "Feche esta janela para encerrar o servidor."

# Mantém rodando até fechar a janela
wait $SERVER_PID
