import streamlit as st
from utils.config import get_config
from utils.helpers import sanitize_service_account
import services.sheets_service as sheets
import traceback

st.title("🐞 Debug")

# ====================================================
# CONFIG
# ====================================================

st.subheader("Configuração")

try:
    cfg = get_config()

    st.write("spreadsheet_id:", repr(cfg.spreadsheet_id))
    st.write("aba_estoque:", repr(cfg.aba_estoque))
    st.write("aba_registro:", repr(cfg.aba_registro))
    st.write("aba_historico:", repr(cfg.aba_historico))

except Exception:
    st.error(traceback.format_exc())

# ====================================================
# SECRETS
# ====================================================

st.subheader("Secrets")

try:
    st.write("SPREADSHEET_ID raiz:")
    st.code(str(st.secrets.get("SPREADSHEET_ID")))

    gcp = st.secrets.get("gcp_service_account")

    if gcp:
        st.success("gcp_service_account encontrado")

        st.json({
            "project_id": gcp.get("project_id"),
            "client_email": gcp.get("client_email"),
            "type": gcp.get("type")
        })

        st.write("SPREADSHEET_ID dentro do gcp_service_account:")
        st.code(str(gcp.get("SPREADSHEET_ID")))

    else:
        st.error("gcp_service_account não encontrado")

except Exception:
    st.error(traceback.format_exc())

# ====================================================
# CLIENT
# ====================================================

st.subheader("Google Client")

try:
    client = sheets._get_client()

    st.success("Client criado com sucesso")

except Exception:
    st.error(traceback.format_exc())

# ====================================================
# PLANILHAS VISÍVEIS
# ====================================================

st.subheader("Planilhas visíveis para a Service Account")

try:
    spreadsheets = client.openall()

    st.write("Quantidade:", len(spreadsheets))

    for ss in spreadsheets:
        st.write({
            "title": ss.title,
            "id": ss.id
        })

except Exception:
    st.error(traceback.format_exc())

# ====================================================
# TESTE DIRETO
# ====================================================

st.subheader("Abrindo por ID")

try:

    spreadsheet_id = cfg.spreadsheet_id

    st.write("Tentando abrir:")
    st.code(spreadsheet_id)

    ss = client.open_by_key(spreadsheet_id)

    st.success("Planilha aberta com sucesso")

    st.write("Título:")
    st.code(ss.title)

except Exception:
    st.error(traceback.format_exc())