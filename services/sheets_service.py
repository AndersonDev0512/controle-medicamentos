from __future__ import annotations
import pandas as pd
import streamlit as st
from typing import Any
from utils.config import get_config
from utils.constants import COLUNAS_ESTOQUE, COLUNAS_REGISTRO, COLUNAS_HISTORICO
from utils.helpers import sanitize_service_account
import traceback
import re

# Lazily import gspread; provide friendly messages when unavailable
try:
    import gspread
    from google.oauth2.service_account import Credentials
    from gspread.exceptions import APIError, SpreadsheetNotFound
    _GSPREAD_AVAILABLE = True
except Exception:
    _GSPREAD_AVAILABLE = False

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _missing_dependency_msg() -> None:
    st.error(
        "Biblioteca `gspread` (ou dependências Google) não encontrada.\n"
        "Instale via: `pip install -r requirements.txt` e reinicie a aplicação."
    )


if _GSPREAD_AVAILABLE:
    @st.cache_resource
    def _get_client() -> gspread.Client:
        try:
            import os
            raw = None

            # 1) Try Streamlit secrets first (preferred on Streamlit Cloud)
            try:
                raw = st.secrets.get("gcp_service_account") if hasattr(st, 'secrets') else None
            except Exception:
                raw = None

            # 2) Try environment variables (useful for CI / deployment platforms)
            if not raw:
                raw = os.environ.get('GCP_SERVICE_ACCOUNT') or os.environ.get('GCP_SERVICE_ACCOUNT_JSON')

            # 3) Try GOOGLE_APPLICATION_CREDENTIALS path
            if not raw:
                gac_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
                if gac_path and os.path.exists(gac_path):
                    try:
                        with open(gac_path, 'r', encoding='utf-8') as f:
                            raw = f.read()
                    except Exception:
                        raw = None

            # 4) Fallback: try to read local .streamlit/secrets.toml (developer convenience)
            if not raw:
                try:
                    try:
                        import tomllib as toml
                    except Exception:
                        import toml
                    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    secrets_path = os.path.join(repo_root, '.streamlit', 'secrets.toml')
                    if os.path.exists(secrets_path):
                        with open(secrets_path, 'rb') as f:
                            data = toml.load(f)
                        raw = data.get('gcp_service_account')
                except Exception:
                    raw = None

            if not raw:
                st.error('gcp_service_account não encontrado. Configure o secret `gcp_service_account` no Streamlit Cloud, ou defina a variável de ambiente `GCP_SERVICE_ACCOUNT`/`GCP_SERVICE_ACCOUNT_JSON`, ou `GOOGLE_APPLICATION_CREDENTIALS` apontando para o arquivo JSON.')
                raise RuntimeError('gcp_service_account não encontrado em st.secrets, variáveis de ambiente ou .streamlit/secrets.toml')

            info = sanitize_service_account(raw)
            creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
            return gspread.authorize(creds)
        except Exception:
            st.error('Erro ao carregar credenciais da Service Account.')
            st.error(traceback.format_exc())
            raise


    @st.cache_resource
    def _get_spreadsheet() -> gspread.Spreadsheet:
        config = get_config()
        sid = config.spreadsheet_id
        client = _get_client()
        if not sid:
            st.error('SPREADSHEET_ID não configurado em .streamlit/secrets.toml')
            raise RuntimeError('SPREADSHEET_ID não configurado')

        # If user passed a URL, extract the key
        m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", str(sid))
        key = m.group(1) if m else sid

        try:
            try:
                return client.open_by_key(key)
            except Exception:
                return client.open(sid)  # try by title
        except SpreadsheetNotFound:
            raw = st.secrets.get('gcp_service_account') if hasattr(st, 'secrets') else None
            info = sanitize_service_account(raw) if raw else None
            email = info.get('client_email') if info else None
            msg = 'Planilha não encontrada.'
            if email:
                msg += f' Compartilhe a planilha com a conta de serviço: {email}.'
            st.error(msg)
            raise
        except PermissionError:
            st.error('Permissão negada ao acessar a planilha. Verifique compartilhamento.')
            raise
        except APIError:
            st.error('Erro na API do Google Sheets.')
            raise


    def _get_ws(aba: str) -> gspread.Worksheet:
        return _get_spreadsheet().worksheet(aba)


    def _ensure_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        for c in cols:
            if c not in df.columns:
                df[c] = ''
        return df[cols]


    def _row(d: dict[str, Any], cols: list[str]) -> list[Any]:
        return [d.get(c, '') for c in cols]


    # READ
    @st.cache_data(ttl=30)
    def ler_estoque() -> pd.DataFrame:
        config = get_config()
        try:
            ws = _get_ws(config.aba_estoque)
            all_rows = ws.get_all_values()
            if not all_rows or len(all_rows) < 1:
                return pd.DataFrame(columns=COLUNAS_ESTOQUE)

            headers = all_rows[0]

            def _tokens(s: str) -> set[str]:
                if s is None:
                    return set()
                return set(re.findall(r"[a-z0-9]+", str(s).lower()))

            col_map: dict[int, str] = {}
            for idx, h in enumerate(headers):
                h_toks = _tokens(h)
                if 'p' in h_toks and 'para' not in h_toks:
                    h_toks = h_toks | {'para'}
                for canon in COLUNAS_ESTOQUE:
                    c_toks = _tokens(canon)
                    stop = {'de', 'da', 'do', 'dos', 'das', 'o', 'a', 'e'}
                    if c_toks - stop <= h_toks:
                        col_map[idx] = canon
                        break

            data_rows = all_rows[1:]
            records: list[dict[str, Any]] = []
            sheet_rows: list[int] = []
            for i, row in enumerate(data_rows):
                if not any(str(cell).strip() != '' for cell in row):
                    continue
                rec: dict[str, Any] = {}
                for idx, canon in col_map.items():
                    rec[canon] = row[idx] if idx < len(row) else ''
                records.append(rec)
                sheet_rows.append(i + 2)  # i+1 for 1-based + 1 for header row

            if not records:
                return pd.DataFrame(columns=COLUNAS_ESTOQUE)

            df = pd.DataFrame(records)
            df = _ensure_cols(df, COLUNAS_ESTOQUE)
            df['_sheet_row'] = sheet_rows
            return df
        except Exception:
            st.error('Erro ao ler estoque')
            st.error(traceback.format_exc())
            return pd.DataFrame(columns=COLUNAS_ESTOQUE)


    @st.cache_data(ttl=30)
    def ler_materiais() -> pd.DataFrame:
        config = get_config()
        try:
            ws = _get_ws(config.aba_materiais)
            all_rows = ws.get_all_values()
            if not all_rows or len(all_rows) < 2:
                return pd.DataFrame(columns=COLUNAS_ESTOQUE)
            headers = all_rows[0]
            data_rows = all_rows[1:]
            records = []
            for row in data_rows:
                if not any(str(c).strip() for c in row):
                    continue
                records.append({h: (row[i] if i < len(row) else '') for i, h in enumerate(headers)})
            if not records:
                return pd.DataFrame(columns=COLUNAS_ESTOQUE)
            df = pd.DataFrame(records)
            return _ensure_cols(df, COLUNAS_ESTOQUE)
        except Exception:
            return pd.DataFrame(columns=COLUNAS_ESTOQUE)


    @st.cache_data(ttl=30)
    def ler_registro_diario() -> pd.DataFrame:
        config = get_config()
        try:
            data = _get_ws(config.aba_registro).get_all_records()
            df = pd.DataFrame(data) if data else pd.DataFrame(columns=COLUNAS_REGISTRO)
            return _ensure_cols(df, COLUNAS_REGISTRO)
        except gspread.exceptions.WorksheetNotFound:
            return pd.DataFrame(columns=COLUNAS_REGISTRO)
        except Exception:
            st.error('Erro ao ler registro')
            st.error(traceback.format_exc())
            return pd.DataFrame(columns=COLUNAS_REGISTRO)


    @st.cache_data(ttl=30)
    def ler_historico() -> pd.DataFrame:
        config = get_config()
        try:
            data = _get_ws(config.aba_historico).get_all_records()
            df = pd.DataFrame(data) if data else pd.DataFrame(columns=COLUNAS_HISTORICO)
            return _ensure_cols(df, COLUNAS_HISTORICO)
        except gspread.exceptions.WorksheetNotFound:
            return pd.DataFrame(columns=COLUNAS_HISTORICO)
        except Exception:
            st.error('Erro ao ler histórico')
            st.error(traceback.format_exc())
            return pd.DataFrame(columns=COLUNAS_HISTORICO)


    # WRITE
    def adicionar_medicamento(dados: dict[str, Any]) -> bool:
        try:
            config = get_config()
            ws = _get_ws(config.aba_estoque)

            # Read headers and rows
            all_rows = ws.get_all_values()
            headers = all_rows[0] if all_rows and len(all_rows) > 0 else []

            def _tokens(s: str) -> set[str]:
                if s is None:
                    return set()
                return set(re.findall(r"[a-z0-9]+", str(s).lower()))

            col_map: dict[int, str] = {}
            for idx, h in enumerate(headers):
                h_toks = _tokens(h)
                if 'p' in h_toks and 'para' not in h_toks:
                    h_toks = h_toks | {'para'}
                for canon in COLUNAS_ESTOQUE:
                    c_toks = _tokens(canon)
                    stop = {'de', 'da', 'do', 'dos', 'das', 'o', 'a', 'e'}
                    if c_toks - stop <= h_toks:
                        col_map[idx] = canon
                        break

            # find last filled row (prefer Medicamento column)
            med_idx = None
            for idx, canon in col_map.items():
                if canon and canon.lower().startswith('medicamento'):
                    med_idx = idx
                    break

            last_data_row = 1
            data_rows = all_rows[1:]
            if data_rows:
                if med_idx is not None:
                    for i in range(len(data_rows) - 1, -1, -1):
                        row = data_rows[i]
                        if med_idx < len(row) and str(row[med_idx]).strip() != '':
                            last_data_row = i + 2
                            break
                    else:
                        for i in range(len(data_rows) - 1, -1, -1):
                            if any(str(c).strip() != '' for c in data_rows[i]):
                                last_data_row = i + 2
                                break
                else:
                    for i in range(len(data_rows) - 1, -1, -1):
                        if any(str(c).strip() != '' for c in data_rows[i]):
                            last_data_row = i + 2
                            break

            target = last_data_row + 1

            # Build row aligned to headers; leave Dias/Status empty so sheet formulas handle them
            ncols = max(len(headers), len(COLUNAS_ESTOQUE))
            new_row = [''] * ncols
            for idx in range(ncols):
                canon = col_map.get(idx)
                if canon:
                    if canon in ("Dias para Vencer", "Status"):
                        new_row[idx] = ''
                    else:
                        new_row[idx] = dados.get(canon, '')

            # try insert, fallback to insertDimension+update, then fallback to append
            try:
                ws.insert_row(new_row, index=target, value_input_option="USER_ENTERED")
            except Exception:
                try:
                    sheet_id = ws._properties.get('sheetId')
                    if sheet_id is None:
                        raise RuntimeError('sheetId não disponível')
                    body = {'requests': [{'insertDimension': {
                        'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': target - 1, 'endIndex': target},
                        'inheritFromBefore': False}}]}
                    _get_spreadsheet().batch_update(body)
                    end_col = chr(64 + min(len(new_row), 26)) if len(new_row) >= 1 else 'A'
                    _get_ws(get_config().aba_estoque).update(f"A{target}:{end_col}{target}", [new_row], value_input_option="USER_ENTERED")
                except Exception:
                    try:
                        ws.append_row(new_row, value_input_option="USER_ENTERED")
                    except Exception:
                        st.warning('Não foi possível inserir/append a nova linha. Verifique permissões e quota.')
                        st.error(traceback.format_exc())
                        return False

            ler_estoque.clear()
            return True

        except Exception:
            st.error('Erro ao cadastrar medicamento')
            st.error(traceback.format_exc())
            return False


    def atualizar_medicamento(sheet_row: int, dados: dict[str, Any]) -> bool:
        try:
            config = get_config()
            ws = _get_ws(config.aba_estoque)
            headers = ws.row_values(1)

            def _toks(s: str) -> set[str]:
                t = set(re.findall(r"[a-z0-9]+", str(s).lower())) if s else set()
                if 'p' in t and 'para' not in t:
                    t |= {'para'}
                return t

            skip = {"Dias para Vencer", "Status"}
            stop = {'de', 'da', 'do', 'dos', 'das', 'o', 'a', 'e'}
            cell_updates: list[dict] = []
            for col_idx, h in enumerate(headers, start=1):
                h_toks = _toks(h)
                for canon in COLUNAS_ESTOQUE:
                    if canon in skip:
                        continue
                    c_toks = _toks(canon) - stop
                    if c_toks and c_toks <= h_toks:
                        cell_updates.append({'range': f'{chr(64 + col_idx)}{sheet_row}', 'values': [[dados.get(canon, '')]]})
                        break

            if cell_updates:
                ws.batch_update(cell_updates, value_input_option='USER_ENTERED')
            ler_estoque.clear()
            return True
        except Exception:
            st.error('Erro ao atualizar medicamento')
            st.error(traceback.format_exc())
            return False


    def excluir_medicamento(sheet_row: int) -> bool:
        try:
            config = get_config()
            _get_ws(config.aba_estoque).delete_rows(sheet_row)
            ler_estoque.clear()
            return True
        except Exception:
            st.error('Erro ao excluir medicamento')
            st.error(traceback.format_exc())
            return False


    def adicionar_registro_diario(dados: dict[str, Any]) -> bool:
        try:
            config = get_config()
            _get_ws(config.aba_registro).append_row(_row(dados, COLUNAS_REGISTRO), value_input_option="USER_ENTERED")
            ler_registro_diario.clear()
            return True
        except Exception:
            st.error('Erro ao registrar aplicação')
            st.error(traceback.format_exc())
            return False


    def adicionar_historico(dados: dict[str, Any]) -> bool:
        try:
            config = get_config()
            _get_ws(config.aba_historico).append_row(_row(dados, COLUNAS_HISTORICO), value_input_option="USER_ENTERED")
            ler_historico.clear()
            return True
        except Exception:
            st.error('Erro ao registrar histórico')
            st.error(traceback.format_exc())
            return False

else:
    def ler_estoque() -> pd.DataFrame:
        _missing_dependency_msg()
        return pd.DataFrame(columns=COLUNAS_ESTOQUE)

    def ler_registro_diario() -> pd.DataFrame:
        _missing_dependency_msg()
        return pd.DataFrame(columns=COLUNAS_REGISTRO)

    def ler_historico() -> pd.DataFrame:
        _missing_dependency_msg()
        return pd.DataFrame(columns=COLUNAS_HISTORICO)

    def adicionar_medicamento(dados: dict[str, Any]) -> bool:
        _missing_dependency_msg()
        return False

    def atualizar_medicamento(sheet_row: int, dados: dict[str, Any]) -> bool:
        _missing_dependency_msg()
        return False

    def excluir_medicamento(sheet_row: int) -> bool:
        _missing_dependency_msg()
        return False

    def adicionar_registro_diario(dados: dict[str, Any]) -> bool:
        _missing_dependency_msg()
        return False

    def adicionar_historico(dados: dict[str, Any]) -> bool:
        _missing_dependency_msg()
        return False
