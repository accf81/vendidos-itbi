#!/bin/bash
# Atualizar Banco ITBI — Pipeline mensal
# Baixa dados novos da Prefeitura SP, atualiza o banco e publica no GitHub.
# Uso: duplo clique neste arquivo.

cd "$(dirname "$0")"

echo ""
echo "======================================"
echo "  ATUALIZAR BANCO ITBI SP"
echo "======================================"
echo ""

# Verificar Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 não encontrado."
    echo "   Instale em: https://www.python.org/downloads/"
    read -p "Pressione Enter para fechar..."
    exit 1
fi

# Instalar dependências se necessário
python3 -c "import requests, openpyxl" 2>/dev/null || {
    echo "Instalando dependências..."
    pip3 install requests openpyxl -q
}

# Rodar atualização
python3 atualizar_banco.py
STATUS=$?

if [ $STATUS -ne 0 ]; then
    echo ""
    echo "❌ Atualização falhou. Banco não foi alterado."
    read -p "Pressione Enter para fechar..."
    exit 1
fi

# Publicar no GitHub
echo ""
echo "======================================"
echo "  PUBLICANDO NO GITHUB..."
echo "======================================"
echo ""

REPO_DIR="$(pwd)"
# Token lido de ~/.alex-os-secrets — nunca gravado no script nem na config (regra 12.5)
SECRETS_FILE="$HOME/.alex-os-secrets"
[ -f "$SECRETS_FILE" ] && source "$SECRETS_FILE"
TOKEN="$ALEX_OS_GH_TOKEN"
if [ -z "$TOKEN" ]; then echo "❌ Token não configurado em ~/.alex-os-secrets"; read -p "Pressione Enter para fechar..."; exit 1; fi

git remote set-url origin "https://github.com/accf81/vendidos-itbi.git" 2>/dev/null || git remote add origin "https://github.com/accf81/vendidos-itbi.git"
git add ITBI_SP_residencial.db.gz atualizar_banco.py "Atualizar Banco ITBI.command"
git commit -m "Atualização banco ITBI $(date '+%d/%m/%Y')" || echo "Nada novo para publicar."
git -c credential.helper='!f() { echo "username=accf81"; echo "password='"$TOKEN"'"; }; f' push origin main

echo ""
echo "======================================"
echo "✅ BANCO ATUALIZADO E PUBLICADO!"
echo "======================================"
echo ""
read -p "Pressione Enter para fechar..."
