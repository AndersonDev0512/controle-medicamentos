"""Login com senha única compartilhada.

A sessão do Streamlit zera a cada recarga, aba nova ou clique na barra de navegação
(os links recarregam a página). Por isso, depois do login, gravamos no navegador um
cookie assinado com HMAC e com validade; cada sessão nova lê esse cookie em
``st.context.cookies`` e entra sem pedir a senha de novo.

Configuração em ``.streamlit/secrets.toml``:
    APP_PASSWORD = "senha da equipe"     # sem ela, o login fica desativado
    AUTH_SECRET  = "texto aleatório"     # opcional, reforça a assinatura do cookie
    AUTH_HORAS   = 12                    # opcional, validade do login em horas
Trocar APP_PASSWORD invalida todos os logins abertos.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import os
import time

import streamlit as st
import streamlit.components.v1 as components

COOKIE = "cm_auth"
_SESSAO_OK = "cm_auth_ok"
_SESSAO_SAIU = "cm_auth_saiu"


def _secret(nome: str, padrao: str = "") -> str:
    valor = os.environ.get(nome)
    if valor:
        return valor
    try:
        return str(st.secrets.get(nome, padrao) or padrao)
    except Exception:
        return padrao


def _senha_configurada() -> str:
    return _secret("APP_PASSWORD")


def login_ativo() -> bool:
    return bool(_senha_configurada())


def _validade_segundos() -> int:
    try:
        return max(1, int(float(_secret("AUTH_HORAS", "12")))) * 3600
    except ValueError:
        return 12 * 3600


def _assinatura(expira: int) -> str:
    chave = hashlib.sha256(f"{_secret('AUTH_SECRET')}|{_senha_configurada()}".encode()).digest()
    return hmac.new(chave, str(expira).encode(), hashlib.sha256).hexdigest()


def _gerar_token() -> str:
    expira = int(time.time()) + _validade_segundos()
    return f"{expira}.{_assinatura(expira)}"


def _token_valido(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    expira_txt, assinatura = token.split(".", 1)
    if not expira_txt.isdigit() or int(expira_txt) < time.time():
        return False
    return hmac.compare_digest(assinatura, _assinatura(int(expira_txt)))


def _cookie_atual() -> str | None:
    try:
        return st.context.cookies.get(COOKIE)
    except Exception:
        return None


def _gravar_cookie(valor: str, max_age: int) -> None:
    # O iframe do componente tem allow-same-origin, então o cookie vale para o app.
    components.html(
        "<script>window.parent.document.cookie = "
        f"'{COOKIE}={valor}; path=/; max-age={max_age}; SameSite=Lax';</script>",
        height=0,
    )


def autenticado() -> bool:
    if not _senha_configurada():
        return True
    if st.session_state.get(_SESSAO_OK):
        return True
    if not st.session_state.get(_SESSAO_SAIU) and _token_valido(_cookie_atual()):
        st.session_state[_SESSAO_OK] = True
        return True
    return False


def sair() -> None:
    st.session_state.pop(_SESSAO_OK, None)
    st.session_state.pop("cm_auth_token", None)
    st.session_state[_SESSAO_SAIU] = True


def _tela_login() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        .lg-card { max-width: 440px; margin: 10vh auto 1.2rem; padding: 2rem 2rem 1.2rem; text-align: center;
            border: 1px solid rgba(96,165,250,.16); border-radius: 18px;
            background: radial-gradient(circle at 90% 0%, rgba(20,184,166,.18), transparent 40%),
                        linear-gradient(135deg, #0b1730, #0f1f3d); box-shadow: 0 18px 45px rgba(0,0,0,.35); }
        .lg-logo { display: grid; place-items: center; width: 64px; height: 64px; margin: 0 auto 1rem;
            border-radius: 18px; color: #fff !important; background: linear-gradient(135deg, #2563eb, #14b8a6);
            box-shadow: 0 10px 28px rgba(37,99,235,.4); }
        .lg-card h1 { margin: 0 !important; padding: 0 !important; color: #f8fafc !important; font-size: 1.6rem !important; }
        .lg-card p { margin: .35rem 0 0 !important; color: #94a3b8 !important; font-size: .9rem; }
        [data-testid="stForm"] { max-width: 440px; margin: 0 auto; border: 1px solid rgba(96,165,250,.16) !important;
            border-radius: 16px !important; background: rgba(15,23,42,.85); }
        </style>
        """,
        unsafe_allow_html=True,
    )
    clinica = html.escape(_secret("CLINIC_NAME", "Controle de Enfermagem"))
    st.markdown(
        '<div class="lg-card"><div class="lg-logo">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>'
        f"<h1>Controle de Enfermagem</h1><p>{clinica}<br>Informe a senha da equipe para continuar.</p></div>",
        unsafe_allow_html=True,
    )
    with st.form("form_login", clear_on_submit=True):
        senha = st.text_input("Senha", type="password", placeholder="Senha de acesso")
        entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
    if entrar:
        if hmac.compare_digest(senha.encode(), _senha_configurada().encode()):
            st.session_state[_SESSAO_OK] = True
            st.session_state[_SESSAO_SAIU] = False
            st.session_state["cm_auth_token"] = _gerar_token()
            st.rerun()
        time.sleep(1)  # freia tentativas em sequência
        st.error("Senha incorreta.")


def exigir_login() -> None:
    """Bloqueia o app até a senha ser informada. Chamar antes de desenhar qualquer página."""
    if st.query_params.get("logout"):
        sair()
        del st.query_params["logout"]

    if st.session_state.get(_SESSAO_SAIU) and _cookie_atual():
        _gravar_cookie("", 0)

    if autenticado():
        token = st.session_state.get("cm_auth_token")
        # Grava o cookie até a próxima sessão já chegar com ele.
        if token and _cookie_atual() != token:
            _gravar_cookie(token, _validade_segundos())
        return

    _tela_login()
    st.stop()
