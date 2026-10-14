"""Cores do app. O vermelho abaixo é a única cor de destaque: nada de verde.
Para trocar o tom, altere só VERMELHO (e o primaryColor em .streamlit/config.toml)."""

VERMELHO = "#E60000"
SOBRE_VERMELHO = "#FFFFFF"            # texto sobre fundo vermelho

# Mini-gráficos de tendência (segundo a imagem de referência): linha azul, pontos vermelhos
LINHA_TENDENCIA = "#3b6ea5"
CINZA_DESTAQUE = "rgba(128,128,128,.22)"   # abas selecionadas e linha de total
DESTAQUE_TOTAL = CINZA_DESTAQUE            # fundo da linha de total
BORDA_TABELA = "rgba(128,128,128,.45)"

# Abas: destaque acinzentado (translúcido, funciona no modo claro e no escuro)
CSS_GLOBAL = """
<style>
/* versões novas do Streamlit (react-aria) e antigas (baseweb) */
[data-testid="stTab"], button[data-baseweb="tab"] { border-radius: 6px 6px 0 0 !important; }
[data-testid="stTab"][aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] {
    background-color: rgba(128,128,128,.22) !important;
}
[data-testid="stTab"][aria-selected="true"] p, button[data-baseweb="tab"][aria-selected="true"] p {
    color: #31333F !important; font-weight: 700 !important;
}
[data-testid="stTab"][aria-selected="true"] { color: #31333F !important; }
@media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) [data-testid="stTab"][aria-selected="true"],
    :root:not([data-theme="light"]) [data-testid="stTab"][aria-selected="true"] p { color: #FAFAFA !important; }
}
[data-testid="stTab"]:hover, button[data-baseweb="tab"]:hover { background-color: rgba(128,128,128,.12) !important; }
[data-testid="stTab"][aria-selected="true"] > div:not([data-testid]), div[data-baseweb="tab-highlight"] {
    background-color: rgba(128,128,128,.85) !important;
}
</style>
"""

# Estilos prontos
CSS_ABAIXO_META = f"background-color:{VERMELHO};color:{SOBRE_VERMELHO};font-weight:700"
