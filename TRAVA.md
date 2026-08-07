# Aqui se publica pela porta

Este repositório publica por **um comando só**: `publicar.command`, na raiz.
Clique duas vezes nele (ou rode-o pelo terminal). Ele confere e, se estiver
tudo certo, guarda e envia.

## O que ele confere antes de deixar sair

1. **R-1** — não sobrou arquivo mexido fora do pacote.
2. **R-2** — só vão os arquivos da própria etapa.
3. **R-3** — a escrita dos arquivos é válida, com o comando certo para cada tipo.
4. **Segredo** — nenhuma chave ficou escrita dentro de arquivo que ia ser publicado.

Se qualquer uma reprovar, **não sai** — e a mensagem diz o que faltou, em qual
arquivo, e qual é o próximo passo.

## O que você precisa preencher antes

O arquivo `.trava/etapa.json` (fica nesta pasta, e **nunca é publicado**):
quais arquivos são desta etapa, e o que na pasta **não é** desta etapa, com o
motivo. Há um exemplo pronto na pasta do motor.

## Onde a trava mora

Fora deste repositório, na pasta `_trava/` de `Projects/` — um motor só,
compartilhado pelos três repositórios (Alex OS, Pandora Data SP e Pandora OS),
para que um conserto valha para os três.

**Consequência que precisa estar escrita:** quem clonar este repositório em
outra máquina **não leva a trava junto**. Hoje só existe uma máquina; se um dia
existir outra, a trava precisa ser instalada lá também.

## E se eu publicar por fora?

Dá. O gancho do git (`pre-push`) recusa, mas existe jeito de pulá-lo. O que
não dá é publicar por fora **em silêncio**: toda publicação pela porta deixa um
recibo, e o que sai sem recibo aparece.

_Ramo de publicação: `main` · Endereço: https://accf81.github.io/vendidos-itbi/_
