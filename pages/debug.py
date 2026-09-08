import importlib.util
import os
import platform
import sys
from typing import Any

import pandas as pd
import streamlit as st
import services.sheets_service as sheets
from utils.config import get_config
from utils.constants import (
    COLUNAS_ESTOQUE,
    COLUNAS_HISTORICO,
    COLUNAS_MATERIAIS,
    COLUNAS_REGISTRO,
)

st.title("🐞 Diagnóstico do sistema")
st.caption("Execute os testes abaixo para identificar configuração, ambiente, abas e campos sem precisar depurar o código manualmente.")

def status_resultado(status: int, detalhe: str, **extra: Any) -> dict[str, Any]:
    return {"Status": status, "Detalhe": detalhe, **extra}


def status_excecao(error: Exception) -> tuple[int, str]:
    if isinstance(error, (FileNotFoundError, KeyError)):
        return 404, str(error)
    if isinstance(error, PermissionError):
        return 403, str(error)
    response = getattr(error, "response", None)
    response_status = getattr(response, "status_code", None)
    if response_status in (401, 403, 404):
        return response_status, str(error)
    return 500, f"{type(error).__name__}: {error}"

def executar_diagnostico() -> dict[str, Any]:
    config = get_config()
    resultados: list[dict[str, Any]] = []
    abas = {
        "Estoque de Medicamentos": (config.aba_estoque, COLUNAS_ESTOQUE),
        "Estoque de Materiais": (config.aba_materiais, COLUNAS_MATERIAIS),
        "Registro Diário": (config.aba_registro, COLUNAS_REGISTRO),
        "Histórico": (config.aba_historico, COLUNAS_HISTORICO),
    }
    resultados.append(status_resultado(
        200 if sheets._GSPREAD_AVAILABLE else 500,
        "gspread e dependências Google disponíveis" if sheets._GSPREAD_AVAILABLE else "gspread não foi carregado",
        Teste="Dependências",
    ))
    resultados.append(status_resultado(
        200 if config.spreadsheet_id else 404,
        "SPREADSHEET_ID configurado" if config.spreadsheet_id else "SPREADSHEET_ID vazio",
        Teste="Configuração",
    ))

    try:
        client = sheets._get_client()
        resultados.append(status_resultado(200, "Cliente autenticado", Teste="Cliente Google"))
    except Exception as error:
        code, detail = status_excecao(error)
        resultados.append(status_resultado(code, detail, Teste="Cliente Google"))
        return {"resultados": resultados, "abas": [], "leituras": []}

    try:
        spreadsheet = sheets._get_spreadsheet()
        nomes_abas = [worksheet.title for worksheet in spreadsheet.worksheets()]
        resultados.append(status_resultado(
            200,
            f"Planilha aberta: {spreadsheet.title}",
            Teste="Planilha principal",
        ))
    except Exception as error:
        code, detail = status_excecao(error)
        resultados.append(status_resultado(code, detail, Teste="Planilha principal"))
        return {"resultados": resultados, "abas": [], "leituras": []}

    abas_resultado: list[dict[str, Any]] = []
    leituras: list[dict[str, Any]] = []
    for nome, (aba, esperadas) in abas.items():
        try:
            worksheet = sheets._get_ws(aba)
            valores = worksheet.get_all_values()
            headers = valores[0] if valores else []
            ausentes = [campo for campo in esperadas if campo not in headers]
            abas_resultado.append(status_resultado(
                200,
                f"Aba encontrada: {worksheet.title}",
                Planilha=nome,
                AbaConfigurada=aba,
                Registros=max(len(valores) - 1, 0),
                CamposAusentes=", ".join(ausentes) or "Nenhum",
            ))
        except Exception as error:
            code, detail = status_excecao(error)
            abas_resultado.append(status_resultado(
                code,
                detail,
                Planilha=nome,
                AbaConfigurada=aba,
            ))

    leitores = {
        "ler_estoque": (sheets.ler_estoque, COLUNAS_ESTOQUE),
    "ler_materiais": (sheets.ler_materiais, COLUNAS_MATERIAIS),
    "ler_registro_diario": (sheets.ler_registro_diario, COLUNAS_REGISTRO),
    "ler_historico": (sheets.ler_historico, COLUNAS_HISTORICO),
    }
    for nome, (leitor, esperadas) in leitores.items():
        try:
            dataframe = leitor()
            ausentes = [campo for campo in esperadas if campo not in dataframe.columns]
            leituras.append(status_resultado(
                200,
                "Leitura executada",
                Leitor=nome,
                Registros=len(dataframe),
                CamposRetornados=", ".join(map(str, dataframe.columns)),
                CamposAusentes=", ".join(ausentes) or "Nenhum",
            ))
        except Exception as error:
            code, detail = status_excecao(error)
            leituras.append(status_resultado(code, detail, Leitor=nome))

    return {"resultados": resultados, "abas": abas_resultado, "leituras": leituras, "nomes_abas": nomes_abas}

st.subheader("Ambiente em execução")
ambiente = pd.DataFrame([{
    "Python executado": sys.executable,
    "Versão Python": platform.python_version(),
    "Ambiente VENV": "Sim" if os.path.sep + ".venv" + os.path.sep in sys.executable else "Não confirmado",
    "gspread instalado": importlib.util.find_spec("gspread") is not None,
    "reportlab instalado": importlib.util.find_spec("reportlab") is not None,
}])
st.dataframe(ambiente, width="stretch", hide_index=True)

config = get_config()
st.subheader("Configuração usada pelo código")
st.dataframe(pd.DataFrame([{
    "SPREADSHEET_ID": "Configurado" if config.spreadsheet_id else "Vazio",
    "Aba estoque": config.aba_estoque,
    "Aba materiais": config.aba_materiais,
    "Aba registro": config.aba_registro,
    "Aba histórico": config.aba_historico,
}]), width="stretch", hide_index=True)

col_run, col_clear = st.columns(2)
with col_run:
    executar = st.button("▶ Executar diagnóstico completo", type="primary", width="stretch")
with col_clear:
    if st.button("🧹 Limpar caches e testar novamente", width="stretch"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

if executar or "diagnostico" not in st.session_state:
    if executar:
        with st.spinner("Consultando Google Sheets e executando leitores..."):
            st.session_state.diagnostico = executar_diagnostico()
    else:
        st.info("Clique em **Executar diagnóstico completo** para consultar as planilhas.")
        st.stop()

diagnostico = st.session_state.diagnostico

st.subheader("Resumo dos testes")
resumo = pd.DataFrame(diagnostico["resultados"])
st.dataframe(resumo, width="stretch", hide_index=True)

st.subheader("Planilhas e abas acessadas")
abas_df = pd.DataFrame(diagnostico["abas"])
if not abas_df.empty:
    st.dataframe(abas_df, width="stretch", hide_index=True)
else:
    st.warning("Não foi possível consultar as abas da planilha principal.")

st.subheader("Retorno de cada leitor")
st.caption("Código 200 = leitura concluída; 404 = planilha/aba/campo não encontrado; 403 = permissão; 500 = erro de código, rede ou configuração.")
leituras_df = pd.DataFrame(diagnostico["leituras"])
if not leituras_df.empty:
    st.dataframe(leituras_df, width="stretch", hide_index=True)

st.subheader("Gerador de possibilidades")
problemas: list[str] = []
if not sheets._GSPREAD_AVAILABLE:
    problemas.append("Dependências Google não carregadas: confirme o interpretador exibido em Ambiente e reinstale requirements.txt nesse mesmo VENV.")
if not config.spreadsheet_id:
    problemas.append("SPREADSHEET_ID vazio: configure o ID na raiz dos secrets.")
for item in diagnostico["abas"]:
    if item["Status"] == 404:
        problemas.append(f"A aba configurada '{item['AbaConfigurada']}' não foi encontrada. Confira acentos, espaços e o nome da guia no Google Sheets.")
    if item.get("CamposAusentes") not in (None, "Nenhum"):
        problemas.append(f"A aba '{item['AbaConfigurada']}' não possui os campos esperados: {item['CamposAusentes']}.")
for item in diagnostico["leituras"]:
    if item["Status"] != 200:
        problemas.append(f"O leitor {item['Leitor']} falhou com status {item['Status']}: {item['Detalhe']}")

if problemas:
    for problema in problemas:
        st.warning(problema)
else:
    st.success("Nenhuma inconsistência foi encontrada nos testes executados.")

with st.expander("Como o código trata cada planilha"):
    st.markdown(
        "- **Estoque de Medicamentos:** `ler_estoque()` normaliza cabeçalhos, mantém `_sheet_row` e recalcula status.\n"
        "- **Estoque de Materiais:** `ler_materiais()` lê a aba configurada e garante `COLUNAS_MATERIAIS`.\n"
        "- **Registro Diário:** `ler_registro_diario()` normaliza os campos de aplicações e ignora linhas sem identificador.\n"
        "- **Histórico:** `ler_historico()` lê registros e garante `COLUNAS_HISTORICO`."
    )
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
    st.write("aba_materiais:", repr(cfg.aba_materiais))
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

    nomes_abas = [worksheet.title for worksheet in ss.worksheets()]
    if cfg.aba_materiais in nomes_abas:
        st.success(f"Aba de materiais encontrada: {cfg.aba_materiais}")
    else:
        st.warning(
            f"Aba de materiais não encontrada: {cfg.aba_materiais}. "
            f"Abas disponíveis: {', '.join(nomes_abas)}"
        )

except Exception:
    st.error(traceback.format_exc())