"""Indicadores – entrada do app (menu de navegação entre relatórios).
Rodar com:  python -m streamlit run app.py
"""
from streamlit import runtime

if not runtime.exists():
    raise SystemExit(
        "\nEste arquivo não deve ser aberto com o botão Run / 'python app.py'.\n"
        "Abra o terminal NA PASTA do projeto e rode:\n\n    python -m streamlit run app.py\n"
    )

import streamlit as st

from comum.idioma import bi
from comum.login import botao_sair, exigir_login
from comum.logo import logo_html
from comum.tema import CSS_GLOBAL
from relatorios import RELATORIOS

st.set_page_config(page_title=bi("指标", "Indicadores"), layout="wide")
st.html(CSS_GLOBAL)
exigir_login()                      # sem entrar, nada abaixo (menu e relatórios) é mostrado
st.html(logo_html())

menu = {"": [st.Page("paginas/inicio.py", title=bi("首页", "Início"), icon=":material/home:", default=True)]}
for r in RELATORIOS:
    menu.setdefault(r["grupo"], []).append(
        st.Page(r["arquivo"], title=r["titulo"], icon=r["icone"], url_path=r["url"])
    )

pagina = st.navigation(menu)
botao_sair()
pagina.run()
