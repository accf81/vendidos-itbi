# Guia do Sistema ITBI

Banco de transações imobiliárias da Prefeitura de São Paulo.
795 mil registros residenciais (2019–2026), atualizado mensalmente.
Reconstruído do zero em 25–26/07/2026 (processo único — ver Dados ITBI/PROCESSO_RECONSTRUCAO.md).
Usado dentro do Alex OS para o ACM (análise comparativa de mercado) e serve a busca
do site público **Pandora Data SP** (antigo "Pandora Vendidos", renomeado 15/07/2026 —
só o nome mudou, o link do site e o repositório continuam os mesmos).

Site público: https://accf81.github.io/vendidos-itbi/
Pasta local: /Users/accf81/Documents/IA/Claude/Projects/Pandora Data SP/
Planilhas originais + backups do banco: /Users/accf81/Documents/IA/Claude/Projects/Dados ITBI/

> **Regras de tratamento e histórico completo dos dados agora ficam em
> `Dados ITBI/ITBI_REGRAS_E_HISTORICO.md`** — ler antes de mexer em qualquer normalização,
> filtro ou no script de atualização mensal. Esse arquivo (`INDICE_ITBI.md`) cobre só a
> arquitetura do site/repositório.
>
> Desde 15/07/2026 existem DOIS bancos com os mesmos dados: o arquivo SQLite local (usado
> pelo Alex OS/ACM) e a tabela `vendas_itbi` no Supabase (usada pela busca do site
> público). A sincronização mensal automática entre os dois já está construída e rodando
> (tarefa agendada dia 10), e desde 26/07/2026 usa a mesma
> deduplicação e as mesmas colunas nos dois (o bug de sincronização foi resolvido junto
> com a reconstrução do banco).

---

## Arquivos principais

| Arquivo | O que é |
|---------|---------|
| `ITBI_SP_residencial.db.gz` | Banco SQLite comprimido (~71MB / 202MB descomprimido) |
| `Atualizar Banco ITBI.command` | Rotina mensal — duplo clique, sem Terminal |
| `atualizar_banco.py` | Script chamado pelo .command acima — não usar diretamente |
| `normalizar_banco.py` | Renormaliza o banco inteiro — usar só se necessário |
| `deploy_github.command` | Publica o banco no GitHub sem atualizar dados |
| `reconstruir_banco.py` | Regera o banco inteiro do zero a partir das planilhas originais |
| `carregar_supabase.py` | Carga/recarga completa da tabela do site no Supabase (usado na reversão) |

---

## Rotina mensal de atualização

Duplo clique em `Atualizar Banco ITBI.command` → aguardar conclusão → pronto.

O script baixa o XLSX da Prefeitura, filtra residenciais, insere registros novos e publica no GitHub automaticamente.

---

## Estrutura do banco

Tabela única: `vendas`

Colunas principais:
- `logradouro_norm` — nome normalizado (usar para buscas, não `logradouro`)
- `referencia` — nome do edifício/condomínio
- `bairro`, `numero`, `complemento`
- `area_construida_m2`, `valor_transacao`, `valor_m2`
- `data_transacao`, `ano`
- `sql` — código da Prefeitura (parte da chave de deduplicação: sql+numero+complemento+data+valor)
- `logradouro_fmt` — nome da rua pra exibição ("Rua Padre João Manuel")
- `proporcao_transmitida` — % do imóvel transmitida na venda (100 = imóvel inteiro; <100 = fração)

---

## Como o banco é usado no Alex OS

Carregado via SQL.js no navegador (lazy — só na primeira abertura do ACM ou ficha de condomínio). Baixa o arquivo `.db.gz` inteiro pro navegador — mesmo problema de performance que o site público tinha antes da migração pro Supabase (ver abaixo). Ainda não migrado (backlog 15.7) — ninguém reclamou porque no ACM já se espera um carregamento.

Buscas em `imoveis.html`:
- Ficha de condomínio: por `logradouro_norm` + `numero`
- ACM manual: por `logradouro_norm`, `referencia`, `bairro`
- ACM por faixas e concorrentes: mesma lógica, com filtros de área e período

---

## Como o banco é usado no Pandora Data SP (site público) — desde 15/07/2026

Não baixa mais arquivo nenhum. Busca consulta direto a tabela `vendas_itbi` no Supabase
(mesmo projeto do Alex OS), com leitura pública liberada via RLS e escrita bloqueada
(dado já é público, vem da Prefeitura — só a rotina de atualização mensal, quando for
automatizada, deve poder escrever).

- Tabela: `vendas_itbi` (mesmas colunas do SQLite + `id` bigserial como chave primária —
  `sql` não é único na origem, um mesmo código de transação pode cobrir várias unidades)
- Índices: `logradouro_norm`, `(logradouro_norm, numero)`, e um índice **trigram**
  (`pg_trgm` + GIN em `logradouro_norm`) — necessário pra busca por "contém" (`ILIKE
  '%termo%'`) não estourar o tempo limite do banco varrendo as 795 mil linhas sem atalho
- Funções de autopreenchimento: `buscar_ruas_itbi(termo)` e `buscar_numeros_itbi(rua, termo)`.
  Desde 26/07/2026 a de ruas lê a view materializada `ruas_itbi` (lista de ruas distintas,
  sem acesso direto pela API) — na tabela inteira o banco parou de usar o índice trigram e
  estourava o timeout; a rotina mensal chama `atualizar_ruas_itbi()` pra manter a lista em dia
- Busca principal: `index.html` monta um filtro `or=(and(logradouro_norm.ilike.*X*,numero.eq.Y),...)`
  via REST do Supabase (PostgREST), suporta múltiplos endereços comparados de uma vez

**Se for mexer na estrutura da tabela `vendas` do SQLite** (adicionar/renomear coluna),
lembrar que `vendas_itbi` no Supabase precisa da mesma mudança manualmente até a
sincronização ser automatizada (backlog 15.1).

---

## Regra crítica — filtro de vagas

**Sempre usar `startsWith`, nunca `includes`, ao filtrar complementos:**

```javascript
// ✅ CORRETO
if (comp.startsWith('VAGA') || comp.startsWith('VG') || comp.startsWith('GARAGEM') || comp.startsWith('BOX')) continue;

// ❌ ERRADO — esconde apartamentos com vaga (ex: "AP 22 E VG")
if (comp.includes('VAGA') || comp.includes('VG')) continue;
```

O padrão `includes('VG')` escondia 119.695 registros. Corrigido em 03/06/2026.

Funções afetadas em `imoveis.html` (verificar todas ao editar):
1. `buscarITBICond` — ficha de condomínio (~linha 1660)
2. Busca manual ACM (~linha 3351)
3. Busca por faixas ACM (~linha 3403)
4. Busca automática concorrentes (~linha 3452)

---

## Documentação detalhada

Para regras de tratamento, estrutura de colunas e histórico completo de decisões/problemas:
`/Users/accf81/Documents/IA/Claude/Projects/Dados ITBI/ITBI_REGRAS_E_HISTORICO.md`

Para o processo de desenvolvimento (time de agentes, esteira, trilho rápido × completo — global, todos os projetos):
`/Users/accf81/Documents/IA/Claude/Projects/Equipe de Agentes/PROCESSO.md`

---

## Como iniciar uma sessão sobre o ITBI

```
Conecta /Users/accf81/Documents/IA/Claude/Projects/Alex OS/v2
e /Users/accf81/Documents/IA/Claude/Projects/Pandora Data SP.
Leia INDICE.md (na raiz de Projects) e siga as instruções.
Sessão ITBI — [descrever o que precisa]
```
