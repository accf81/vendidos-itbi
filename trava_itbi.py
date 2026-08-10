#!/usr/bin/env python3
"""
trava_itbi.py — a rede de segurança das cargas do ITBI (R-11 da trava).
=======================================================================

De que erro isto nasceu (lição L-21, 05/08/2026)
------------------------------------------------
Duas abas da planilha da Prefeitura de 2024 (janeiro e outubro) vieram SEM
LINHA DE TÍTULO. Os scripts procuram as colunas pelo nome, não acham, e pulavam
a aba inteira sem erro, sem aviso e sem registro. Resultado: 19.785 vendas
residenciais de 2024 nunca entraram no banco, e o ACM do Alex trabalhou mais de
um ano com 2024 incompleto. Não havia como perceber: o sistema não mentia, só
omitia. A frase da lição é o item inteiro: SILÊNCIO NÃO É SINAL DE SUCESSO.

O que já existia antes desta peça (e continua)
----------------------------------------------
O leitor já conta por aba quantas linhas leu e quantas entendeu, já separa aba
vazia (mês sem venda — não é falha) de aba com linhas e nada aproveitado (é
falha, e a rodada PARA), e já grava o boletim em arquivo e no caderno de bordo.

O que esta peça acrescenta (Etapa 3 da trava)
---------------------------------------------
  1. COMPARAÇÃO COM A RODADA ANTERIOR. O caderno de bordo (`importacoes` e
     `importacoes_partes`) já guarda os totais de cada rodada. Faltava ler a
     última e gritar na variação: parte já fechada que caia mais de 5%, ou que
     passe a ter zero, PARA A RODADA em vez de aceitar o número novo.
  2. A LISTA DE "IGNORADO DE PROPÓSITO" SAI DE DENTRO DO CÓDIGO. Ela vira o
     arquivo `ignorados_de_proposito.json`, lido antes da carga e repetido no
     boletim. Assim a aba de instruções continua passando, e a lista fica
     visível em vez de embutida.
  3. O GRITO SAI DO TERMINAL. A rotina mensal roda sozinha e ninguém está
     olhando o terminal às 6h da manhã: o veto passa a virar cartão no quadro
     da área IA.

Uma tradução que precisa estar escrita: o plano fala em "anos fechados". A
rotina mensal lê UM ano por vez, e dentro dele as abas são os MESES. Então
"ano fechado" aqui é "mês que já existia na rodada anterior" — inclusive o mês
corrente, porque mês nenhum pode ENCOLHER de uma rodada para a outra. É a
leitura mais apertada das duas, e é de propósito.

ATENÇÃO À CHAVE (e já houve tropeço nisto): cada projeto do Supabase tem a SUA
chave de escrita. O caderno de bordo do ITBI vive no projeto do Pandora OS; o
quadro da área IA vive no projeto do Alex OS. A chave de um não funciona no
outro.

Autor: Claude Code (Opus 5) · 08/08/2026
"""
import json
import os
import time

import requests

AQUI = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DOS_IGNORADOS = os.path.join(AQUI, 'ignorados_de_proposito.json')

# A queda máxima aceita numa parte já conhecida, antes de a rodada parar.
# 5% foi a decisão do Orquestrador em 07/08 (§8 da arquitetura).
QUEDA_MAXIMA = 0.05

# O quadro da área IA — projeto do ALEX OS, não o do Pandora OS.
PROJETO_DO_QUADRO = 'sobmjqounukzbplrmhkr'
QUADRO = f'https://{PROJETO_DO_QUADRO}.supabase.co/rest/v1/backlog_itens'


# ─── 1. A lista de "ignorado de propósito" ──────────────────────────────────

def ler_ignorados():
    """Lê a lista declarada. Arquivo ausente PARA a carga, de propósito.

    Poderia haver uma lista de reserva dentro do código, e é justamente isso que
    não pode existir: a lista escondida dentro do código foi o que permitiu que
    ninguém soubesse o que estava sendo pulado. Sem o arquivo, a carga não roda.
    """
    if not os.path.exists(ARQUIVO_DOS_IGNORADOS):
        raise RuntimeError(
            f'não achei {ARQUIVO_DOS_IGNORADOS}.\n'
            '  Esta lista diz quais abas a carga ignora DE PROPÓSITO, e ela precisa existir\n'
            '  ANTES da carga. Sem ela eu não sei distinguir "aba de instruções" de "aba de\n'
            '  dados que a planilha veio quebrada" — que foi a lição L-21, 19.785 vendas\n'
            '  perdidas por mais de um ano. A carga PARA aqui.')
    with open(ARQUIVO_DOS_IGNORADOS, encoding='utf-8') as f:
        dados = json.load(f)
    abas = dados.get('abas') or []
    if not abas:
        raise RuntimeError(f'{ARQUIVO_DOS_IGNORADOS} não tem nenhuma aba declarada em "abas".')
    return dados


def prefixos_ignorados():
    """Só os começos de nome, para o leitor decidir se a aba é de dados."""
    return [str(a['comeca_com']).strip().upper() for a in ler_ignorados()['abas']]


def texto_dos_ignorados():
    """O pedaço do boletim que repete a lista — o "declarado antes" à vista."""
    dados = ler_ignorados()
    linhas = ['## Ignorado de propósito (declarado antes da carga)', '',
              f'_Lista lida de `{os.path.basename(ARQUIVO_DOS_IGNORADOS)}`, '
              f'atualizada em {dados.get("atualizado_em", "?")}._', '',
              '**Abas de apoio (não são de dados):**', '']
    for a in dados['abas']:
        linhas.append(f'- `{a["comeca_com"]}` — {a["motivo"]}')
    if dados.get('descartes_esperados'):
        linhas += ['', '**Descartes esperados dentro das abas de dados:**', '']
        for d in dados['descartes_esperados']:
            linhas.append(f'- `{d["motivo"]}` — {d["explicacao"]}')
    linhas += ['', 'Qualquer aba com linhas que NÃO esteja nesta lista e não renda nada '
                   'PARA a rodada (lição L-21).', '']
    return '\n'.join(linhas)


# ─── 2. A comparação com a rodada anterior ──────────────────────────────────

def rodada_anterior(base, headers, fonte, origem):
    """A última rodada DESTE ARQUIVO gravada no caderno de bordo, com as partes.

    Devolve None quando este arquivo nunca foi carregado — primeira carga dele
    não tem com o que comparar, e inventar comparação aí seria barrar trabalho
    bom. Quem lê o None precisa DIZER que nada foi comparado; ver
    `comparar_com_a_anterior` e `texto_da_comparacao`.

    ── POR QUE A BUSCA É PELA ORIGEM, E NÃO PELA ÚLTIMA RODADA DE TODAS ──────
    Até 08/08/2026 esta função pegava a **última rodada de todas** (`order=
    id.desc&limit=1`) e só depois filtrava as partes por `origem`. Quando essa
    última rodada era de outro ano, o filtro não achava nada, a comparação
    voltava vazia — e vazia era lida como sucesso. O QA reproduziu: total caindo
    de 500.000 para zero, e o boletim escrevendo "OK — nenhuma parte encolheu".

    Isso não era um caso raro: o `--ano` da rotina mensal tem como padrão o ano
    corrente, então **em janeiro de todo ano** a rodada nova compara com a última
    rodada, que é do ano anterior — e a comparação sumia, calada. É a L-21 escrita
    ao contrário, dentro da peça feita para matá-la.

    Agora a pergunta é a certa: qual foi a última vez que ESTE arquivo entrou?
    """
    # 1) A última parte gravada com esta origem diz qual foi a última rodada dela.
    ultima = requests.get(f'{base}/rest/v1/importacoes_partes',
                          params={'origem': f'eq.{origem}', 'order': 'importacao_id.desc',
                                  'limit': '1', 'select': 'importacao_id'},
                          headers=headers, timeout=60)
    ultima.raise_for_status()
    achadas = ultima.json()
    if not achadas:
        return None                      # este arquivo nunca foi carregado
    importacao_id = achadas[0]['importacao_id']

    # 2) O cabeçalho daquela rodada.
    r = requests.get(f'{base}/rest/v1/importacoes',
                     params={'id': f'eq.{importacao_id}', 'fonte': f'eq.{fonte}',
                             'select': 'id,referencia,linhas_lidas,linhas_entendidas,total_apos'},
                     headers=headers, timeout=60)
    r.raise_for_status()
    linhas = r.json()
    if not linhas:
        return None
    imp = linhas[0]

    # 3) As partes daquela rodada, deste arquivo.
    p = requests.get(f'{base}/rest/v1/importacoes_partes',
                     params={'importacao_id': f'eq.{imp["id"]}', 'origem': f'eq.{origem}',
                             'select': 'parte,lida,linhas_lidas,linhas_entendidas'},
                     headers=headers, timeout=60)
    p.raise_for_status()
    imp['partes'] = {x['parte']: x for x in p.json()}

    # O total gravado no cabeçalho é da rodada INTEIRA; se aquela rodada tocou
    # mais de um arquivo, comparar o total dela com o total deste arquivo seria
    # comparar coisas diferentes. Então o total da comparação é a soma das partes
    # DESTE arquivo, e o do cabeçalho fica só como informação.
    imp['linhas_entendidas_do_arquivo'] = sum(
        int(x.get('linhas_entendidas') or 0) for x in imp['partes'].values())
    return imp


def comparar_com_a_anterior(anterior, contas, origem):
    """Compara a rodada de agora com a anterior. Devolve a lista de gritos.

    Grita em três situações, e as três param a rodada:
      1. uma parte que a rodada anterior conhecia SUMIU do arquivo;
      2. uma parte que rendia alguma coisa passou a render ZERO;
      3. uma parte encolheu mais que o limite (5%).
    E uma quarta sobre o arquivo inteiro: o total entendido encolheu mais que o
    limite.

    Por que "encolheu" e não "mudou": a planilha da Prefeitura é republicada e
    CRESCE — mês novo entra, mês antigo é corrigido para mais. Encolher é o
    sintoma da L-21: a aba veio quebrada e o leitor pulou. Crescimento nunca é
    motivo de parada.
    """
    # ── O TERCEIRO ESTADO: nada comparado NUNCA é sucesso ────────────────────
    #
    # São duas ausências diferentes, e tratá-las igual foi o defeito que o QA
    # achou (05_QA.md §AC.3.2):
    #
    #   (a) este arquivo NUNCA foi carregado -> não há o que comparar, e isso é
    #       legítimo. Passa — mas quem chama é obrigado a DIZER que nada foi
    #       comparado, em vez de escrever "OK, nada encolheu". Ver o
    #       `texto_da_comparacao` e o `sem_comparacao()` aqui embaixo.
    #
    #   (b) existe rodada anterior deste arquivo e ela veio SEM PARTES -> isso é
    #       "não consegui conferir", e "não consegui" vale como reprovado (R-14).
    #       Com a busca por origem isto virou quase impossível; "quase" não serve
    #       para o item cujo erro leva um ano para aparecer.
    if anterior and not anterior.get('partes'):
        return [f'a rodada anterior ({anterior.get("referencia")}) existe no caderno de bordo mas '
                f'não trouxe nenhuma parte do arquivo {origem} — NADA foi comparado. '
                'Não sei dizer se a planilha veio inteira, e não conferido não vale como conferido '
                '(é o R-14 da trava: "não consegui conferir" conta como reprovado)']
    if not anterior:
        return []

    agora = {c.nome: c for c in contas if getattr(c, 'eh_dados', True)}
    gritos = []

    for nome, antes in anterior['partes'].items():
        antes_ok = int(antes.get('linhas_entendidas') or 0)
        if antes_ok <= 0:
            continue                      # não rendia nada antes: nada a comparar
        c = agora.get(nome)
        if c is None:
            gritos.append(f'a parte "{nome}" existia na rodada anterior ({antes_ok:,} linhas entendidas) '
                          f'e SUMIU do arquivo {origem} desta rodada')
            continue
        agora_ok = int(getattr(c, 'entendidas', 0) or 0)
        if agora_ok == 0:
            gritos.append(f'a parte "{nome}" rendia {antes_ok:,} linhas na rodada anterior e agora rende ZERO '
                          f'(leu {getattr(c, "lidas", 0):,} linhas) — é exatamente o retrato da lição L-21')
            continue
        if agora_ok < antes_ok * (1 - QUEDA_MAXIMA):
            queda = (1 - agora_ok / antes_ok) * 100
            gritos.append(f'a parte "{nome}" caiu {queda:.1f}%: eram {antes_ok:,} linhas entendidas '
                          f'e agora são {agora_ok:,} (o limite é {QUEDA_MAXIMA*100:.0f}%)')

    # O total é o DESTE arquivo — a soma das partes dele —, não o total da rodada
    # anterior inteira: se aquela rodada tocou dois anos, o cabeçalho dela soma os
    # dois, e comparar isso com um ano só acusaria uma queda que não existe.
    antes_total = int(anterior.get('linhas_entendidas_do_arquivo')
                      or sum(int((x or {}).get('linhas_entendidas') or 0) for x in anterior['partes'].values()))
    agora_total = sum(int(getattr(c, 'entendidas', 0) or 0) for c in contas if getattr(c, 'eh_dados', True))
    if antes_total > 0 and agora_total < antes_total * (1 - QUEDA_MAXIMA):
        queda = (1 - agora_total / antes_total) * 100
        gritos.append(f'o arquivo {origem} inteiro caiu {queda:.1f}%: eram {antes_total:,} linhas entendidas '
                      f'na rodada {anterior.get("referencia")} e agora são {agora_total:,}')

    return gritos


def sem_comparacao(anterior):
    """Nada foi comparado nesta rodada? Devolve a frase, ou None se comparou.

    Existe para que NENHUM lugar do sistema possa escrever "OK, nada encolheu"
    quando não houve comparação nenhuma. Quem chama a comparação pergunta isto
    antes de dar qualquer OK.
    """
    if not anterior:
        return ('NADA FOI COMPARADO — este arquivo nunca tinha sido carregado, então não há '
                'rodada anterior dele no caderno de bordo. Não é falha; é a primeira vez. '
                'Mas também não é "está tudo bem": ninguém conferiu nada.')
    if not anterior.get('partes'):
        return ('NADA FOI COMPARADO — a rodada anterior não trouxe partes deste arquivo.')
    return None


def texto_da_comparacao(anterior, contas, origem, gritos):
    """O pedaço do boletim que mostra a comparação — inclusive quando está tudo bem.

    Relatório vazio reprova (CA-29): silêncio não é sinal de sucesso.
    """
    linhas = ['## Comparação com a rodada anterior', '']

    # Nada comparado nunca vira "OK". Esta é a mesma frase que o terminal mostra,
    # e ela existe porque o boletim já chegou a escrever "OK — nenhuma parte
    # encolheu" embaixo de uma tabela vazia (05_QA.md §AC.3.2).
    nada = sem_comparacao(anterior)
    if nada:
        linhas += [f'**{nada}**', '']
        if gritos:
            linhas += ['**A RODADA PAROU. O que a comparação encontrou:**', '']
            linhas += [f'- {g}' for g in gritos]
            linhas.append('')
        return '\n'.join(linhas)

    linhas += [f'Rodada anterior: `{anterior.get("referencia")}` — '
               f'{int(anterior.get("linhas_entendidas_do_arquivo") or 0):,} linhas entendidas '
               f'deste arquivo (`{origem}`).', '',
               '| parte | antes | agora | variação |', '|---|---:|---:|---:|']
    agora = {c.nome: c for c in contas if getattr(c, 'eh_dados', True)}
    for nome in sorted(set(list(anterior['partes'].keys()) + list(agora.keys()))):
        antes = int((anterior['partes'].get(nome) or {}).get('linhas_entendidas') or 0)
        depois = int(getattr(agora.get(nome), 'entendidas', 0) or 0) if nome in agora else 0
        if antes == 0 and depois == 0:
            continue
        if antes == 0:
            variacao = 'parte nova'
        elif nome not in agora:
            variacao = 'SUMIU'
        else:
            variacao = f'{(depois/antes - 1) * 100:+.1f}%'
        linhas.append(f'| {nome} | {antes:,} | {depois:,} | {variacao} |')
    linhas.append('')
    if gritos:
        linhas += ['**A RODADA PAROU. O que a comparação encontrou:**', '']
        linhas += [f'- {g}' for g in gritos]
    else:
        linhas.append(f'OK — nenhuma parte encolheu mais que {QUEDA_MAXIMA*100:.0f}% e nenhuma sumiu.')
    linhas.append('')
    return '\n'.join(linhas)


# ─── 3. O grito sai do terminal e vira cartão no quadro ─────────────────────

def _chave_do_quadro():
    """A chave de escrita do ALEX OS (o quadro), não a do Pandora OS (o banco)."""
    caminho = os.path.expanduser('~/.alex-os-secrets')
    if not os.path.exists(caminho):
        return None
    with open(caminho) as f:
        for linha in f:
            linha = linha.strip()
            if linha.startswith('SUPABASE_SERVICE_ROLE_KEY=') or linha.startswith('export SUPABASE_SERVICE_ROLE_KEY='):
                return linha.split('=', 1)[1].strip().strip('"\'')
    return None


def gritar_no_quadro(item_id, titulo, descricao, prioridade='ALTA', ensaio=False):
    """Um cartão POR ASSUNTO, atualizado — nunca um cartão por rodada (D-A12).

    Nunca lança: a rodada não pode quebrar por causa do aviso. Se não conseguir
    gravar, devolve o motivo e quem chamou imprime — o aviso nunca some calado.
    """
    if ensaio or os.environ.get('TRAVA_QUADRO'):
        destino = os.environ.get('TRAVA_QUADRO')
        if destino:
            try:
                with open(destino, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({'quando': time.strftime('%Y-%m-%dT%H:%M:%S'),
                                        'item_id': item_id, 'titulo': titulo,
                                        'descricao': descricao, 'prioridade': prioridade},
                                       ensure_ascii=False) + '\n')
                return True, f'cartão escrito no quadro de mentira ({destino})'
            except Exception as e:
                return False, f'não consegui escrever no quadro de mentira: {e}'
        return True, '(ensaio) o cartão NÃO foi criado'

    chave = _chave_do_quadro()
    if not chave:
        return False, 'não achei a SUPABASE_SERVICE_ROLE_KEY (a do Alex OS) em ~/.alex-os-secrets'
    H = {'apikey': chave, 'Authorization': f'Bearer {chave}', 'Content-Type': 'application/json'}
    corpo = {'item_id': item_id, 'titulo': titulo, 'descricao': descricao,
             'area': 'Trava', 'projeto': 'alexos', 'tipo': 'Trava',
             'prioridade': prioridade, 'coluna': 'a_fazer', 'status': 'aberto'}
    try:
        achado = requests.get(QUADRO, params={'item_id': f'eq.{item_id}', 'select': 'id'},
                              headers=H, timeout=30)
        achado.raise_for_status()
        existentes = achado.json()
        if existentes:
            r = requests.patch(QUADRO, params={'id': f'eq.{existentes[0]["id"]}'},
                               headers=H, json=corpo, timeout=30)
        else:
            r = requests.post(QUADRO, headers=H, json=corpo, timeout=30)
        if r.status_code >= 300:
            return False, f'o quadro recusou a gravação ({r.status_code})'
        return True, 'cartão atualizado' if existentes else 'cartão criado'
    except Exception as e:
        return False, f'não consegui falar com o quadro: {e}'


def parar_a_rodada(assunto, titulo, motivos, boletim=None, ensaio=False):
    """Imprime o veto na tela E o põe no quadro. Devolve o texto do aviso.

    Antes desta peça o veto só aparecia no terminal de quem rodou — e a rotina
    mensal roda sozinha, de madrugada, sem ninguém olhando.
    """
    print(f'\n✗ A RODADA PAROU — {titulo}')
    for m in motivos:
        print(f'   - {m}')
    print('   Nada foi escrito no banco.')

    descricao = (f'A carga do ITBI parou em {time.strftime("%d/%m/%Y %H:%M")}.\n\n'
                 + '\n'.join(f'- {m}' for m in motivos)
                 + '\n\nNada foi escrito no banco. A base continua com o conteúdo da rodada anterior.'
                 + (f'\n\nBoletim completo: {boletim}' if boletim else '')
                 + '\n\nO que fazer: abra o boletim, veja qual parte da planilha veio diferente e '
                   'confira a planilha original antes de rodar de novo. Em 2024 duas abas vieram sem '
                   'linha de título e 19.785 vendas ficaram fora do banco por mais de um ano, sem '
                   'ninguém perceber (lição L-21).')
    ok, motivo = gritar_no_quadro(f'trava:R-11:{assunto}', titulo, descricao, 'ALTA', ensaio)
    print(f'   Quadro da área IA: {motivo}')
    if not ok:
        print('   ATENÇÃO: o aviso NÃO chegou ao quadro. Avise numa sessão DEV.')
    return descricao


# ─── 4. A rede do carregador (o terceiro script) ────────────────────────────

def conferir_boletim_do_arquivo(caminho_db):
    """O `carregar_supabase_v2.py` recusa arquivo sem boletim aprovado.

    Ele era só um carregador: empurrava para o banco o que achasse no arquivo
    local, sem conferir nada. Um arquivo gerado por uma rodada que PAROU seria
    carregado do mesmo jeito.

    Devolve (ok, mensagem). Boletim ausente = não ok. Boletim que registra veto
    = não ok.
    """
    boletim = os.path.splitext(caminho_db)[0] + '_boletim.md'
    if not os.path.exists(boletim):
        return False, (f'não achei o boletim deste arquivo ({boletim}).\n'
                       '  Todo arquivo que vai para o banco precisa vir com o boletim da rodada que o\n'
                       '  gerou — é ele que diz o que NÃO foi importado e por quê. Gere com:\n'
                       '    python3 reconstruir_banco_v2.py --anos <anos> --saida ' + caminho_db)
    with open(boletim, encoding='utf-8') as f:
        texto = f.read()
    marcas_de_veto = ['ERRO — aba com linhas', 'A RODADA PAROU', 'linhas lidas, 0 entendidas']
    achadas = [m for m in marcas_de_veto if m in texto]
    if achadas:
        return False, (f'o boletim {boletim} registra que a rodada teve problema '
                       f'({achadas[0]!r}).\n'
                       '  Arquivo gerado por rodada com veto não vai para o banco. Conserte a origem\n'
                       '  e gere o arquivo de novo.')
    if 'OK — nenhuma aba com linhas ficou sem nada entendido' not in texto:
        return False, (f'o boletim {boletim} não diz que a rodada terminou bem.\n'
                       '  Esperava a linha "OK — nenhuma aba com linhas ficou sem nada entendido".\n'
                       '  Sem essa linha eu não tenho como saber se o arquivo está inteiro.')
    return True, f'boletim conferido: {os.path.basename(boletim)}'


def conferir_o_que_saiu(total_no_arquivo, enviados):
    """"Arquivo com linhas, zero enviadas" é FALHA, não resultado.

    É a L-21 do lado do carregador: um erro que faz o laço não rodar nenhuma vez
    terminaria com "0 registros enviados" e código de saída zero — sucesso
    aparente com o banco intocado.
    """
    if total_no_arquivo > 0 and enviados == 0:
        return False, (f'o arquivo tem {total_no_arquivo:,} linhas e ZERO foram enviadas.\n'
                       '  Isso não é resultado, é falha: silêncio não é sinal de sucesso (lição L-21).')
    return True, ''
