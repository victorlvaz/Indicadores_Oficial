"""Aba Resumo do SM: totais, taxa e gráficos por dia, semana ou mês, com filtro de regional."""
from datetime import datetime

import pandas as pd
import streamlit as st

from comum.estilos import pct, pp
from comum.graficos import grafico_taxa, grafico_volume
from comum.tema import CINZA_DESTAQUE, VERMELHO
from comum.uploads import opcao_valida
from . import textos as tx
from .calculos import resumo
from .config import REGIOES, TIPOS

VISOES = ("D", "W", "M")


def _tabela(df: pd.DataFrame):
    """(tabela crua para exportar, tabela estilizada para a tela). Total do período na 1ª linha, em cinza."""
    prev, real = int(df["prev"].sum()), int(df["real"].sum())
    total = {tx.RES_PERIODO: tx.TOTAL, tx.COL_PREV: prev, tx.COL_REAL: real,
             tx.COL_TAXA: real / prev if prev else float("nan"), tx.COL_VAR: float("nan")}
    corpo = pd.DataFrame({tx.RES_PERIODO: df["periodo"], tx.COL_PREV: df["prev"], tx.COL_REAL: df["real"],
                          tx.COL_TAXA: df["taxa"], tx.COL_VAR: df["variacao"]})
    cru = pd.concat([pd.DataFrame([total]), corpo.iloc[::-1]], ignore_index=True)   # mais recente primeiro
    txt = cru.copy()
    txt[tx.COL_TAXA] = cru[tx.COL_TAXA].map(pct)
    txt[tx.COL_VAR] = cru[tx.COL_VAR].map(pp)
    est = pd.DataFrame("", index=txt.index, columns=txt.columns)
    est.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    est.loc[(cru[tx.COL_VAR].round(4) < 0).fillna(False), tx.COL_VAR] = f"color:{VERMELHO};font-weight:700"
    return cru, txt.style.apply(lambda _: est, axis=None)


def _secao(base, tipo, regional, freq, ini, fim, export):
    st.subheader(tx.subtitulo_resumo(tipo))
    df = resumo(base, tipo, freq, regional, ini, fim)
    if df.empty or df["prev"].sum() == 0:
        st.info(tx.RES_SEM_DADOS)
        return
    prev, real = int(df["prev"].sum()), int(df["real"].sum())
    taxa = real / prev
    ultimo = df.dropna(subset=["taxa"]).iloc[-1]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(tx.COL_PREV, f"{prev:,}".replace(",", "."))
    c2.metric(tx.COL_REAL, f"{real:,}".replace(",", "."))
    c3.metric(tx.COL_TAXA, pct(taxa))
    delta = "" if pd.isna(ultimo["variacao"]) else pp(ultimo["variacao"]).replace("▲ ", "").replace("▼ ", "")
    c4.metric(f"{tx.RES_ULTIMO} · {ultimo['periodo']}", pct(ultimo["taxa"]), delta or None, delta_color="off")

    ordem = list(df["periodo"])
    g1, g2 = st.columns(2)
    with g1:
        st.altair_chart(grafico_taxa(df, ordem, None, pequeno=len(df) > 60, titulo_y=tx.RES_GRAF_TAXA,
                                     titulo_periodo=tx.RES_PERIODO, titulo_taxa=tx.RES_GRAF_TAXA), width="stretch")
    with g2:
        st.altair_chart(grafico_volume(df, ordem, tx.COL_PREV, tx.COL_REAL, tx.RES_GRAF_VOL, tx.RES_PERIODO),
                        width="stretch")
    if df["taxa"].isna().any():
        st.caption(tx.RES_LACUNA)

    cru, estilizada = _tabela(df)
    with st.expander(tx.RES_TABELA):
        st.dataframe(estilizada, width="stretch", hide_index=True, height=min((len(cru) + 1) * 35 + 3, 420))
    exp = cru.copy()
    exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100
    export[tx.aba_excel_resumo(tipo)] = (exp, {"taxa": tx.COL_TAXA, "pp_extra": [tx.COL_VAR]})


def mostrar(base: pd.DataFrame, export: dict) -> None:
    """Desenha a aba inteira: Coleta primeiro, depois Entrega."""
    st.caption(tx.RES_NOTA)
    anos = sorted(base["dia"].dt.year.unique(), reverse=True)
    opcoes_ano = anos + [None]
    opcao_valida("smres_ano", opcoes_ano)
    regs = [r for r in REGIOES if r in set(base["regiao"])]
    opcoes_reg = ["*"] + regs            # "*" = todas (None viraria o texto "Choose an option")
    opcao_valida("smres_reg", opcoes_reg)

    f1, f2, f3 = st.columns(3)
    regional = f1.selectbox(tx.RES_REGIONAL, opcoes_reg, key="smres_reg",
                            format_func=lambda r: tx.RES_TODAS if r == "*" else r)
    regional = None if regional == "*" else regional
    freq = f2.radio(tx.RES_VISAO, VISOES, index=1, horizontal=True, key="smres_vis",
                    format_func=lambda g: tx.GRAN_NOMES[g])
    atual = datetime.now().year
    ano = f3.selectbox(tx.RES_ANO, opcoes_ano, index=anos.index(atual) if atual in anos else 0, key="smres_ano",
                       format_func=lambda a: tx.RES_TODO_HISTORICO if a is None else str(a))
    ini, fim = (None, None) if ano is None else (pd.Timestamp(year=ano, month=1, day=1),
                                                 pd.Timestamp(year=ano, month=12, day=31))
    for tipo in TIPOS:
        _secao(base, tipo, regional, freq, ini, fim, export)
