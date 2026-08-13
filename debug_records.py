from services.sheets_service import _get_ws, get_config, COLUNAS_ESTOQUE
ws=_get_ws(get_config().aba_estoque)
all_rows=ws.get_all_values()
headers=all_rows[0]
import re

def _tokens(s):
    if s is None:
        return set()
    return set(re.findall(r'[a-z0-9]+', str(s).lower()))

col_map={}
for idx,h in enumerate(headers):
    h_toks=_tokens(h)
    if 'p' in h_toks and 'para' not in h_toks:
        h_toks=h_toks|{'para'}
    for canon in COLUNAS_ESTOQUE:
        c_toks=_tokens(canon)
        stop={'de','da','do','dos','das','o','a','e'}
        if c_toks - stop <= h_toks:
            col_map[idx]=canon
            break

records=[]
for row in all_rows[1:]:
    if not any(str(c).strip()!='' for c in row):
        continue
    rec={}
    for idx,canon in col_map.items():
        rec[canon]=row[idx] if idx < len(row) else ''
    records.append(rec)

print('col_map', col_map)
print('records sample', records[:5])
print('len records', len(records))
