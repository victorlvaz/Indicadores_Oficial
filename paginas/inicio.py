"""Página inicial: lista os relatórios disponíveis."""
import streamlit as st

from comum.idioma import cabecalho, frase
from relatorios import RELATORIOS

cabecalho("指标", "Indicadores")
st.write(frase("请在左侧菜单或下方快捷入口中选择报表。",
               "Escolha um relatório no menu lateral ou nos atalhos abaixo."))

grupo_atual = None
for r in RELATORIOS:
    if r["grupo"] != grupo_atual:
        grupo_atual = r["grupo"]
        st.subheader(grupo_atual)
    st.page_link(r["arquivo"], label=r["titulo"], icon=r["icone"])
    st.caption(r["descricao"])
