import streamlit as st
from utils.config import get_config
from utils.helpers import check_credentials_configured

st.markdown('<h1 class="page-title">⚙️ Configurações</h1>', unsafe_allow_html=True)

config = get_config()
credentials_ok = check_credentials_configured()

# ── Connection Status ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Status da Conexão</div>', unsafe_allow_html=True)

if credentials_ok:
    st.success("✅ Credenciais do Google Sheets configuradas corretamente.")
else:
    st.error("❌ Credenciais não configuradas. Siga as instruções abaixo.")
    with st.expander("📋 Como configurar o Google Sheets?"):
        st.markdown("""
**1.** Acesse [console.cloud.google.com](https://console.cloud.google.com)  
**2.** Crie um projeto e ative a **Google Sheets API** e a **Google Drive API**  
**3.** Crie uma **Conta de Serviço** e baixe o JSON de credenciais  
**4.** Compartilhe a planilha com o email da conta de serviço  
**5.** Crie o arquivo `.streamlit/secrets.toml` conforme abaixo:
        """)
        st.code("""
[gcp_service_account]
type = "service_account"
project_id = "SEU_PROJETO_ID"
private_key_id = "SUA_CHAVE_ID"
private_key = \"\"\"-----BEGIN RSA PRIVATE KEY-----
...sua chave privada aqui...
-----END RSA PRIVATE KEY-----
\"\"\"
client_email = "sua-conta@projeto.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"

SPREADSHEET_ID = "<SUA_PLANILHA_ID_OU_URL>"
CLINIC_NAME = "Nome da Clínica"
RESPONSIBLE_EMAIL = "email@clinica.com"
        """, language="toml")

st.markdown("<br>", unsafe_allow_html=True)

# ── Clinic Info ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Informações da Clínica</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.text_input("Nome da Clínica", value=config.clinic_name, disabled=True,
                  help="Defina em .streamlit/secrets.toml → CLINIC_NAME")
with col2:
    st.text_input("E-mail do Responsável", value=config.responsible_email, disabled=True,
                  help="Defina em .streamlit/secrets.toml → RESPONSIBLE_EMAIL")

st.markdown("<br>", unsafe_allow_html=True)

# ── Google Sheets Config ───────────────────────────────────────────────────────
st.markdown('<div class="section-header">Google Sheets</div>', unsafe_allow_html=True)
col3, col4 = st.columns(2)
with col3:
    st.text_input("Planilha (ID / URL)", value=config.spreadsheet_id, disabled=True)
    st.text_input("Aba — Estoque", value=config.aba_estoque, disabled=True)
with col4:
    st.text_input("Aba — Registro Diário", value=config.aba_registro, disabled=True)
    st.text_input("Aba — Histórico", value=config.aba_historico, disabled=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Alert Thresholds ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Limites de Alerta de Vencimento</div>', unsafe_allow_html=True)
col5, col6 = st.columns(2)
with col5:
    st.number_input("Atenção (dias)", value=config.dias_alerta_atencao, disabled=True,
                    help="Medicamentos com prazo ≤ X dias recebem status Atenção")
with col6:
    st.number_input("Próximo (dias)", value=config.dias_alerta_proximo, disabled=True,
                    help="Medicamentos com prazo ≤ X dias recebem status Próximo")

st.markdown("<br>", unsafe_allow_html=True)

# ── About ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Sobre o Sistema</div>', unsafe_allow_html=True)
st.markdown("""
<div style="background:#1e293b;border-radius:10px;padding:1.5rem;border:1px solid #334155;line-height:1.9;">
    <div style="font-size:1.15rem;font-weight:700;margin-bottom:0.5rem;">💊 Controle de Medicamentos</div>
    <div style="color:#94a3b8;font-size:0.9rem;">
        Sistema de gestão de medicamentos para clínicas.<br>
        <b>Versão:</b> 1.0.0 &nbsp;|&nbsp; <b>Banco de dados:</b> Google Sheets &nbsp;|&nbsp; <b>Interface:</b> Streamlit<br>
        <b>Notificações:</b> Módulo preparado para e-mail, WhatsApp e notificações internas (não ativo).
    </div>
</div>
""", unsafe_allow_html=True)
