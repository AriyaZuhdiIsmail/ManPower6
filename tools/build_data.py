#!/usr/bin/env python3
"""Build the website preload data from the supplied current SOTK master.

Usage:
  python3 build_data.py <SOTK_MASTER.xlsx> <data.js> [DATA_SOTK_CABANG_FORMASI.xlsx]

The source workbook is read-only. Existing SOTK columns and rows are preserved;
POSITION is derived as an additional display column. Both position-tier rule
sheets are emitted to data.js so the runtime can use the same source of truth.
"""
import sys, json, datetime, re
import pandas as pd

if len(sys.argv) < 3:
    raise SystemExit(__doc__)
SRC = sys.argv[1]
OUT = sys.argv[2]
FORMASI_SRC = sys.argv[3] if len(sys.argv) > 3 else None

SHEETS = [
    'SOTK_WILAYAH', 'SOTK_AREA', 'SOTK_CABANG', 'CORPORATE_TITLE',
    'UNIT_MASTER_CABANG', 'WEB_FILTER_MASTER', 'POSITION_GRADE_RULES',
    'POSITION_GRADE_TIER_MAP'
]
CODE_COLS = {'ORG CODE', 'UNIT_KEY', 'BRANCH_KEY', 'FORMASI_KEY', 'JOB CODE'}
# Rule documentation columns are useful in the Excel source, but are not used as
# runtime fields by the legacy matcher. The canonical runtime map is emitted in
# POSITION_GRADE_TIER_MAP instead.
DROP_COLS = {'SOTK_CABANG': {
    'CURRENT_JOB_CODE_FIELD', 'DEFINITIVE_JOB_CODE_FIELD', 'CURRENT_POSITION_FIELD',
    'DEFINITIVE_POSITION_FIELD', 'CURRENT_JOB_GRADE_FIELD', 'DEFINITIVE_JOB_GRADE_FIELD',
    'MATCH_PRIORITY_RULE'
}}

REQUIRED = {
    'SOTK_WILAYAH': ['ORG CODE', 'BRANCH NAME', 'ORG NAME', 'JOB CODE', 'JOB NAME', 'FORMASI', 'FORMASI_KEY'],
    'SOTK_AREA': ['ORG CODE', 'NAMA UNIT KERJA', 'ORG NAME', 'KLASIFIKASI AREA', 'JOB CODE', 'JOB NAME', 'FORMASI', 'FORMASI_KEY'],
    'SOTK_CABANG': ['ORG CODE', 'NAMA UNIT KERJA', 'OFFICE TYPE', 'KELAS CABANG', 'KELAS UPC/UPS', 'JOB CODE', 'JOB NAME', 'JOB GRADE', 'FORMASI', 'UNIT_KEY', 'BRANCH_KEY', 'FORMASI_KEY'],
    'CORPORATE_TITLE': ['CORPORATE_BAND', 'CORPORATE_TITLE', 'JOB_GRADE_MIN', 'JOB_GRADE_MAX'],
    'UNIT_MASTER_CABANG': ['UNIT_KEY', 'UNIT_NAME', 'KANTOR_AREA', 'BRANCH_NAME', 'UNIT_TYPE', 'CLUSTER_TYPE', 'KELAS_UNIT', 'BRANCH_KEY', 'KELAS UPC/UPS'],
    'POSITION_GRADE_RULES': ['SOTK_JOB_KEY', 'NAMA_JABATAN_MASTER', 'POSITION_NAME_PREFIX_MATCH', 'FALLBACK_JOB_GRADE'],
    'POSITION_GRADE_TIER_MAP': ['SOTK_JOB_KEY', 'NAMA_JABATAN_MASTER', 'POSITION_NAME_PREFIX', 'JENIS_PENCOCOKAN', 'TINGKAT_HASIL', 'JOB_GRADE_PASANGAN', 'URUTAN_PRIORITAS'],
    'WEB_FILTER_MASTER': ['LEVEL', 'FILTER_1', 'INTERNAL_KEY_1', 'MATCH_RULE'],
}


def norm_key(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ''
    if isinstance(v, (int, float)) and float(v).is_integer():
        return str(int(v))
    return str(v).strip()

def norm_text(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ''
    return str(v).strip()


def validate_master(data):
    errors, warnings = [], []
    for name, required in REQUIRED.items():
        if name not in data:
            errors.append(f'Sheet wajib tidak ditemukan: {name}')
            continue
        missing = [c for c in required if c not in data[name].columns]
        if missing:
            errors.append(f'{name}: kolom wajib hilang: {", ".join(missing)}')
        if data[name].empty:
            errors.append(f'{name}: tidak memiliki baris data')

    if errors:
        raise SystemExit('Validasi SOTK gagal:\n- ' + '\n- '.join(errors))

    # Formasi keys must be unique and formasi must be numeric/non-negative.
    for name in ('SOTK_WILAYAH', 'SOTK_AREA', 'SOTK_CABANG'):
        df = data[name]
        key_col = 'FORMASI_KEY'
        keys = df[key_col].map(norm_key)
        dup = keys[keys.ne('') & keys.duplicated()].unique().tolist()
        if dup:
            errors.append(f'{name}: FORMASI_KEY duplikat: {dup[:8]}')
        vals = pd.to_numeric(df['FORMASI'], errors='coerce')
        if vals.isna().any():
            errors.append(f'{name}: terdapat FORMASI kosong/non-numerik ({int(vals.isna().sum())} baris)')
        elif (vals < 0).any():
            errors.append(f'{name}: terdapat FORMASI negatif')

    um = data['UNIT_MASTER_CABANG'].copy()
    um['__UNIT_KEY'] = um['UNIT_KEY'].map(norm_key)
    dup_units = um.loc[um['__UNIT_KEY'].duplicated(keep=False), '__UNIT_KEY'].unique().tolist()
    if dup_units:
        errors.append(f'UNIT_MASTER_CABANG: UNIT_KEY duplikat: {dup_units[:8]}')
    um_map = {r['__UNIT_KEY']: r for _, r in um.iterrows() if r['__UNIT_KEY']}

    # Every outlet-level SOTK row must resolve to one canonical Unit Master record.
    cab = data['SOTK_CABANG'].copy()
    cab['__UNIT_KEY'] = cab['UNIT_KEY'].map(norm_key)
    missing_units = sorted(set(cab['__UNIT_KEY']) - set(um_map))
    if missing_units:
        errors.append(f'SOTK_CABANG: {len(missing_units)} UNIT_KEY tidak ada di UNIT_MASTER_CABANG: {missing_units[:12]}')

    invalid_cabang_class = cab.loc[~cab['KELAS CABANG'].astype(str).str.strip().isin(['A', 'B']), 'ORG CODE'].astype(str).tolist()
    if invalid_cabang_class:
        errors.append(f'SOTK_CABANG: KELAS CABANG kosong/tidak valid pada kode outlet: {invalid_cabang_class[:12]}')

    valid_upc = {'U1', 'U2', 'U3', 'U4'}
    for _, row in cab.iterrows():
        unit_key = norm_key(row['UNIT_KEY'])
        unit = um_map.get(unit_key)
        if unit is None:
            continue
        unit_type = norm_text(unit['UNIT_TYPE']).upper()
        row_type = norm_text(row['OFFICE TYPE']).upper()
        row_class = norm_text(row['KELAS CABANG'])
        unit_class = norm_text(unit['KELAS_UNIT'])
        row_upc = norm_text(row['KELAS UPC/UPS']).upper()
        unit_upc = norm_text(unit['KELAS UPC/UPS']).upper()
        if row_class != unit_class:
            errors.append(f"Kelas A/B tidak konsisten pada outlet {unit_key}: SOTK={row_class}, Unit Master={unit_class}")
            break
        if row_type == 'UPC/UPS' or unit_type == 'UPC/UPS':
            if row_type != 'UPC/UPS' or unit_type != 'UPC/UPS':
                errors.append(f"Jenis outlet tidak konsisten pada outlet {unit_key}: SOTK={row_type}, Unit Master={unit_type}")
                break
            if row_upc not in valid_upc or unit_upc not in valid_upc:
                errors.append(f"Kelas UPC/UPS tidak valid pada outlet {unit_key}: SOTK={row_upc}, Unit Master={unit_upc}")
                break
            if row_upc != unit_upc:
                errors.append(f"Kelas UPC/UPS berbeda pada outlet {unit_key}: SOTK={row_upc}, Unit Master={unit_upc}")
                break
        elif row_upc or unit_upc:
            errors.append(f"Outlet non-UPC/UPS {unit_key} tidak boleh memiliki KELAS UPC/UPS (SOTK={row_upc}, Unit Master={unit_upc})")
            break

    # Branch parent linkage must point to a canonical master outlet.
    invalid_parents = sorted({norm_key(x) for x in cab['BRANCH_KEY'] if norm_key(x) and norm_key(x) not in um_map})
    if invalid_parents:
        errors.append(f'SOTK_CABANG: BRANCH_KEY tidak ditemukan di UNIT_MASTER_CABANG: {invalid_parents[:12]}')

    if errors:
        raise SystemExit('Validasi SOTK gagal:\n- ' + '\n- '.join(errors))

    print('Validasi SOTK: LULUS')
    print('  Formasi cabang:', len(cab), 'baris |', int(pd.to_numeric(cab['FORMASI']).sum()), 'kebutuhan')
    print('  Outlet master:', len(um_map), '| UPC/UPS:', int((um['UNIT_TYPE'].astype(str).str.upper() == 'UPC/UPS').sum()))
    print('  Kelas UPC/UPS:', um.loc[um['UNIT_TYPE'].astype(str).str.upper() == 'UPC/UPS', 'KELAS UPC/UPS'].value_counts().to_dict())
    if warnings:
        for w in warnings:
            print('PERINGATAN:', w)


def validate_formasi_reference(master_cabang, reference_path):
    """Optional row-by-outlet validation against the initial FORMASI_SOTK workbook."""
    ref = pd.read_excel(reference_path, sheet_name=0, header=1, dtype=object).dropna(how='all')
    ref.columns = [str(c).strip() for c in ref.columns]
    code_col = find_col(ref, ['KODE OUTLET', 'KODE', 'ORG CODE'])
    if not code_col:
        print('Peringatan: kolom kode outlet tidak ditemukan pada file referensi; pembandingan dilewati.')
        return
    role_map = {
        'Manager Bisnis': 'MBI', 'Pimpinan Cabang': 'PNC', 'Pengelola Agunan': 'PAGN',
        'Kasir': 'KSR', 'Penaksir': 'PSR', 'Asisten Manager Non Gadai': 'AMNG',
        'Account Officer': 'AO', 'Senior Account Officer': 'SAO', 'Kepala UPC': 'KUPC',
        'Pengelola Unit Co-Lo': 'PCOL', 'Mobile Appraiser': 'MAP'
    }
    actual = {}
    for _, r in master_cabang.iterrows():
        k = norm_key(r['ORG CODE']), str(r['JOB CODE']).strip()
        actual[k] = actual.get(k, 0) + float(r['FORMASI'])
    diffs = []
    ref_outlets = set()
    for _, r in ref.iterrows():
        outlet = norm_key(r.get(code_col))
        if not outlet:
            continue
        ref_outlets.add(outlet)
        for col, job in role_map.items():
            if col not in ref.columns:
                continue
            try:
                expected = float(r.get(col) or 0)
            except (TypeError, ValueError):
                expected = 0
            got = actual.get((outlet, job), 0)
            if expected != got:
                diffs.append((outlet, col, expected, got))
    master_outlets = set(master_cabang['ORG CODE'].map(norm_key))
    if diffs or ref_outlets != master_outlets:
        print('Validasi referensi formasi: GAGAL')
        if diffs:
            print('  Selisih contoh:', diffs[:12], '| total selisih:', len(diffs))
        if ref_outlets != master_outlets:
            print('  Outlet hanya di referensi:', sorted(ref_outlets - master_outlets)[:12])
            print('  Outlet hanya di master:', sorted(master_outlets - ref_outlets)[:12])
        raise SystemExit('Master tidak cocok dengan referensi formasi cabang.')
    print('Validasi referensi formasi: LULUS |', len(ref_outlets), 'outlet | tidak ada selisih outlet/jabatan')


def clean(v, col=None):
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return None
    if isinstance(v, (datetime.datetime, pd.Timestamp)):
        return v.strftime('%Y-%m-%d')
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if col in CODE_COLS and not isinstance(v, str):
        v = str(int(v)) if isinstance(v, (int, float)) else str(v)
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    # Convert numpy scalar types to native Python types for JSON serialization.
    if hasattr(v, 'item'):
        try:
            return v.item()
        except Exception:
            pass
    return v


def read(name):
    df = pd.read_excel(SRC, sheet_name=name, dtype=object)
    df = df.dropna(how='all')
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_col(df, candidates):
    """Return the first existing header from candidates, case-insensitively."""
    lut = {str(c).strip().upper(): c for c in df.columns}
    for c in candidates:
        if c.strip().upper() in lut:
            return lut[c.strip().upper()]
    return None


def to_grade(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    m = re.search(r'\d+', str(v))
    return int(m.group(0)) if m else None


TIERED = {'AMNG', 'PSR', 'SAO', 'AO', 'PAGN'}


def tier_text(rules, key):
    key_col = find_col(rules, ['SOTK_JOB_KEY'])
    name_col = find_col(rules, ['POSITION_NAME_PREFIX_MATCH', 'POSITION NAME / LEVEL', 'POSITION_NAME_PREFIX'])
    grade_col = find_col(rules, ['FALLBACK_JOB_GRADE', 'JOB GRADE TARGET', 'JOB_GRADE_PASANGAN'])
    if not key_col or not name_col:
        return ''
    items, seen = [], set()
    for _, r in rules[rules[key_col].astype(str).str.strip() == key].iterrows():
        nm = str(r.get(name_col) or '').strip()
        if not nm or nm.lower() in ('nan', 'none') or 'fallback lama' in nm.lower():
            continue
        grade = to_grade(r.get(grade_col)) if grade_col else None
        item = f'{nm} (JG {grade})' if grade is not None else nm
        if item not in seen:
            seen.add(item); items.append(item)
    return ' · '.join(items)


def position_cabang(row, rules_text):
    job = str(row.get('JOB CODE') or '').strip()
    jn = str(row.get('JOB NAME ', row.get('JOB NAME', '')) or '').strip()
    kelas = str(row.get('KELAS CABANG') or '').strip()
    if job in TIERED:
        return rules_text.get(job) or jn
    if job == 'PNC' and kelas in ('A', 'B'):
        return f'{jn} {kelas}'
    if job == 'MBI' and kelas in ('A', 'B'):
        return f'{jn} {kelas}'
    if job == 'KUPC' and kelas in ('A', 'B'):
        unit = str(row.get('NAMA UNIT KERJA') or '').upper()
        kind = 'UPS' if unit.startswith(('UPS', 'UPKS')) else 'UPC'
        return f'Kepala {kind} {kelas}'
    return jn


def read_validation_changes():
    try:
        val = pd.read_excel(SRC, sheet_name='VALIDASI_REVISI', header=None, dtype=object).dropna(how='all')
    except Exception:
        return []
    changes = []
    for _, r in val.iterrows():
        p, v, k = r.get(0), r.get(1), r.get(2)
        if isinstance(p, str) and isinstance(k, str) and p.strip().upper() not in ('ITEM', 'PARAMETER', 'VALIDASI REVISI MASTER SOTK'):
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                changes.append({'org': '', 'kind': str(p).strip(), 'text': str(k).strip()})
    return changes


def main():
    data = {n: read(n) for n in SHEETS}
    validate_master(data)
    if FORMASI_SRC:
        validate_formasi_reference(data['SOTK_CABANG'], FORMASI_SRC)
    rules = data['POSITION_GRADE_RULES']
    rules_text = {k: tier_text(rules, k) for k in TIERED}

    # Additional display metadata only: source SOTK_WILAYAH/SOTK_AREA fields
    # are copied unchanged and POSITION mirrors their existing JOB NAME.
    w = data['SOTK_WILAYAH']
    a = data['SOTK_AREA']
    c = data['SOTK_CABANG']
    w['POSITION'] = w['JOB NAME']
    a['POSITION'] = a['JOB NAME']
    c['POSITION'] = c.apply(lambda r: position_cabang(r, rules_text), axis=1)

    pre = {}
    for n, df in data.items():
        df = df.drop(columns=[x for x in DROP_COLS.get(n, ()) if x in df.columns])
        pre[n + '_H'] = list(df.columns)
        pre[n] = [[clean(v, col) for col, v in zip(df.columns, row)] for row in df.itertuples(index=False, name=None)]

    # Metadata is informational only and reflects the actual source filename.
    changes = read_validation_changes()
    pre['SOTK_META'] = {
        'version': 'SOTK 2026 — master terbaru dengan Position Name dan peta tingkat jabatan',
        'source': SRC.replace('\\', '/').split('/')[-1],
        'generated': datetime.date.today().isoformat(),
        'changes': changes + [{
            'org': '', 'kind': 'Kolom POSITION',
            'text': 'POSITION ditambahkan sebagai metadata display; isi formasi Kantor Wilayah dan Kantor Area dipertahankan.'
        }, {
            'org': '', 'kind': 'Peta tingkat jabatan',
            'text': 'POSITION_GRADE_RULES dan POSITION_GRADE_TIER_MAP dimuat ke aplikasi untuk deteksi Position Name dan validasi grade.'
        }]
    }

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('window.SOTK_PRELOAD=' + json.dumps(pre, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + ';\n')

    forms_idx = pre['SOTK_CABANG_H'].index('FORMASI')
    total_formasi = sum((r[forms_idx] or 0) for r in pre['SOTK_CABANG'])
    um_headers = pre['UNIT_MASTER_CABANG_H']
    um_key_idx = um_headers.index('UNIT_KEY')
    outlets = {r[um_key_idx] for r in pre['UNIT_MASTER_CABANG'] if r[um_key_idx] not in (None, '')}
    print('Baris:', {n: len(pre[n]) for n in SHEETS})
    print('Total formasi SOTK_CABANG:', total_formasi, '| outlet master:', len(outlets))
    print('POSITION_GRADE_TIER_MAP rows:', len(pre['POSITION_GRADE_TIER_MAP']))
    print('Contoh POSITION Cabang:')
    headers = pre['SOTK_CABANG_H']
    pos_idx = headers.index('POSITION')
    job_idx = headers.index('JOB CODE')
    for j in ['PSR', 'AMNG', 'SAO', 'AO', 'PAGN']:
        row = next((r for r in pre['SOTK_CABANG'] if r[job_idx] == j), None)
        print(' ', j, '->', row[pos_idx] if row else '(tidak ditemukan)')

if __name__ == '__main__':
    main()
