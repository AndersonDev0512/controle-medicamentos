"""Avisos em pop-up centralizado (st.dialog) para as ações de cadastro, edição e exclusão.

Uso:
    mostrar_aviso("Informe o lote.", "erro")            # na hora, sem rerun
    agendar_aviso("Material cadastrado!", "sucesso")     # antes de st.rerun()
    mostrar_aviso_pendente()                             # no topo da página

Estilos em assets/style.css (seção AVISOS).
"""
from __future__ import annotations

import html

import streamlit as st

from utils.ui import icon

_CHAVE = "toast_mensagem"

TIPOS = {
    "sucesso": ("check", "#22C55E", "Tudo certo!"),
    "erro": ("x-circle", "#EF4444", "Não foi possível concluir"),
    "aviso": ("triangle", "#F59E0B", "Atenção"),
}
# Compatibilidade com o formato antigo (texto, emoji) guardado em session_state.
_EMOJI_TIPO = {"✅": "sucesso", "❌": "erro", "⚠️": "aviso"}


def agendar_aviso(texto: str, tipo: str = "sucesso") -> None:
    st.session_state[_CHAVE] = (texto, tipo)


def mostrar_aviso_pendente() -> None:
    mensagem = st.session_state.pop(_CHAVE, None)
    if mensagem:
        texto, tipo = mensagem
        mostrar_aviso(texto, _EMOJI_TIPO.get(tipo, tipo))


def mostrar_aviso(mensagens: str | list[str], tipo: str = "sucesso") -> None:
    """Abre o pop-up. Só cabe um st.dialog por execução, então junte as mensagens numa lista."""
    lista = [mensagens] if isinstance(mensagens, str) else [str(m) for m in mensagens]
    nome_icone, cor, titulo = TIPOS.get(tipo, TIPOS["aviso"])
    if len(lista) == 1:
        corpo_texto = f"<p>{html.escape(lista[0])}</p>"
    else:
        corpo_texto = "<ul>" + "".join(f"<li>{html.escape(m)}</li>" for m in lista) + "</ul>"

    def conteudo() -> None:
        st.html(
            f'<div class="av-box av-{tipo}" style="--c:{cor}">'
            f'<div class="av-icon">{icon(nome_icone, 38)}</div>'
            f"{corpo_texto}</div>"
        )
        if st.button("OK, entendi", type="primary", width="stretch", key="aviso_ok"):
            st.rerun()

    st.dialog(titulo, width="small")(conteudo)()
