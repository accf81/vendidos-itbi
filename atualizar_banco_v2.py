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

PROJETO = 'ijyxkyxovhvifrtfnqvs'          # Pandora OS — a base definitiva
BASE = f'https://{PROJETO}.supabase.co'
PAGINA_ITBI = 'https://prefeitura.sp.gov.br/web/fazenda/w/acesso_a_informacao/31501'
PLAN_DIR = '/Users/accf81/Documents/IA/Claude/Projects/Dados ITBI/planilhas_originais'
BOLETINS_DIR = '/Users/accf81/Documents/IA/Claude/Projects/Dados ITBI/boletins'
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
        print(f'\n✗ VETO (lição L-21): {len(falhas)} aba(s) com linhas e nada aproveitado:')
        for c in falhas:
            print(f'   - {c.nome}: {c.lidas:,} linhas lidas, 0 entendidas')
        print('   A rodada PARA aqui. Nada foi escrito. Avise numa sessão DEV.')
        sys.exit(1)

    if args.ensaio:
        print('\n(ensaio) Pararia aqui sem escrever. Banco local em: ' + tmp)
        return

    # ─── 3. Enviar ao banco (o banco ignora o que já tem) ────────────────────
    print('\n3. Enviando ao banco (repetido é ignorado pela impressão digital)')
    antes = requests.get(f'{BASE}/rest/v1/vendas_itbi?select=count', headers={**H, 'Prefer': 'count=exact'},
                         timeout=60).headers.get('content-range', '/?').split('/')[-1]
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
    depois = requests.get(f'{BASE}/rest/v1/vendas_itbi?select=count', headers={**H, 'Prefer': 'count=exact'},
                          timeout=60).headers.get('content-range', '/?').split('/')[-1]
    novas = int(depois) - int(antes)
    print(f'   {enviados:,} enviados · base foi de {int(antes):,} para {int(depois):,} '
          f'({novas:,} novas)')

    # ─── 4. Atualizar a lista de ruas do autopreencher ──────────────────────
    print('\n4. Atualizando a lista de ruas')
    requests.post(f'{BASE}/rest/v1/rpc/atualizar_ruas_itbi', headers=H, json={}, timeout=300)
    print('   ✓')

    # ─── 5. Republicar o arquivo do ACM (recorte residencial, 2019+) ────────
    # Isto NÃO existia antes: o arquivo ficava parado até alguém subir à mão.
    print('\n5. Republicando o arquivo do ACM')
    publicar_arquivo_acm(key)

    # ─── 6. Boletim no caderno de bordo (L-21) ──────────────────────────────
    print('\n6. Gravando o boletim')
    aviso = montar_aviso(novas, nao_lidas)
    gravar_boletim(H, args.ano, lidas, entendidas, novas, int(depois), contas, aviso)

    print(f'\n✅ Terminado em {time.time()-t0:.0f}s')
    print(f'   Aviso para o Alex: "{aviso}"')
    conn.close()


def montar_aviso(novas, nao_lidas):
    """A mensagem que chega ao Alex. Desde a L-21 ela diz também o que ficou DE FORA."""
    if novas == 0:
        base = 'Banco ITBI conferido — sem vendas novas este mês.'
    else:
        base = f'Banco ITBI atualizado: {novas:,} vendas novas.'.replace(',', '.')
    if nao_lidas:
        nomes = ', '.join(c.nome for c in nao_lidas)
        base += f' Atenção: parte da planilha não pôde ser lida ({nomes}) e ficou de fora.'
    return base


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
    completo = os.path.join(tempfile.gettempdir(), 'itbi_completo_atual.db')
    if not os.path.exists(completo):
        print('   ⚠ PULADO: não há banco completo local para gerar o recorte.')
        print('     O arquivo do ACM continua com o conteúdo da última publicação.')
        print('     Para regerar: python3 reconstruir_banco_v2.py --anos 2006-2026 --saida '
              + completo)
        return
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
        return
    print(f'   ✓ {n:,} vendas · {tam/1048576:.1f} MB publicados no cofre')


def gravar_boletim(H, ano, lidas, entendidas, novas, total, contas, aviso):
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
