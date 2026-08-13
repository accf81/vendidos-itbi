# Vendidos ITBI SP — Índice do Projeto
*Atualizado em 31/05/2026*

---

## 📁 Estrutura de arquivos

```
app/
├── README.md                      ← você está aqui
├── index.html                     ← ferramenta de consulta (PWA)
├── ITBI_SP_residencial.db.gz      ← banco SQLite comprimido (~48MB)
├── manifest.json                  ← config PWA
├── sw.js                          ← service worker
├── Abrir Vendidos ITBI.command    ← abre localmente (servidor Python)
├── deploy_github.command          ← publica no GitHub Pages
└── fix_deploy.command             ← corrigiu problema de deploy anterior
```

---

## 🚀 Como usar

**Localmente:** duplo clique em `Abrir Vendidos ITBI.command`
**Online:** https://accf81.github.io/vendidos-itbi/

---

## 📊 Sobre o banco de dados

Documentação completa em:
`/Users/accf81/Documents/Claude/Projects/ACM/alex-os/_docs/ITBI_DATABASE.md`

Resumo:
- 718.614 registros de transações imobiliárias de SP (2020–2026)
- Fonte: Prefeitura de São Paulo (arquivo CSV mensal)
- Filtrado para imóveis residenciais
- Normalização pendente (logradouros, cartório, números)

---

## 🔗 Projeto relacionado

O banco é usado também no **Alex OS**:
- `https://accf81.github.io/alex-os/`
- `/Users/accf81/Documents/Claude/Projects/ACM/alex-os/`

---

## 🛠️ Trabalho planejado

1. **Normalização do banco** (Opção B) — próxima sessão
   - Expandir abreviações de logradouros
   - Padronizar formato do cartório
   - Remover vagas de garagem e valores inválidos
   - Adicionar campo tipo de imóvel

2. **Pipeline mensal automatizado** (Opção C) — sessão futura
   - Download automático do CSV da Prefeitura
   - Processamento e normalização
   - Publicação automática

---

*Para iniciar sessão de desenvolvimento:*
> *"Conecta /Users/accf81/Documents/Claude/Projects/ACM/app e /Users/accf81/Documents/Claude/Projects/ACM/alex-os. Leia o README.md de cada pasta e o arquivo _docs/ITBI_DATABASE.md."*
