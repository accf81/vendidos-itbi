#!/usr/bin/env python3
"""
Normalização do banco ITBI SP Residencial
==========================================
Opção B — executa limpeza e normalização no ITBI_SP_residencial.db.gz

O que faz:
  1. Adiciona coluna logradouro_norm (abreviações expandidas)
  2. Normaliza cartório → "N CRI"
  3. Converte numero "99999" → "S/N"
  4. Remove vagas de garagem (complemento com VAGA/VG/GARAGEM)
  5. Remove registros com valor_m2 inválido (nulo ou < 100)
  6. Cria índices para busca rápida

Uso:
  python3 normalizar_banco.py

Saída:
  ITBI_SP_residencial.db.gz  (substitui o original — backup automático)
"""

import sqlite3, gzip, shutil, re, os, time
from datetime import datetime

# ─── Configuração ────────────────────────────────────────────────
INPUT_FILE  = 'ITBI_SP_residencial.db.gz'
BACKUP_FILE = f'ITBI_SP_residencial_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db.gz'
TMP_DB      = '/tmp/itbi_normalize.db'

# ─── Tabela de normalização de logradouros ────────────────────────
# Ordem importa: prefixos de tipo primeiro, depois títulos
NORMALIZE_MAP = [
    # Tipos de logradouro (início da string)
    (r'^R\b',    'RUA'),
    (r'^AV\b',   'AVENIDA'),
    (r'^AL\b',   'ALAMEDA'),
    (r'^PC\b',   'PRACA'),
    (r'^PCA\b',  'PRACA'),
    (r'^TV\b',   'TRAVESSA'),
    (r'^TVP\b',  'TRAVESSA'),
    (r'^EST\b',  'ESTRADA'),
    (r'^ES\b',   'ESTRADA'),
    (r'^RD\b',   'RODOVIA'),
    (r'^RV\b',   'RODOVIA'),
    (r'^VL\b',   'VILA'),
    (r'^LG\b',   'LARGO'),
    (r'^VD\b',   'VIADUTO'),
    (r'^PQ\b',   'PARQUE'),
    (r'^LD\b',   'LADEIRA'),
    (r'^PS\b',   'PASSARELA'),
    (r'^VP\b',   'VIA PARQUE'),

    # Nossa Senhora (antes dos outros para evitar conflito com S)
    (r'\bNSRA\b',  'NOSSA SENHORA'),
    (r'\bNSA\b',   'NOSSA SENHORA'),

    # Títulos honoríficos e nobiliárquicos
    (r'\bENG\b',   'ENGENHEIRO'),
    (r'\bENGA\b',  'ENGENHEIRA'),
    (r'\bDR\b',    'DOUTOR'),
    (r'\bDRA\b',   'DOUTORA'),
    (r'\bPROF\b',  'PROFESSOR'),
    (r'\bPROFA\b', 'PROFESSORA'),
    (r'\bPDE\b',   'PADRE'),
    (r'\bFRE\b',   'FREI'),
    (r'\bCEL\b',   'CORONEL'),
    (r'\bCAP\b',   'CAPITAO'),
    (r'\bTEN\b',   'TENENTE'),
    (r'\bBRIG\b',  'BRIGADEIRO'),
    (r'\bBR\b',    'BARAO'),
    (r'\bVIS\b',   'VISCONDE'),
    (r'\bCONS\b',  'CONSELHEIRO'),
    (r'\bMAL\b',   'MARECHAL'),
    (r'\bGEN\b',   'GENERAL'),
    (r'\bGOV\b',   'GOVERNADOR'),
    (r'\bPREF\b',  'PREFEITO'),
    (r'\bDEP\b',   'DEPUTADO'),
    (r'\bSEN\b',   'SENADOR'),
    (r'\bVER\b',   'VEREADOR'),
    (r'\bPRES\b',  'PRESIDENTE'),
    (r'\bMIN\b',   'MINISTRO'),
    (r'\bCOM\b',   'COMENDADOR'),
    (r'\bDES\b',   'DESEMBARGADOR'),
    (r'\bMAJ\b',   'MAJOR'),
    (r'\bDUQ\b',   'DUQUE'),
    (r'\bMARQ\b',  'MARQUES'),
    (r'\bCOND\b',  'CONDE'),
    (r'\bPRSA\b',  'PRINCESA'),

    # Santos/Santas (após NSRA para não conflitar)
    (r'\bSTA\b',   'SANTA'),
    (r'\bSTO\b',   'SANTO'),
    (r'\bSTE\b',   'SANTO'),
]

# Correções específicas: mesclagem de variantes DE/DO/DA confirmadas
# como mesma rua (verificado por bairros em comum)
SPECIFIC_CORRECTIONS = {
    "AVENIDA DOS CARINAS": "AVENIDA DAS CARINAS",
    "AVENIDA DOS MINUANOS": "AVENIDA MINUANOS",
    "AVENIDA DOUTOR SALOMAO DE VASCONCELOS": "AVENIDA DOUTOR SALOMAO VASCONCELOS",
    "AVENIDA NOSSA SENHORA DE SABARA": "AVENIDA NOSSA SENHORA DO SABARA",
    "ESTRADA DO M BOI MIRIM": "ESTRADA M BOI MIRIM",
    "RUA ALCATRAZES": "RUA DOS ALCATRAZES",
    "RUA BANDEIRANTES": "RUA DOS BANDEIRANTES",
    "RUA BARAO DE SANTA EULALIA": "RUA BARAO SANTA EULALIA",
    "RUA A BELEM": "RUA BELEM",
    "RUA CATILEIAS": "RUA DAS CATILEIAS",
    "RUA CORNETEIRO DE JESUS": "RUA CORNETEIRO JESUS",
    "RUA CORONEL MELO OLIVEIRA": "RUA CORONEL MELO DE OLIVEIRA",
    "RUA CUSTODIO NASCIMENTO": "RUA CUSTODIO DO NASCIMENTO",
    "RUA DAS FIANDEIRAS": "RUA FIANDEIRAS",
    "RUA DAS GIESTAS": "RUA GIESTAS",
    "RUA DAS IMBIRAS": "RUA IMBIRAS",
    "RUA DO HIPODROMO": "RUA HIPODROMO",
    "RUA DO MANIFESTO": "RUA MANIFESTO",
    "RUA DO ORFANATO": "RUA ORFANATO",
    "RUA DOS ALIADOS": "RUA ALIADOS",
    "RUA DOS CAETES": "RUA CAETES",
    "RUA DOS COROADOS": "RUA COROADOS",
    "RUA DOS MORAS": "RUA MORAS",
    "RUA DOS TAPES": "RUA TAPES",
    "RUA DOUTOR PLINIO AMARAL": "RUA DOUTOR PLINIO DO AMARAL",
    "RUA DA GRANJA JULIETA": "RUA GRANJA JULIETA",
    "RUA GREGORIO MATOS": "RUA GREGORIO DE MATOS",
    "RUA GUAICURI": "RUA DO GUAICURI",
    "RUA JOAO CASTELHANOS": "RUA JOAO DE CASTELHANOS",
    "RUA JOSE TAVARES DE SIQUEIRA": "RUA JOSE TAVARES SIQUEIRA",
    "RUA LEOPOLDO COUTO DE MAGALHAES JUNIOR": "RUA LEOPOLDO COUTO MAGALHAES JUNIOR",
    "RUA MARQUES OLINDA": "RUA MARQUES DE OLINDA",
    "RUA SERRA DO JAPI": "RUA SERRA DE JAPI",
    "RUA SITIANTES": "RUA DOS SITIANTES",    "RUA MINISTRO ALVARO DE SOUZA LIMA": "AVENIDA MINISTRO ALVARO DE SOUZA LIMA",}

LOWER_WORDS = {
    'DE','DO','DA','DOS','DAS',
    'E','EM','NO','NA','NOS','NAS',
    'POR','PARA','COM','SOB','SOBRE','ATE','ATÉ',
    'AO','AOS','A','PELA','PELO'
}

ABBREVS_FMT = {
    'RUA': 'Rua',
    'AVENIDA': 'Av.',
    'ALAMEDA': 'Alameda',
    'TRAVESSA': 'Travessa',
    'ESTRADA': 'Estrada',
    'RODOVIA': 'Rodovia',
    'VILA': 'Vila',
    'LARGO': 'Largo',
    'PARQUE': 'Parque',
    'VIADUTO': 'Viaduto',
    'PRAÇA': 'Praça',
    'PRACA': 'Praça',
    'VIADUTO': 'Viaduto',
    'PASSARELA': 'Passarela',
}

def clean_word(word):
    return re.sub(r'[^\wÀ-ÿ]+', '', word, flags=re.UNICODE)

def title_case_word(word, is_first=False):
    if not word:
        return word
    up = word.upper()
    clean = clean_word(up)
    if clean in ABBREVS_FMT:
        return ABBREVS_FMT[clean]
    if not is_first and clean in LOWER_WORDS:
        return clean.lower()
    return word.lower().capitalize()


def title_case_logradouro(text):
    if not text:
        return text
    text = re.sub(r'\s+', ' ', text.strip())
    words = text.split(' ')
    result = []
    for idx, word in enumerate(words):
        result.append(title_case_word(word, is_first=(idx == 0)))
    return ' '.join(result)


def sentence_case(text):
    if not text:
        return text
    t = text.lower()
    return t[0].upper() + t[1:] if len(t) > 0 else t


def normalize_logradouro(s):
    if not s:
        return s
    s = s.upper().strip()
    s = re.sub(r'\s+', ' ', s)
    # Expande prefixos primeiro (R -> RUA, AV -> AVENIDA, etc.)
    for pattern, replacement in NORMALIZE_MAP:
        s = re.sub(pattern, replacement, s)
    # Aplica correções específicas depois de expandir prefixos
    s = SPECIFIC_CORRECTIONS.get(s, s)
    return s


def normalize_cartorio(s):
    if not s:
        return s
    m = re.search(r'(\d+)', s)
    if m:
        return f"{m.group(1)} CRI"
    return s

# ─── Main ────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*55}")
    print("  NORMALIZAÇÃO DO BANCO ITBI SP RESIDENCIAL")
    print(f"{'='*55}\n")

    # 1. Backup
    print(f"1. Fazendo backup → {BACKUP_FILE}")
    shutil.copy2(INPUT_FILE, BACKUP_FILE)
    print(f"   ✓ Backup salvo ({os.path.getsize(BACKUP_FILE)/1024/1024:.1f} MB)")

    # 2. Descomprimir
    print(f"\n2. Descomprimindo banco...")
    t0 = time.time()
    with gzip.open(INPUT_FILE, 'rb') as f:
        data = f.read()
    with open(TMP_DB, 'wb') as f:
        f.write(data)
    print(f"   ✓ {len(data)/1024/1024:.1f} MB descomprimidos em {time.time()-t0:.1f}s")

    conn = sqlite3.connect(TMP_DB)
    cur = conn.cursor()

    # Contagem inicial
    cur.execute("SELECT COUNT(*) FROM vendas")
    total_inicial = cur.fetchone()[0]
    print(f"\n   Registros iniciais: {total_inicial:,}")

    # 3. Remover vagas de garagem PURAS (não remove apartamentos que incluem vaga)
    # Vagas puras: complemento COMEÇA com VG, VAGA, GARAGEM, BOX
    # Apartamento+vaga (manter): "AP 22 E VG", "A 869 AP 81 VG" — não começam com esses prefixos
    print(f"\n3. Removendo vagas de garagem puras...")
    cur.execute("""
        DELETE FROM vendas
        WHERE UPPER(COALESCE(complemento,'')) LIKE 'VG%'
           OR UPPER(COALESCE(complemento,'')) LIKE 'VAGA%'
           OR UPPER(COALESCE(complemento,'')) LIKE 'GARAGEM%'
           OR UPPER(COALESCE(complemento,'')) LIKE 'BOX%'
    """)
    removidos_vagas = cur.rowcount
    print(f"   ✓ {removidos_vagas:,} vagas/garagens removidas")

    # 4. Remover valores inválidos
    print(f"\n4. Removendo registros com valor inválido...")
    cur.execute("DELETE FROM vendas WHERE valor_m2 IS NULL OR valor_m2 < 100")
    removidos_valor = cur.rowcount
    print(f"   ✓ {removidos_valor:,} registros com valor_m2 < R$100 removidos")

    # Contagem após limpeza
    cur.execute("SELECT COUNT(*) FROM vendas")
    total_apos_limpeza = cur.fetchone()[0]
    print(f"\n   Registros após limpeza: {total_apos_limpeza:,}")

    # 5. Adicionar colunas de logradouro
    print(f"\n5. Adicionando colunas logradouro_norm e logradouro_fmt...")
    try:
        cur.execute("ALTER TABLE vendas ADD COLUMN logradouro_norm TEXT")
        print("   ✓ Coluna logradouro_norm criada")
    except sqlite3.OperationalError:
        print("   ℹ Coluna logradouro_norm já existe, atualizando...")
    try:
        cur.execute("ALTER TABLE vendas ADD COLUMN logradouro_fmt TEXT")
        print("   ✓ Coluna logradouro_fmt criada")
    except sqlite3.OperationalError:
        print("   ℹ Coluna logradouro_fmt já existe, atualizando...")

    # 6. Normalizar logradouros (em lotes para mostrar progresso)
    print(f"\n6. Normalizando logradouros...")
    cur.execute("SELECT rowid, logradouro FROM vendas")
    rows = cur.fetchall()
    batch = []
    for i, (rowid, logradouro) in enumerate(rows):
        norm = normalize_logradouro(logradouro)
        # gerar em Title Case (cada palavra importante com inicial maiúscula)
        fmt = title_case_logradouro(norm)
        batch.append((norm, fmt, rowid))
        if len(batch) >= 10000:
            cur.executemany("UPDATE vendas SET logradouro_norm=?, logradouro_fmt=? WHERE rowid=?", batch)
            batch = []
            print(f"   ... {i+1:,}/{len(rows):,} ({(i+1)/len(rows)*100:.0f}%)", end='\r')
    if batch:
        cur.executemany("UPDATE vendas SET logradouro_norm=?, logradouro_fmt=? WHERE rowid=?", batch)
    print(f"   ✓ {len(rows):,} logradouros normalizados                    ")

    # Verificar resultado
    cur.execute("""
        SELECT logradouro, logradouro_norm, COUNT(*) as n
        FROM vendas
        WHERE logradouro != logradouro_norm
        GROUP BY logradouro_norm
        ORDER BY n DESC
        LIMIT 5
    """)
    print("   Exemplos de normalizações:")
    for r in cur.fetchall():
        print(f"     '{r[0]}' → '{r[1]}' ({r[2]:,}x)")

    # 7. Normalizar cartório
    print(f"\n7. Normalizando cartório...")
    cur.execute("SELECT DISTINCT cartorio FROM vendas WHERE cartorio IS NOT NULL")
    cartorios = cur.fetchall()
    for (cartorio,) in cartorios:
        normalizado = normalize_cartorio(cartorio)
        cur.execute("UPDATE vendas SET cartorio=? WHERE cartorio=?", (normalizado, cartorio))
    conn.commit()
    cur.execute("SELECT DISTINCT cartorio FROM vendas ORDER BY cartorio LIMIT 10")
    print("   Exemplos de cartórios normalizados:")
    for r in cur.fetchall():
        print(f"     '{r[0]}'")

    # 8. Normalizar número 99999 → S/N
    print(f"\n8. Convertendo numero '99999' → 'S/N'...")
    cur.execute("UPDATE vendas SET numero='S/N' WHERE numero='99999'")
    print(f"   ✓ {cur.rowcount:,} registros atualizados")

    # 9. Criar índices
    print(f"\n9. Criando índices...")
    indices = [
        ("idx_logradouro_norm", "logradouro_norm"),
        ("idx_referencia",      "referencia"),
        ("idx_ano",             "ano"),
        ("idx_bairro",          "bairro"),
    ]
    for nome, coluna in indices:
        try:
            cur.execute(f"CREATE INDEX IF NOT EXISTS {nome} ON vendas({coluna})")
            print(f"   ✓ Índice {nome}")
        except Exception as e:
            print(f"   ⚠ {nome}: {e}")

    conn.commit()

    # Estatísticas finais
    cur.execute("SELECT COUNT(*) FROM vendas")
    total_final = cur.fetchone()[0]
    print(f"\n{'─'*40}")
    print(f"  Registros iniciais:  {total_inicial:,}")
    print(f"  Vagas removidas:     {removidos_vagas:,}")
    print(f"  Valores inválidos:   {removidos_valor:,}")
    print(f"  Registros finais:    {total_final:,}")
    print(f"  Removidos no total:  {total_inicial - total_final:,} ({(total_inicial-total_final)/total_inicial*100:.1f}%)")
    print(f"{'─'*40}\n")

    conn.close()

    # 10. Recomprimir
    print(f"10. Recomprimindo banco...")
    t0 = time.time()
    with open(TMP_DB, 'rb') as f_in:
        with gzip.open(INPUT_FILE, 'wb', compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
    size_mb = os.path.getsize(INPUT_FILE)/1024/1024
    print(f"    ✓ Salvo em {time.time()-t0:.1f}s — {size_mb:.1f} MB")

    # Limpeza
    os.remove(TMP_DB)

    print(f"\n✅ CONCLUÍDO!")
    print(f"   Arquivo atualizado: {INPUT_FILE}")
    print(f"   Backup mantido em:  {BACKUP_FILE}")
    print(f"\n   Próximo passo: git add + git push para publicar no GitHub Pages")
    print(f"   (duplo clique em deploy_github.command)\n")

if __name__ == '__main__':
    main()
