"""Aba Resumo dos Custos: indicadores do período, frete por pacote por regional e por veículo, e linha por período."""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comum import periodos, resumo_dia
from comum.tema import CINZA_DESTAQUE, VERMELHO
from comum.uploads import opcao_valida
from . import textos as tx
from .calculos import por_veiculo, regioes_da, resumo, tabela_periodo

VISOES = ("D", "W", "M")
CINZA = "#8C8C8C"
GRADE = "rgba(128,128,128,.25)"


def brl(v, casas=2) -> str:
    """R$ 1.234,56; '–' sem dado."""
    if pd.isna(v):
        return "–"
    return "R$ " + f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def inteiro(v) -> str:
    return "–" if pd.isna(v) else f"{v:,.0f}".replace(",", ".")


def variacao(v) -> str:
    """Variação relativa com seta; custo que SOBE é ruim."""
    if pd.isna(v):
        return "–"
    x = round(v * 100, 2)
    seta = "▲" if x > 0 else "▼" if x < 0 else "＝"
    return f"{seta} {x:+.2f}".replace(".", ",") + "%"


def _botoes(base, freq, ini, fim):
    if freq == "D":
        return freq, ini, fim
    sub = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    lista = periodos.lista(sub["dia"], freq)
    if not lista:
        return freq, ini, fim
    chave = f"cures_pil_{freq}"
    opcao_valida(chave, lista)
    st.caption(tx.RES_PILULA_W if freq == "W" else tx.RES_PILULA_M)
    per = st.pills(tx.GRAN_NOMES[freq], lista, selection_mode="single", default=lista[-1], key=chave,
                   format_func=lambda p: periodos.rotulo_curto(p, freq, com_ano=ini is None))
    if per is None:
        return freq, ini, fim
    st.caption(f"{tx.RES_DIAS_DE}: {periodos.rotulo(per, freq)}")
    return "D", per, periodos.fim(per, freq)


def _g_barras(df, rotulo, valor="frete_pacote"):
    df = df.dropna(subset=[valor]).sort_values(valor)
    fig = go.Figure(go.Bar(
        y=df[rotulo], x=df[valor], orientation="h", marker_color=CINZA,
        text=[f"{brl(v)} · {int(n)}" for v, n in zip(df[valor], df["viagens"])], textposition="outside",
        hovertemplate="%{y}<br>" + tx.COL_FRETE_PACOTE + ": R$ %{x:,.2f}<extra></extra>"))
    maior = float(df[valor].max()) if len(df) else 1.0
    fig.update_layout(height=70 + 28 * max(len(df), 1), margin=dict(l=10, r=40, t=10, b=20), showlegend=False,
                      xaxis=dict(range=[0, maior * 1.35 or 1], gridcolor=GRADE, zeroline=False, tickprefix="R$ "),
                      yaxis=dict(type="category"))
    return fig


def _g_linha(df):
    fig = go.Figure(go.Scatter(x=list(df["periodo"]), y=df["frete_pacote"], mode="lines+markers", connectgaps=False,
                               line=dict(color=CINZA, width=2), marker=dict(color=VERMELHO, size=8),
                               hovertemplate="%{x}<br>" + tx.COL_FRETE_PACOTE + ": R$ %{y:,.2f}<extra></extra>"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=30), showlegend=False,
                      xaxis=dict(type="category", gridcolor=GRADE), yaxis=dict(gridcolor=GRADE, tickprefix="R$ "))
    return fig


def _tabela(df):
    f, p, k = float(df["frete"].sum()), float(df["pacotes"].sum()), float(df["km"].sum())
    total = {tx.RES_PERIODO: "合计 Total", tx.COL_VIAGENS: int(df["viagens"].sum()), tx.COL_PACOTES: p, tx.COL_KM: k,
             tx.COL_FRETE: f, tx.COL_FRETE_KM: f / k if k else float("nan"),
             tx.COL_FRETE_PACOTE: f / p if p else float("nan"), tx.COL_VAR_PACOTE: float("nan")}
    corpo = pd.DataFrame({tx.RES_PERIODO: df["periodo"], tx.COL_VIAGENS: df["viagens"], tx.COL_PACOTES: df["pacotes"],
                          tx.COL_KM: df["km"], tx.COL_FRETE: df["frete"], tx.COL_FRETE_KM: df["frete_km"],
                          tx.COL_FRETE_PACOTE: df["frete_pacote"], tx.COL_VAR_PACOTE: df["variacao"]})
    cru = pd.concat([pd.DataFrame([total]), corpo.iloc[::-1]], ignore_index=True)
    txt = cru.copy()
    for c in (tx.COL_PACOTES, tx.COL_KM):
        txt[c] = cru[c].map(inteiro)
    for c in (tx.COL_FRETE, tx.COL_FRETE_KM, tx.COL_FRETE_PACOTE):
        txt[c] = cru[c].map(brl)
    txt[tx.COL_VAR_PACOTE] = cru[tx.COL_VAR_PACOTE].map(variacao)
    est = pd.DataFrame("", index=txt.index, columns=txt.columns)
    est.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    est.loc[(cru[tx.COL_VAR_PACOTE].round(4) > 0).fillna(False), tx.COL_VAR_PACOTE] = f"color:{VERMELHO};font-weight:700"
    return cru, txt.style.apply(lambda _: est, axis=None)


def _secao(base, regional, freq, ini, fim, export):
    st.subheader(tx.RES_SECAO)
    df = resumo(base, freq, regional, ini, fim)
    if df.empty or df["viagens"].sum() == 0:
        st.info(tx.RES_SEM_DADOS)
        return
    f, p, k = float(df["frete"].sum()), float(df["pacotes"].sum()), float(df["km"].sum())
    ultimo = df.dropna(subset=["frete_pacote"]).iloc[-1] if df["frete_pacote"].notna().any() else None
    c1, c2, c3, c4, c5 = st.columns([1, 1.7, 1.2, 1.2, 1.4])
    c1.metric(tx.COL_VIAGENS, inteiro(df["viagens"].sum()))
    c2.metric(tx.COL_FRETE, brl(f))
    c3.metric(tx.COL_FRETE_PACOTE, brl(f / p if p else float("nan")))
    c4.metric(tx.COL_FRETE_KM, brl(f / k if k else float("nan")))
    if ultimo is not None:
        delta = variacao(ultimo["variacao"]).replace("▲ ", "").replace("▼ ", "")
        c5.metric(f"{tx.RES_ULTIMO} · {ultimo['periodo']}", brl(ultimo["frete_pacote"]),
                  None if delta == "–" else delta, delta_color="off")

    g1, g2 = st.columns(2)
    with g1:
        st.caption(tx.RES_GRAF_REG)
        tab = tabela_periodo(base, ini, fim).iloc[1:]
        tab = tab[tab["viagens"] > 0]
        if regional:
            tab = tab[tab["regiao"] == regional]
        st.plotly_chart(_g_barras(tab, "regiao"), width="stretch", theme="streamlit", key="cures_g_reg")
    with g2:
        st.caption(tx.RES_GRAF_VEIC)
        st.plotly_chart(_g_barras(por_veiculo(base, ini, fim, regional), "veiculo"), width="stretch", theme="streamlit",
                        key="cures_g_vei")
    st.caption(tx.RES_GRAF_TEND)
    st.plotly_chart(_g_linha(df), width="stretch", theme="streamlit", key="cures_g_lin")
    if df["frete_pacote"].isna().any():
        st.caption(tx.RES_LACUNA)

    cru, estilizada = _tabela(df)
    with st.expander(tx.RES_TABELA):
        st.dataframe(estilizada, width="stretch", hide_index=True, height=min((len(cru) + 1) * 35 + 3, 420))
    exp = cru.copy()
    exp[tx.COL_VAR_PACOTE] = exp[tx.COL_VAR_PACOTE] * 100
    export[tx.RES_SECAO[:31]] = (exp, {"custos": True, "pp_extra": [tx.COL_VAR_PACOTE]})


def mostrar(base: pd.DataFrame, export: dict, dia=None) -> None:
    st.caption(tx.RES_NOTA)
    anos = sorted(base["dia"].dt.year.unique(), reverse=True)
    opcoes_ano = anos + [None]
    atual = datetime.now().year
    opcao_valida("cures_ano", opcoes_ano)
    opcoes_reg = ["*"] + regioes_da(base)
    opcao_valida("cures_reg", opcoes_reg)
    f1, f2, f3 = st.columns(3)
    regional = f1.selectbox(tx.RES_REGIONAL, opcoes_reg, key="cures_reg",
                            format_func=lambda r: tx.RES_TODAS if r == "*" else r)
    regional = None if regional == "*" else regional
    freq = f2.radio(tx.RES_VISAO, VISOES, index=1, horizontal=True, key="cures_vis", format_func=lambda g: tx.GRAN_NOMES[g])
    ano = f3.selectbox(tx.RES_ANO, opcoes_ano, index=anos.index(atual) if atual in anos else 0, key="cures_ano",
                       format_func=lambda a: tx.RES_TODO_HISTORICO if a is None else str(a))
    ini, fim = (None, None) if ano is None else (pd.Timestamp(year=ano, month=1, day=1), pd.Timestamp(year=ano, month=12, day=31))
    freq, ini, fim = _botoes(base, freq, ini, fim)
    ini, fim = resumo_dia.aplicar(freq, ini, fim, dia)
    _secao(base, regional, freq, ini, fim, export)
