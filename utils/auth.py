"""Login com senha única compartilhada.

A sessão do Streamlit zera a cada recarga, aba nova ou clique na barra de navegação
(os links recarregam a página). Por isso, depois do login, gravamos no navegador um
cookie assinado com HMAC e com validade; cada sessão nova lê esse cookie e entra sem
pedir a senha de novo.

O cookie é lido de dois jeitos: ``st.context.cookies`` (rodando local) e um componente
que lê ``document.cookie`` no navegador e devolve o valor ao Python. O segundo é o que
funciona no Streamlit Community Cloud, que filtra os cookies antes de chegarem ao app.

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


# Componente sem visual (escondido em style.css por .st-key-cm_auth_cookie). Roda na
# página do app: grava ou apaga o cookie quando pedido e devolve o valor atual em ``token``.
_COOKIE_JS = """
export default function ({ data, setStateValue }) {
    const pedido = data || {};
    if (typeof pedido.valor === "string") {
        const seguro = location.protocol === "https:" ? "; Secure" : "";
        document.cookie = `%(nome)s=${pedido.valor}; path=/; max-age=${pedido.max_age}; SameSite=Lax${seguro}`;
    }
    const achado = document.cookie.split("; ").find((c) => c.startsWith("%(nome)s="));
    setStateValue("token", achado ? achado.slice(%(tam)d) : "");
}
""" % {"nome": COOKIE, "tam": len(COOKIE) + 1}
_cookie_navegador = st.components.v2.component("cm_auth_cookie", js=_COOKIE_JS)


def _cookie_no_navegador(valor: str | None = None, max_age: int = 0) -> str | None:
    """Monta o componente (gravando ``valor`` se informado) e devolve o cookie lido no
    navegador. Devolve None na primeira execução, antes de o navegador responder."""
    pedido = {} if valor is None else {"valor": valor, "max_age": max_age}
    return _cookie_navegador(data=pedido, key="cm_auth_cookie", on_token_change=lambda: None).token


def _entrar(token: str) -> None:
    st.session_state[_SESSAO_OK] = True
    st.session_state[_SESSAO_SAIU] = False
    st.session_state["cm_auth_token"] = token


def autenticado() -> bool:
    if not _senha_configurada():
        return True
    return bool(st.session_state.get(_SESSAO_OK))


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
            _entrar(_gerar_token())
            st.rerun()
        time.sleep(1)  # freia tentativas em sequência
        st.error("Senha incorreta.")


def exigir_login() -> None:
    """Bloqueia o app até a senha ser informada. Chamar antes de desenhar qualquer página."""
    if st.query_params.get("logout"):
        sair()
        del st.query_params["logout"]

    if not _senha_configurada():
        return

    if st.session_state.get(_SESSAO_SAIU):
        _cookie_no_navegador("", 0)  # apaga o cookie
    elif autenticado():
        # Mantém o cookie gravado para as próximas sessões (recarga, aba nova, navegação).
        _cookie_no_navegador(st.session_state.get("cm_auth_token", ""), _validade_segundos())
        return
    else:
        no_navegador = _cookie_no_navegador()
        for token in (_cookie_atual(), no_navegador):
            if _token_valido(token):
                _entrar(token)
                return
        if no_navegador is None and not _cookie_atual():
            # No Cloud o cookie só chega pelo componente, que responde com um rerun.
            st.markdown('<p class="cm-auth-wait">Verificando acesso…</p>', unsafe_allow_html=True)
            st.stop()

    _tela_login()
    st.stop()
