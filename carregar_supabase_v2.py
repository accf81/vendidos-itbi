#!/usr/bin/env python3
"""
Carga da base ITBI nova (21 anos, todos os tipos) para o Supabase do Pandora OS.
================================================================================
Diferenças em relação ao `carregar_supabase.py` (que continua servindo à base antiga):

  - Projeto de destino vem por parâmetro, não fixo no código.
  - 36 colunas (as 28 da Prefeitura + derivadas + origem + impressão digital).
  - RETOMÁVEL: usa a impressão digital (`chave_dedup`, índice único criado na
    migração 032) com `resolution=ignore-duplicates`. Rodar duas vezes não duplica
    nada, e uma carga interrompida no meio recomeça de onde parou sem limpar tudo.
    O carregador antigo abortava e mandava recomeçar do zero — inviável com 2,65
    milhões de linhas.
  - MEDE os primeiros lotes e projeta o tempo total antes de seguir (ADR D-7).
    Se a projeção estourar o limite, ele PARA e pergunta, em vez de deixar rodando
    no escuro por horas.

Uso:
  python3 carregar_supabase_v2.py <arquivo.db> <projeto> [--limite-min N] [--comecar-em N]

Precisa da SUPABASE_SERVICE_ROLE_KEY em ~/.alex-os-secrets.
Autor: Claude Code (Opus 5) · 06/08/2026
"""
import sqlite3, sys, os, json, time, urllib.request, urllib.error, argparse

LOTE = 1000          # linhas por requisição
AMOSTRA = 20         # lotes medidos antes de projetar o tempo total

CAMPOS = ['sql', 'data_transacao', 'logradouro', 'numero', 'complemento', 'bairro',
          'referencia', 'cep', 'natureza_transacao', 'valor_transacao',
          'valor_venal_referencia', 'proporcao_transmitida',
          'valor_venal_referencia_proporcional', 'base_calculo_adotada',
          'tipo_financiamento', 'valor_financiado', 'cartorio', 'matricula',
          'situacao_sql', 'area_terreno_m2', 'testada_m', 'fracao_ideal',
          'area_construida_m2', 'uso_iptu', 'descricao_uso_iptu', 'padrao_iptu',
          'descricao_padrao_iptu', 'acc_iptu', 'valor_m2', 'ano', 'logradouro_norm',
          'logradouro_fmt', 'residencial', 'ano_planilha', 'aba_origem', 'chave_dedup']


def ler_secret(nome):
    caminho = os.path.expanduser('~/.alex-os-secrets')
    if not os.path.exists(caminho):
        return None
    with open(caminho) as f:
        for linha in f:
            if linha.strip().startswith(f'{nome}='):
                return linha.strip().split('=', 1)[1]
    return None


def enviar(url, headers, dados, tentativas=5):
    corpo = json.dumps(dados).encode('utf-8')
    for t in range(tentativas):
        req = urllib.request.Request(url, data=corpo, method='POST', headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                resp.read()
            return
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode()[:400]
            # 4xx é erro nosso (dado ou permissão) — insistir não adianta.
            if e.code < 500 or t == tentativas - 1:
                raise RuntimeError(f'HTTP {e.code}: {detalhe}')
        except Exception:
            if t == tentativas - 1:
                raise
        time.sleep(4 * (t + 1))


def humano(seg):
    if seg < 90:
        return f'{seg:.0f}s'
    if seg < 5400:
        return f'{seg/60:.0f}min'
    return f'{seg/3600:.1f}h'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('db')
    p.add_argument('projeto')
    p.add_argument('--limite-min', type=float, default=90,
                   help='se a projeção passar disso (minutos), para e pergunta')
    p.add_argument('--comecar-em', type=int, default=0,
                   help='pula as N primeiras linhas (para retomar)')
    p.add_argument('--seguir', action='store_true',
                   help='não para na projeção, mesmo se passar do limite')
    p.add_argument('--max-linhas', type=int, default=0,
                   help='envia no máximo N linhas e para (carga em blocos, para medir o '
                        'disco entre um bloco e outro — ver nota sobre o disco abaixo)')
    args = p.parse_args()

    # Cada projeto do Supabase tem a SUA chave de escrita — a chave do projeto antigo
    # devolve "Invalid API key" no projeto novo (aconteceu na primeira tentativa desta
    # carga, 06/08). Por isso a chave é escolhida pelo projeto de destino.
    key = None
    if args.projeto == 'ijyxkyxovhvifrtfnqvs':          # pandora-os (base nova)
        key = ler_secret('SUPABASE_SERVICE_ROLE_KEY_PANDORA_OS')
        nome_esperado = 'SUPABASE_SERVICE_ROLE_KEY_PANDORA_OS'
    else:                                               # Alex OS (base antiga)
        key = ler_secret('SUPABASE_SERVICE_ROLE_KEY')
        nome_esperado = 'SUPABASE_SERVICE_ROLE_KEY'
    if not key:
        print(f'✗ Falta {nome_esperado} em ~/.alex-os-secrets.')
        print('  Cada projeto tem a sua chave de escrita; a de um não serve no outro.')
        sys.exit(1)

    url = (f'https://{args.projeto}.supabase.co/rest/v1/vendas_itbi'
           f'?on_conflict=chave_dedup')
    headers = {'apikey': key, 'Authorization': f'Bearer {key}',
               'Content-Type': 'application/json',
               'Prefer': 'return=minimal,resolution=ignore-duplicates'}

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    total = cur.execute('select count(*) from vendas').fetchone()[0]
    print(f'Origem : {args.db} — {total:,} registros')
    print(f'Destino: projeto {args.projeto}, tabela vendas_itbi')
    if args.comecar_em:
        print(f'Retomando a partir da linha {args.comecar_em:,}')
    print()

    cur.execute(f'select {",".join(CAMPOS)} from vendas order by id'
                + (f' limit -1 offset {args.comecar_em}' if args.comecar_em else ''))

    t0 = time.time()
    enviados = args.comecar_em
    lotes = 0
    projetou = False
    while True:
        linhas = cur.fetchmany(LOTE)
        if not linhas:
            break
        payload = [dict(zip(CAMPOS, l)) for l in linhas]
        try:
            enviar(url, headers, payload)
        except Exception as e:
            print(f'\n✗ Falhou no lote a partir de {enviados:,}: {e}')
            print(f'  Para retomar daqui:  --comecar-em {enviados}')
            print(f'  Nada se perde: a impressão digital impede repetição.')
            sys.exit(1)
        enviados += len(linhas)
        lotes += 1

        # Mede e projeta antes de deixar rodar no escuro (ADR D-7).
        if lotes == AMOSTRA and not projetou:
            projetou = True
            passado = time.time() - t0
            por_linha = passado / (lotes * LOTE)
            projecao = por_linha * (total - args.comecar_em)
            print(f'  Medição dos primeiros {lotes*LOTE:,}: {passado:.0f}s '
                  f'({por_linha*1000:.1f}s por mil linhas)')
            print(f'  Projeção para os {total-args.comecar_em:,} restantes: '
                  f'{humano(projecao)}')
            if projecao > args.limite_min * 60 and not args.seguir:
                print(f'\n⏸  PARADO: a projeção passa do limite de {args.limite_min:.0f} min.')
                print(f'   O que já subiu está lá e não se perde.')
                print(f'   Para seguir assim mesmo:  --seguir --comecar-em {enviados}')
                sys.exit(2)
            print()

        # Carga em blocos: para no limite pedido, para quem chamou medir o disco antes de
        # soltar o resto. Motivo (06/08/2026): o disco do Supabase CRESCE SOZINHO, mas com
        # cota — 4 aumentos por janela de 24h. A primeira tentativa desta carga encheu mais
        # rápido do que o disco crescia, esgotou a cota e o banco recusou escrita. Enquanto
        # a cota está esgotada não há aumento possível, nem automático nem manual.
        if args.max_linhas and (enviados - args.comecar_em) >= args.max_linhas:
            print(f'\n⏸  Bloco concluído em {enviados:,} (--max-linhas).')
            print(f'   Próximo bloco:  --comecar-em {enviados}')
            break

        if enviados % 100000 < LOTE or enviados >= total:
            passado = time.time() - t0
            feito = enviados - args.comecar_em
            resta = (passado / feito) * (total - enviados) if feito else 0
            print(f'   {enviados:,}/{total:,} ({enviados/total*100:.0f}%) — '
                  f'{humano(passado)} corridos, faltam ~{humano(resta)}', flush=True)

    conn.close()
    print(f'\n✅ {enviados:,} registros enviados em {humano(time.time()-t0)}')
    print('   Confira o total no banco antes de dar por encerrado — o número que vale')
    print('   é o que está gravado lá, não o que este programa diz ter mandado.')


if __name__ == '__main__':
    main()
