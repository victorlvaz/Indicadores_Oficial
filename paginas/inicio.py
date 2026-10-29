"""Página inicial: cartões com ícone e botão que levam direto ao relatório."""
import html

import streamlit as st

from comum.idioma import cabecalho, frase
from comum.tema import VERMELHO
from relatorios import RELATORIOS

COLUNAS = 3
ALTURA = 355

cabecalho("指标", "Indicadores")
st.write(frase("点击下方卡片中的按钮，直接进入所需报表。",
               "Clique no botão do cartão para ir direto ao relatório que você quer."))

st.html(f"""<style>
.cartao-icone {{ display:inline-flex; align-items:center; justify-content:center; width:52px; height:52px;
  border-radius:14px; background:{VERMELHO}14; color:{VERMELHO}; margin-bottom:.4rem; }}
.cartao-icone .material-symbols-rounded {{ font-size:30px; line-height:1; }}
.cartao-titulo {{ font-size:1.05rem; font-weight:700; line-height:1.3; margin:-.2rem 0 .35rem; }}
.cartao-desc {{ font-size:.85rem; opacity:.75; line-height:1.45; }}
</style>""")


def _nome_icone(icone: str) -> str:
    return icone.replace(":material/", "").rstrip(":")


def _cartao(r: dict, chave: str) -> None:
    with st.container(border=True, height=ALTURA):
        st.markdown(f"## :red[:material/{_nome_icone(r['icone'])}:]")
        st.html(f'<div class="cartao-titulo">{html.escape(r["titulo"])}</div>'
                f'<div class="cartao-desc">{html.escape(r["descricao"]).replace(chr(10), "<br>")}</div>')
        if st.button(frase("打开报表", "Abrir relatório"), key=chave, type="primary", icon=":material/arrow_forward:",
                     width="stretch"):
            st.switch_page(r["arquivo"])


grupos: dict[str, list] = {}
for r in RELATORIOS:
    grupos.setdefault(r["grupo"], []).append(r)

for grupo, itens in grupos.items():
    st.subheader(grupo)
    for i in range(0, len(itens), COLUNAS):
        cols = st.columns(COLUNAS)
        for col, r in zip(cols, itens[i:i + COLUNAS]):
            with col:
                _cartao(r, f"ini_{r['url']}")
