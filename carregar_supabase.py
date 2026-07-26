#!/usr/bin/env python3
"""
Carga completa de um banco SQLite do ITBI para uma tabela do Supabase.
=====================================================================
Usado na troca do banco reconstruído (25-26/07/2026) e reaproveitável em qualquer
recarga futura — inclusive na REVERSÃO: basta apontar pro .db do backup.

Uso:
  python3 carregar_supabase.py <arquivo.db> <nome_da_tabela> [--limpar]

  --limpar  apaga tudo o que já está na tabela antes de carregar (recarga do zero)

Precisa da SUPABASE_SERVICE_ROLE_KEY em ~/.alex-os-secrets (chave de escrita —
a chave pública do site só lê). Nunca colar chave no código: este arquivo vai pro
repositório público accf81/vendidos-itbi.
"""
import sqlite3, sys, os, json, time, urllib.request, urllib.error

PROJETO = 'sobmjqounukzbplrmhkr'
LOTE = 2000

CAMPOS = ['sql', 'data_transacao', 'logradouro', 'numero', 'complemento', 'bairro',
          'referencia', 'area_construida_m2', 'valor_transacao', 'valor_m2',
          'cartorio', 'matricula', 'ano', 'logradouro_norm', 'logradouro_fmt',
          'proporcao_transmitida']


def ler_secret(nome):
    caminho = os.path.expanduser('~/.alex-os-secrets')
    if not os.path.exists(caminho):
        return None
    with open(caminho) as f:
        for linha in f:
            if linha.strip().startswith(f'{nome}='):
                return linha.strip().split('=', 1)[1]
    return None


def enviar(url, headers, dados, metodo='POST', tentativas=4):
    """Envia um lote, com nova tentativa em caso de falha de rede/limite temporário."""
    corpo = json.dumps(dados).encode('utf-8') if dados is not None else None
    for t in range(tentativas):
        req = urllib.request.Request(url, data=corpo, method=metodo, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp.read()
            return
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode()[:300]
            if e.code < 500 or t == tentativas - 1:
                raise RuntimeError(f"HTTP {e.code}: {detalhe}")
        except Exception as e:
            if t == tentativas - 1:
                raise
        time.sleep(3 * (t + 1))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    db_path, tabela = sys.argv[1], sys.argv[2]
    limpar = '--limpar' in sys.argv

    key = ler_secret('SUPABASE_SERVICE_ROLE_KEY')
    if not key:
        print("✗ Falta SUPABASE_SERVICE_ROLE_KEY em ~/.alex-os-secrets.")
        sys.exit(1)

    url = f'https://{PROJETO}.supabase.co/rest/v1/{tabela}'
    headers = {'apikey': key, 'Authorization': f'Bearer {key}',
               'Content-Type': 'application/json', 'Prefer': 'return=minimal'}

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("select count(*) from vendas")
    total = cur.fetchone()[0]
    print(f"Origem: {db_path} — {total:,} registros")
    print(f"Destino: tabela {tabela}\n")

    if limpar:
        print("Limpando a tabela de destino...")
        enviar(url + '?id=gt.0', headers, None, metodo='DELETE')
        print("   ✓ limpa\n")

    cur.execute(f"select {','.join(CAMPOS)} from vendas")
    t0 = time.time()
    enviados = 0
    while True:
        linhas = cur.fetchmany(LOTE)
        if not linhas:
            break
        payload = [dict(zip(CAMPOS, l)) for l in linhas]
        try:
            enviar(url, headers, payload)
        except Exception as e:
            print(f"\n✗ Falhou no lote a partir de {enviados:,}: {e}")
            print("  Nada além deste ponto foi enviado. Dá pra recomeçar do zero com --limpar.")
            sys.exit(1)
        enviados += len(linhas)
        if enviados % 50000 == 0 or enviados == total:
            pct = enviados / total * 100
            print(f"   {enviados:,}/{total:,} ({pct:.0f}%) — {time.time()-t0:.0f}s", flush=True)
    conn.close()
    print(f"\n✅ {enviados:,} registros carregados em {time.time()-t0:.0f}s")


if __name__ == '__main__':
    main()
