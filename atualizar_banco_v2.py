#!/usr/bin/env python3
"""
Rotina mensal da base ITBI — versão 2 (base definitiva, projeto Pandora OS).
============================================================================
Substitui o `atualizar_banco.py`, que continua no repositório apontando para a base
antiga e serve como volta atrás.

O QUE MUDOU, e por quê (07/08/2026):

  1. Escreve na base NOVA (projeto Pandora OS), não na antiga.
  2. Usa o MESMO leitor da reconstrução (`reconstruir_banco_v2`). Antes havia dois
     programas lendo a mesma planilha de formas ligeiramente diferentes — foi assim
     que 124 mil revendas se perderam em 2026. Agora existe um leitor só.
  3. A chave de deduplicação inclui a MATRÍCULA, igual à da base. Se divergirem, a
     rodada reinsere como novidade o que já está lá.
  4. O banco é o único dono da verdade: manda tudo e deixa o banco ignorar repetido
     (a impressão digital é índice único). Não existe mais "banco local publicado no
     GitHub" — com 2,66 milhões de linhas o arquivo passaria do limite do GitHub.
  5. Publica sozinha o ARQUIVO DO ACM no cofre. Antes ninguém publicava: o arquivo
     ficou parado no conteúdo de 26/07/2026 sem ninguém perceber.
  6. Grava o BOLETIM no caderno de bordo (lição L-21) e compara com a rodada anterior.

Uso:
  python3 atualizar_banco_v2.py [--ano 2026] [--ensaio]

  --ensaio   faz tudo menos escrever no banco e no cofre (para testar sem efeito)

Autor: Claude Code (Opus 5) · 07/08/2026
"""
import os, re, sys, json, time, gzip, shutil, sqlite3, argparse, tempfile
import urllib.request
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reconstruir_banco_v2 as leitor
import trava_itbi

PROJETO = 'ijyxkyxovhvifrtfnqvs'          # Pandora OS — a base definitiva
BASE = f'https://{PROJETO}.supabase.co'
PAGINA_ITBI = 'https://prefeitura.sp.gov.br/web/fazenda/w/acesso_a_informacao/31501'
PLAN_DIR = '/Users/accf81/Documents/IA/Claude/Projects/Dados ITBI/planilhas_originais'
BOLETINS_DIR = '/Users/accf81/Documents/IA/Claude/Projects/Dados ITBI/boletins'
# O banco completo local — fonte do arquivo que o ACM baixa. Fica em pasta DURÁVEL, não na
# pasta temporária do sistema: o macOS limpa a temporária, e entre uma rodada e outra passam
# 30 dias. Com o caminho antigo, a rotina simplesmente não publicaria o arquivo do ACM na
# rodada seguinte — e o ACM voltaria a congelar em silêncio, que é o problema que este
# programa existe para resolver. (Achado da auditoria de 07/08/2026.)
BANCO_LOCAL = '/Users/accf81/Documents/IA/Claude/Projects/Dados ITBI/banco_local/itbi_completo.db'
ANO = time.localtime().tm_year

# Colunas do arquivo que o ACM do Alex OS baixa — RECORTE, não a base inteira.
COLS_ACM = ['sql','data_transacao','logradouro','numero','complemento','bairro','referencia',
            'area_construida_m2','valor_transacao','valor_m2','cartorio','matricula','ano',
            'logradouro_norm','logradouro_fmt','proporcao_transmitida']
ACM_ANO_MIN = 2019     # mesmo corte do ITBI_ANO_MIN do Alex OS (js/imoveis/core.js)


def secret(nome):
    caminho = os.path.expanduser('~/.alex-os-secrets')
    if not os.path.exists(caminho):
        return None
    with open(caminho) as f:
        for linha in f:
            if linha.strip().startswith(f'{nome}='):
                return linha.strip().split('=', 1)[1]
    return None


def baixar_planilha(ano):
    """Descobre o link na página oficial (ele muda a cada republicação, sem aviso) e baixa."""
    h = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(PAGINA_ITBI, headers=h, timeout=60)
    r.raise_for_status()
    m = re.search(rf'<strong>{ano}\s*\(<a href="([^"]+)"[^>]*>Excel/xlsx</a>', r.text)
    if not m:
        raise RuntimeError(f'Não achei o link do XLSX de {ano} na página oficial — '
                           'o layout da página pode ter mudado.')
    url = m.group(1)
    if url.startswith('/'):
        url = 'https://prefeitura.sp.gov.br' + url
    destino = os.path.join(PLAN_DIR, f'{ano}.xlsx')
    print(f'  baixando {url[:90]}...')
    resp = requests.get(url, headers=h, timeout=600)
    resp.raise_for_status()

    # CONFERIR ANTES DE SOBRESCREVER (achado da auditoria de 07/08/2026).
    # `raise_for_status()` não basta: um servidor pode devolver uma página de erro em HTML
    # com status 200, e aí gravaríamos o HTML por cima da planilha original — que é a nossa
    # única fonte de verdade, guardada justamente para nunca precisar baixar de novo.
    # Um .xlsx é um arquivo zip: começa com 'PK'.
    if resp.content[:2] != b'PK':
        raise RuntimeError(
            f'O que veio da Prefeitura não é uma planilha (começa com {resp.content[:16]!r}). '
            f'A planilha guardada em {destino} NÃO foi tocada.')
    if len(resp.content) < 1_000_000:
        raise RuntimeError(
            f'A planilha veio pequena demais ({len(resp.content)/1024:.0f} KB) — as do ITBI '
            f'passam de 15 MB. A planilha guardada em {destino} NÃO foi tocada.')

    # Guarda a anterior até o novo estar gravado: se o disco encher no meio da escrita,
    # não ficamos sem nenhuma das duas.
    if os.path.exists(destino):
        shutil.copy2(destino, destino + '.anterior')
    with open(destino, 'wb') as f:
        f.write(resp.content)
    print(f'  arquivado em {destino} ({len(resp.content)/1048576:.0f} MB)')
    return destino


def enviar_lote(url, headers, dados, tentativas=5):
    corpo = json.dumps(dados).encode('utf-8')
    for t in range(tentativas):
        req = urllib.request.Request(url, data=corpo, method='POST', headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                r.read()
            return
        except Exception as e:
            if t == tentativas - 1:
                raise
            time.sleep(4 * (t + 1))


def contar(H):
    """Total de linhas na base.

    Duas formas foram testadas em 07/08/2026, nesta tabela de 2,66 milhões de linhas:

      1. `select=count` (agregado)  — devolveu 500 sob carga. O agregado varre a tabela
         inteira e estoura o tempo limite quando o banco está ocupado. Instável nesta
         escala, por isso NÃO é usada aqui.
      2. `limit=1` + `Prefer: count=exact`, lendo o cabeçalho `content-range` — devolve
         `0-0/2663725`. É a forma canônica do PostgREST e a que se usa.

    Cuidado que motivou este comentário: a primeira versão desta função quebrou DEPOIS do
    envio já ter dado certo. Contador que falha no fim faz uma rodada bem-sucedida parecer
    falha — e o passo seguinte (publicar o arquivo do ACM) deixa de acontecer.

    ACHADO DE 10/08/2026: mesmo a forma canônica quebrava com 500 logo depois de um envio
    grande. Causa raiz (confirmada com EXPLAIN ANALYZE): a contagem usa um índice e não
    devia precisar abrir as vendas uma por uma — mas só consegue esse atalho se o "mapa de
    visibilidade" do Postgres estiver em dia, e um envio grande deixa ele desatualizado nas
    páginas recém-escritas. Nesse estado a contagem precisou abrir 325 mil vendas à toa e
    levou 5,4s; toda consulta tem um limite de 8s, e a soma com a carga do envio estourava
    esse limite. `limpar_vendas_itbi()` roda antes desta função para evitar isso — ver lá."""
    r = requests.get(f'{BASE}/rest/v1/vendas_itbi?select=id&limit=1',
                     headers={**H, 'Prefer': 'count=exact'}, timeout=180)
    r.raise_for_status()
    faixa = r.headers.get('content-range', '')
    total = faixa.split('/')[-1] if '/' in faixa else ''
    if not total.isdigit():
        raise RuntimeError(f'Não consegui contar as linhas da base (content-range: {faixa!r}).')
    return int(total)


def limpar_vendas_itbi():
    """Roda a limpeza de rotina do Postgres (VACUUM ANALYZE) na tabela logo após um envio
    grande, para que a contagem seguinte não precise abrir vendas uma por uma (ver o
    comentário longo em `contar()`). Não apaga nem muda nenhum dado — só atualiza o
    índice e o "mapa de visibilidade" internos do banco.

    VACUUM não pode rodar dentro de uma transação, e a API normal do banco (PostgREST)
    sempre embrulha cada chamada numa transação — por isso não dá para pedir isso pela
    mesma porta usada para ler/escrever venda. Usa a API de administração do Supabase
    (o token já existente em SUPABASE_ACCESS_TOKEN, sem precisar de senha nova).

    Falha aqui não é motivo para parar a rodada: na pior das hipóteses a contagem
    seguinte volta a correr o risco antigo, mas o dado em si não é afetado."""
    token = secret('SUPABASE_ACCESS_TOKEN')
    if not token:
        print('   ⚠ SUPABASE_ACCESS_TOKEN não configurado — pulando a limpeza (a contagem '
              'a seguir pode voltar a dar erro sob carga).')
        return False
    try:
        r = requests.post(
            f'https://api.supabase.com/v1/projects/{PROJETO}/database/query',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'query': 'vacuum (analyze) vendas_itbi;'}, timeout=120)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f'   ⚠ não consegui limpar a tabela antes de contar: {e}')
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ano', type=int, default=ANO)
    p.add_argument('--ensaio', action='store_true',
                   help='faz tudo menos escrever no banco e no cofre')
    args = p.parse_args()

    key = secret('SUPABASE_SERVICE_ROLE_KEY_PANDORA_OS')
    if not key:
        print('✗ Falta SUPABASE_SERVICE_ROLE_KEY_PANDORA_OS em ~/.alex-os-secrets.')
        print('  ATENÇÃO: a chave do projeto ANTIGO não serve aqui — cada projeto tem a sua.')
        sys.exit(1)
    H = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}

    print(f"\n{'='*60}\n  ROTINA MENSAL DO ITBI — {args.ano}"
          f"{'  (ENSAIO: não escreve nada)' if args.ensaio else ''}\n{'='*60}\n")
    t0 = time.time()

    # ─── 1. Baixar e arquivar a planilha do ano ──────────────────────────────
    # No modo ensaio NÃO baixa: "não escreve nada" tem de valer também para a pasta das
    # planilhas originais, que é a nossa fonte de verdade. Antes o ensaio sobrescrevia a
    # planilha no passo 1 e só parava no passo 3 (achado da auditoria de 07/08/2026).
    if args.ensaio:
        caminho = os.path.join(PLAN_DIR, f'{args.ano}.xlsx')
        print(f'1. (ensaio) NÃO baixando — usando a planilha já arquivada: {caminho}')
        if not os.path.exists(caminho):
            print('   ✗ ela não existe. Rode sem --ensaio para baixar.')
            sys.exit(1)
    else:
        print('1. Baixando a planilha da Prefeitura')
        caminho = baixar_planilha(args.ano)

    # ─── 2. Ler com o MESMO leitor da reconstrução ───────────────────────────
    print('\n2. Lendo a planilha (mesmo leitor da base)')
    tmp = os.path.join(tempfile.gettempdir(), f'itbi_mensal_{args.ano}.db')
    if os.path.exists(tmp):
        os.remove(tmp)
    conn = leitor.criar_banco(tmp)
    contas = leitor.processar_planilha(caminho, args.ano, conn)
    leitor.indexar(conn)

    # Veto da L-21: aba que TEM linhas e não rendeu nada é falha, não silêncio.
    falhas = [c for c in contas if c.eh_dados and c.lidas > 0 and c.entendidas == 0]
    lidas = sum(c.lidas for c in contas)
    entendidas = sum(c.entendidas for c in contas)
    nao_lidas = [c for c in contas if c.eh_dados and not c.lida]
    total_local = conn.execute('select count(*) from vendas').fetchone()[0]
    print(f'   {lidas:,} lidas · {entendidas:,} entendidas · {total_local:,} distintas')
    for c in nao_lidas:
        print(f'   ⚠ aba NÃO lida: {c.nome} — {c.motivo}')
    if falhas:
        # O grito SAI DO TERMINAL: esta rotina roda sozinha, de madrugada, e
        # ninguém está olhando a tela. Agora ela também vira cartão no quadro.
        trava_itbi.parar_a_rodada(
            assunto=f'aba-vazia-{args.ano}',
            titulo=f'ITBI {args.ano}: {len(falhas)} aba(s) com linhas e nada aproveitado',
            motivos=[f'{c.nome}: {c.lidas:,} linhas lidas, 0 entendidas' for c in falhas],
            ensaio=args.ensaio)
        sys.exit(1)

    # ── Comparação com a rodada anterior (R-11 da trava) ─────────────────────
    # O caderno de bordo já guardava os totais de cada rodada; faltava LER a
    # última e gritar na variação. Parte que encolhe é o sintoma da L-21: a aba
    # veio quebrada e o leitor pulou, sem erro nenhum. Crescimento nunca para
    # nada — a planilha da Prefeitura é republicada e cresce.
    print('\n2b. Comparando com a rodada anterior (caderno de bordo)')
    origem_do_arquivo = os.path.basename(caminho)
    try:
        anterior = trava_itbi.rodada_anterior(BASE, H, 'itbi', origem_do_arquivo)
    except Exception as e:
        print(f'   ✗ não consegui ler a rodada anterior: {e}')
        print('   A rodada PARA aqui: sem a comparação eu não sei se a planilha veio inteira.')
        print('   (isto é o R-14 da trava: "não consegui conferir" vale como reprovado)')
        sys.exit(1)
    gritos = trava_itbi.comparar_com_a_anterior(anterior, contas, origem_do_arquivo)
    nada_comparado = trava_itbi.sem_comparacao(anterior)
    if anterior and not nada_comparado:
        print(f'   rodada anterior deste arquivo: {anterior.get("referencia")} '
              f'({int(anterior.get("linhas_entendidas_do_arquivo") or 0):,} entendidas em {origem_do_arquivo})')
    if gritos:
        trava_itbi.parar_a_rodada(
            assunto=f'variacao-{args.ano}',
            titulo=f'ITBI {args.ano}: a planilha encolheu de uma rodada para a outra',
            motivos=gritos, ensaio=args.ensaio)
        sys.exit(1)
    # "Nada comparado" NUNCA vira "OK". São dois desfechos diferentes e cada um
    # tem a sua frase — foi confundi-los que deixou a rodada de janeiro passar
    # calada, com o total caindo a zero (05_QA.md §AC.3.2).
    if nada_comparado:
        print(f'   {nada_comparado}')
    else:
        print('   OK — nenhuma parte sumiu nem encolheu além do limite de '
              f'{trava_itbi.QUEDA_MAXIMA*100:.0f}%')

    if args.ensaio:
        print('\n' + trava_itbi.texto_dos_ignorados())
        print(trava_itbi.texto_da_comparacao(anterior, contas, origem_do_arquivo, gritos))
        print('(ensaio) Pararia aqui sem escrever. Banco local em: ' + tmp)
        return

    # ─── 3. Enviar ao banco (o banco ignora o que já tem) ────────────────────
    print('\n3. Enviando ao banco (repetido é ignorado pela impressão digital)')
    antes = contar(H)
    url = f'{BASE}/rest/v1/vendas_itbi?on_conflict=chave_dedup'
    hh = {**H, 'Prefer': 'return=minimal,resolution=ignore-duplicates'}
    cur = conn.execute(f"select {','.join(leitor.COLS_BANCO)} from vendas")
    enviados = 0
    while True:
        linhas = cur.fetchmany(1000)
        if not linhas:
            break
        enviar_lote(url, hh, [dict(zip(leitor.COLS_BANCO, l)) for l in linhas])
        enviados += len(linhas)
    print('   limpando a tabela antes de contar de novo (achado de 10/08/2026)...')
    limpar_vendas_itbi()
    depois = contar(H)
    novas = depois - antes
    print(f'   {enviados:,} enviados · base foi de {antes:,} para {depois:,} ({novas:,} novas)')

    # ─── 3b. Espelhar as vendas novas na cópia local ─────────────────────────
    # O passo 5 gera o arquivo do ACM a partir da cópia local, NÃO do banco na nuvem.
    # Sem este passo a cópia ficava parada: o site ganhava as vendas novas, o ACM era
    # republicado com o dado do mês anterior e o aviso dizia que deu tudo certo.
    # É a L-21 se disfarçando de sucesso. (Achado de 08/08/2026, antes da 1ª rodada.)
    print('\n3b. Espelhando as vendas na cópia local (a que gera o arquivo do ACM)')
    local_ok = espelhar_no_banco_local(tmp)

    # ─── 4. Atualizar a lista de ruas do autopreencher ──────────────────────
    print('\n4. Atualizando a lista de ruas')
    requests.post(f'{BASE}/rest/v1/rpc/atualizar_ruas_itbi', headers=H, json={}, timeout=300)
    print('   ✓')

    # ─── 5. Republicar o arquivo do ACM (recorte residencial, 2019+) ────────
    # Isto NÃO existia antes: o arquivo ficava parado até alguém subir à mão.
    print('\n5. Republicando o arquivo do ACM')
    acm_ok = publicar_arquivo_acm(key) if local_ok else False
    if not local_ok:
        print('   ✗ NÃO PUBLIQUEI: a cópia local não recebeu as vendas novas (passo 3b).')
        print('     Publicar agora subiria dado velho parecendo novo.')

    # ─── 6. Boletim no caderno de bordo (L-21) ──────────────────────────────
    print('\n6. Gravando o boletim')
    aviso = montar_aviso(novas, nao_lidas, acm_ok)
    gravar_boletim(H, args.ano, lidas, entendidas, novas, depois, contas, aviso,
                   extras=[trava_itbi.texto_dos_ignorados(),
                           trava_itbi.texto_da_comparacao(anterior, contas,
                                                          origem_do_arquivo, gritos)])

    print(f'\n✅ Terminado em {time.time()-t0:.0f}s')
    print(f'   Aviso para o Alex: "{aviso}"')
    conn.close()


def montar_aviso(novas, nao_lidas, acm_ok=True):
    """A mensagem que chega ao Alex. Desde a L-21 ela diz também o que ficou DE FORA.

    O `acm_ok` entrou em 07/08/2026, pela auditoria: quando o arquivo do ACM não era
    publicado, o programa imprimia "PULADO" no terminal e o aviso ao Alex continuava
    dizendo só "atualizado, N vendas novas". Ou seja, a mesma doença que a L-21 conserta
    no dado estava viva no arquivo — falha que não reclama."""
    if novas == 0:
        base = 'Banco ITBI conferido — sem vendas novas este mês.'
    else:
        base = f'Banco ITBI atualizado: {novas:,} vendas novas.'.replace(',', '.')
    if nao_lidas:
        nomes = ', '.join(c.nome for c in nao_lidas)
        base += f' Atenção: parte da planilha não pôde ser lida ({nomes}) e ficou de fora.'
    if not acm_ok:
        base += (' ATENÇÃO: o arquivo que o ACM usa NÃO foi atualizado — o ACM segue com '
                 'o dado do mês passado. Precisa olhar numa sessão DEV.')
    return base


def espelhar_no_banco_local(banco_do_mes):
    """Copia as vendas do mês para a cópia local completa (BANCO_LOCAL).

    Por que existe: o arquivo que o ACM baixa é gerado a partir de BANCO_LOCAL, não do
    banco na nuvem. Se a cópia não receber as vendas novas, o ACM trabalha com dado velho
    e ninguém fica sabendo — porque a rodada termina com sucesso em tudo o mais.

    Seguro de repetir: a cópia tem índice único na impressão digital (`idx_dedup`), então
    `insert or ignore` descarta o que já está lá. Devolve True só se realmente espelhou.
    """
    if not os.path.exists(BANCO_LOCAL):
        print(f'   ✗ a cópia local não existe: {BANCO_LOCAL}')
        print('     Para refazer (leva ~9 min): python3 reconstruir_banco_v2.py '
              f'--anos 2006-2026 --saida {BANCO_LOCAL}')
        return False
    try:
        dst = sqlite3.connect(BANCO_LOCAL)
        # `id` fica DE FORA de propósito. Ele é só o número de ordem interno de cada
        # banco, e os dois numeram do 1. Copiá-lo faria o `insert or ignore` descartar
        # a venda por choque de número, não por ser repetida — e como o `ignore` é
        # calado, a rodada terminaria dizendo "0 novas" com tudo certo na tela.
        # Pego por teste antes da 1ª rodada; sem ele, o espelho não espelharia nada.
        cols_dst = [r[1] for r in dst.execute('pragma table_info(vendas)') if r[1] != 'id']
        src = sqlite3.connect(banco_do_mes)
        cols_src = [r[1] for r in src.execute('pragma table_info(vendas)')]
        src.close()
        # Recusa em vez de escrever torto: se os formatos divergirem, `insert select *`
        # gravaria valor na coluna errada, em silêncio e sem volta.
        faltando = [c for c in cols_dst if c not in cols_src]
        if faltando:
            print('   ✗ os dois bancos não têm o mesmo formato — não escrevi nada.')
            print(f'     Falta na leitura do mês: {", ".join(faltando)}')
            dst.close()
            return False
        antes = dst.execute('select count(*) from vendas').fetchone()[0]
        dst.execute('attach database ? as mes', (banco_do_mes,))
        lista = ','.join(f'"{c}"' for c in cols_dst)
        dst.execute(f'insert or ignore into vendas ({lista}) select {lista} from mes.vendas')
        dst.commit()
        depois = dst.execute('select count(*) from vendas').fetchone()[0]
        recente = dst.execute('select max(data_transacao) from vendas').fetchone()[0]
        dst.execute('detach database mes')
        dst.close()
        print(f'   ✓ cópia local foi de {antes:,} para {depois:,} '
              f'({depois-antes:,} novas) · venda mais recente: {str(recente)[:10]}')
        return True
    except Exception as e:
        print(f'   ✗ não deu para espelhar na cópia local: {e}')
        return False


def publicar_arquivo_acm(key):
    """Gera o recorte que o ACM do Alex OS baixa e sobe ao cofre.
    RECORTE de propósito: residencial, 2019+, as 16 colunas de sempre. O arquivo é
    baixado inteiro no navegador; a base completa passaria de 300 MB e travaria a aba."""
    origem = os.path.join(tempfile.gettempdir(), 'itbi_acm.db')
    if os.path.exists(origem):
        os.remove(origem)
    # o recorte sai do próprio banco na nuvem seria lento; sai do banco local do mês?
    # não: o ACM precisa da base INTEIRA, não só do mês. Baixa a base do Supabase por
    # páginas seria demorado — então o arquivo é regerado a partir do banco completo
    # local quando ele existe, e senão é pulado com aviso claro.
    completo = BANCO_LOCAL
    if not os.path.exists(completo):
        print('   ✗ NÃO PUBLIQUEI o arquivo do ACM: falta o banco completo local.')
        print(f'     Esperado em: {completo}')
        print('     Para refazer (leva ~9 min): python3 reconstruir_banco_v2.py '
              f'--anos 2006-2026 --saida {completo}')
        return False
    src = sqlite3.connect(completo)
    dst = sqlite3.connect(origem)
    dst.execute('PRAGMA page_size=8192')
    dst.execute(f"CREATE TABLE vendas ({','.join(c + ' TEXT' for c in COLS_ACM)})")
    cur = src.execute(f"select {','.join(COLS_ACM)} from vendas "
                      f"where residencial=1 and ano >= {ACM_ANO_MIN}")
    n = 0
    while True:
        lote = cur.fetchmany(20000)
        if not lote:
            break
        dst.executemany(f"INSERT INTO vendas VALUES ({','.join(['?']*len(COLS_ACM))})", lote)
        n += len(lote)
    dst.commit()
    for col in ['logradouro_norm', 'referencia', 'bairro', 'ano']:
        dst.execute(f'CREATE INDEX idx_{col} ON vendas({col})')
    dst.commit()
    dst.execute('VACUUM')
    dst.close()
    src.close()
    with open(origem, 'rb') as f, gzip.open(origem + '.gz', 'wb', compresslevel=9) as o:
        shutil.copyfileobj(f, o)
    tam = os.path.getsize(origem + '.gz')
    with open(origem + '.gz', 'rb') as f:
        r = requests.post(
            f'{BASE}/storage/v1/object/itbi/ITBI_SP_residencial.db.gz',
            headers={'apikey': key, 'Authorization': f'Bearer {key}',
                     'Content-Type': 'application/gzip', 'x-upsert': 'true'},
            data=f, timeout=900)
    if r.status_code >= 300:
        print(f'   ✗ Falhou ao publicar: {r.status_code} {r.text[:200]}')
        return False
    print(f'   ✓ {n:,} vendas · {tam/1048576:.1f} MB publicados no cofre')
    return True


def gravar_boletim(H, ano, lidas, entendidas, novas, total, contas, aviso, extras=None):
    """Grava em DOIS lugares: arquivo (sobrevive a falha de rede) e banco (para o mês
    seguinte comparar). Lição L-21: toda importação declara o que NÃO importou."""
    os.makedirs(BOLETINS_DIR, exist_ok=True)
    ref = time.strftime('%Y-%m')
    caminho = os.path.join(BOLETINS_DIR, f'{ref}.md')
    linhas = [f'# Rotina mensal do ITBI — {ref}', '',
              f'- planilha: {ano}', f'- linhas lidas: {lidas:,}',
              f'- entendidas: {entendidas:,}', f'- vendas novas na base: {novas:,}',
              f'- total da base ao fim: {total:,}', '',
              '## Abas', '']
    for c in contas:
        if not c.eh_dados:
            continue
        estado = 'lida' if c.lida else f'NÃO LIDA — {c.motivo}'
        linhas.append(f'- {c.nome}: {c.lidas:,} lidas · {c.entendidas:,} entendidas · {estado}')
    linhas += ['', f'## Aviso enviado ao Alex', '', f'> {aviso}', '']
    # A lista do que se ignora de propósito e a comparação com a rodada anterior
    # entram no boletim SEMPRE, inclusive quando está tudo bem: relatório vazio
    # reprova, porque silêncio não é sinal de sucesso (CA-29 e lição L-21).
    for bloco in (extras or []):
        linhas += ['', bloco]
    with open(caminho, 'w') as f:
        f.write('\n'.join(linhas))
    print(f'   arquivo: {caminho}')

    try:
        r = requests.post(f'{BASE}/rest/v1/importacoes',
                          headers={**H, 'Prefer': 'return=representation'},
                          json={'fonte': 'itbi', 'referencia': ref, 'linhas_lidas': lidas,
                                'linhas_entendidas': entendidas, 'linhas_novas': novas,
                                'total_apos': total,
                                'abas_encontradas': len([c for c in contas if c.eh_dados]),
                                'abas_lidas': len([c for c in contas if c.eh_dados and c.lida]),
                                'terminou_em_erro': False, 'aviso_enviado': aviso},
                          timeout=60)
        imp_id = r.json()[0]['id']
        partes = [{'importacao_id': imp_id, 'parte': c.nome, 'origem': f'{ano}.xlsx',
                   'layout': c.layout, 'lida': c.lida, 'motivo_nao_lida': c.motivo,
                   'linhas_lidas': c.lidas, 'linhas_entendidas': c.entendidas}
                  for c in contas if c.eh_dados]
        requests.post(f'{BASE}/rest/v1/importacoes_partes', headers=H, json=partes, timeout=120)
        print(f'   caderno de bordo: importação #{imp_id}')
    except Exception as e:
        print(f'   ⚠ não deu para gravar no caderno de bordo: {e}')
        print(f'     (o arquivo em {caminho} tem tudo — nada se perdeu)')


if __name__ == '__main__':
    main()
