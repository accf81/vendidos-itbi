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
TOKEN=$(grep 'TOKEN\|ghp_' deploy_github.command 2>/dev/null | grep -o 'ghp_[A-Za-z0-9]*' | head -1)

git add ITBI_SP_residencial.db.gz atualizar_banco.py "Atualizar Banco ITBI.command"
git commit -m "Atualização banco ITBI $(date '+%d/%m/%Y')" || echo "Nada novo para publicar."
git push

echo ""
echo "======================================"
echo "✅ BANCO ATUALIZADO E PUBLICADO!"
echo "======================================"
echo ""
read -p "Pressione Enter para fechar..."
