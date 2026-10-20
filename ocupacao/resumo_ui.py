"""Aba Resumo da Taxa de Ocupação: bolhas por regional (viagens × ocupação), barras por tipo de veículo e linha por período."""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comum import periodos, resumo_dia
from comum.estilos import pct, pp
from comum.tema import CINZA_DESTAQUE, VERMELHO
from comum.uploads import opcao_valida
from . import textos as tx
from .calculos import por_veiculo, regionais, resumo, tabela_periodo
from .config import INDICADORES

VISOES = ("D", "W", "M")
CINZA = "#8C8C8C"
GRADE = "rgba(128,128,128,.25)"


def _botoes(base, freq, ini, fim):
    if freq == "D":
        return freq, ini, fim
    sub = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    lista = periodos.lista(sub["dia"], freq)
    if not lista:
        return freq, ini, fim
    chave = f"ocres_pil_{freq}"
    opcao_valida(chave, lista)
    st.caption(tx.RES_PILULA_W if freq == "W" else tx.RES_PILULA_M)
    per = st.pills(tx.GRAN_NOMES[freq], lista, selection_mode="single", default=lista[-1], key=chave,
                   format_func=lambda p: periodos.rotulo_curto(p, freq, com_ano=ini is None))
    if per is None:
        return freq, ini, fim
    st.caption(f"{tx.RES_DIAS_DE}: {periodos.rotulo(per, freq)}")
    return "D", per, periodos.fim(per, freq)


# Uma cor fixa por regional (sem vermelho), para a mesma regional ter a mesma cor em Coleta e Entrega
CORES_REGIAO = {"SPE": "#1F77B4", "SPS": "#2CA02C", "SPN": "#FF7F0E", "RJ": "#9467BD", "MG": "#17BECF",
                "PR": "#BCBD22", "CE": "#8C564B", "BA": "#E377C2", "GP": "#4D6A8F", "SR": "#7F7F7F"}
_EXTRAS = ["#393B79", "#637939", "#8C6D31", "#843C39", "#5254A3"]


def _g_rosca(tab):
    """Uma rosca por regional: a parte colorida é a ocupação da PRÓPRIA regional (carregado / capacidade), o resto é cinza."""
    t = tab[tab["prev"] > 0].reset_index(drop=True)
    n = len(t)
    colunas = 5
    linhas = max((n + colunas - 1) // colunas, 1)
    fig = go.Figure()
    anot = []
    larg, alto = 1 / colunas, 1 / linhas
    for i, r in t.iterrows():
        cor = CORES_REGIAO.get(r["regiao"]) or _EXTRAS[i % len(_EXTRAS)]
        c, l = i % colunas, i // colunas
        x0, x1 = c * larg + 0.01, (c + 1) * larg - 0.01
        y1 = 1 - l * alto - 0.12 / linhas
        y0 = 1 - (l + 1) * alto + 0.10 / linhas
        taxa = 0.0 if pd.isna(r["taxa"]) else float(r["taxa"])
        fig.add_trace(go.Pie(
            values=[taxa, 1 - taxa], hole=0.74, sort=False, direction="clockwise", rotation=0, textinfo="none",
            marker=dict(colors=[cor, "#E3E3E3"], line=dict(color="#FFFFFF", width=1)), showlegend=False,
            domain=dict(x=[x0, x1], y=[y0, y1]), name=r["regiao"],
            hovertemplate=f"{r['regiao']}<br>" + tx.COL_TAXA + f": {taxa:.1%}<br>" + tx.COL_VIAGENS + f": {int(r['viagens'])}<extra></extra>"))
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        anot.append(dict(text=f"<b>{taxa * 100:.0f}%</b>", x=xm, y=ym, showarrow=False, font=dict(size=13)))
        anot.append(dict(text=f"<b>{r['regiao']}</b> · {int(r['viagens'])}", x=xm, y=y0 - 0.02 / linhas, yanchor="top",
                         showarrow=False, font=dict(size=12)))
    fig.update_layout(height=200 * linhas + 40, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, annotations=anot)
    return fig


def _g_veiculo(v):
    v = v.dropna(subset=["taxa"]).sort_values("viagens")
    fig = go.Figure(go.Bar(
        y=v["veiculo"], x=v["taxa"], orientation="h", marker_color=CINZA,
        text=[f"{t * 100:.0f}% · {n}" for t, n in zip(v["taxa"], v["viagens"])], textposition="outside",
        hovertemplate="%{y}<br>" + tx.COL_TAXA + ": %{x:.1%}<extra></extra>"))
    fig.update_layout(height=70 + 28 * max(len(v), 1), margin=dict(l=10, r=40, t=10, b=20), showlegend=False,
                      xaxis=dict(tickformat=".0%", range=[0, 1.25], gridcolor=GRADE, zeroline=False),
                      yaxis=dict(type="category"))
    return fig


def _g_linha(df):
    fig = go.Figure(go.Scatter(x=list(df["periodo"]), y=df["taxa"], mode="lines+markers", connectgaps=False,
                               line=dict(color=CINZA, width=2), marker=dict(color=VERMELHO, size=8),
                               hovertemplate="%{x}<br>" + tx.COL_TAXA + ": %{y:.1%}<extra></extra>"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=30), showlegend=False,
                      xaxis=dict(type="category", gridcolor=GRADE), yaxis=dict(tickformat=".0%", gridcolor=GRADE, range=[0, 1.05]))
    return fig


def _tabela(df):
    prev, real = float(df["prev"].sum()), float(df["real"].sum())
    total = {tx.RES_PERIODO: "合计 Total", tx.COL_VIAGENS: int(df["viagens"].sum()), tx.COL_PREV: prev, tx.COL_REAL: real,
             tx.COL_TAXA: min(real / prev, 1.0) if prev else float("nan"), tx.COL_VAR: float("nan")}
    corpo = pd.DataFrame({tx.RES_PERIODO: df["periodo"], tx.COL_VIAGENS: df["viagens"], tx.COL_PREV: df["prev"],
                          tx.COL_REAL: df["real"], tx.COL_TAXA: df["taxa"], tx.COL_VAR: df["variacao"]})
    cru = pd.concat([pd.DataFrame([total]), corpo.iloc[::-1]], ignore_index=True)
    txt = cru.copy()
    txt[tx.COL_PREV] = cru[tx.COL_PREV].map(lambda v: f"{v:,.0f}".replace(",", "."))
    txt[tx.COL_REAL] = cru[tx.COL_REAL].map(lambda v: f"{v:,.0f}".replace(",", "."))
    txt[tx.COL_TAXA], txt[tx.COL_VAR] = cru[tx.COL_TAXA].map(pct), cru[tx.COL_VAR].map(pp)
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
    prev, real = float(df["prev"].sum()), float(df["real"].sum())
    ultimo = df.dropna(subset=["taxa"]).iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(tx.COL_VIAGENS, f"{int(df['viagens'].sum()):,}".replace(",", "."))
    c2.metric(tx.COL_REAL, f"{real:,.0f}".replace(",", "."))
    c3.metric(tx.COL_TAXA, pct(min(real / prev, 1.0)))
    delta = "" if pd.isna(ultimo["variacao"]) else pp(ultimo["variacao"]).replace("▲ ", "").replace("▼ ", "")
    c4.metric(f"{tx.RES_ULTIMO} · {ultimo['periodo']}", pct(ultimo["taxa"]), delta or None, delta_color="off")

    g1, g2 = st.columns(2)
    with g1:
        st.caption(tx.RES_GRAF_REG)
        tab = tabela_periodo(base, tipo, ini, fim).iloc[1:]
        tab = tab[tab["prev"] > 0]
        if regional:
            tab = tab[tab["regiao"] == regional]
        st.plotly_chart(_g_rosca(tab), width="stretch", theme="streamlit", key=f"ocres_bol_{tipo}")
        st.caption(tx.RES_GRAF_AJUDA)
    with g2:
        st.caption(tx.RES_GRAF_VEIC)
        st.plotly_chart(_g_veiculo(por_veiculo(base, tipo, ini, fim, regional)), width="stretch", theme="streamlit",
                        key=f"ocres_vei_{tipo}")
    st.caption(tx.RES_GRAF_TEND)
    st.plotly_chart(_g_linha(df), width="stretch", theme="streamlit", key=f"ocres_lin_{tipo}")
    if df["taxa"].isna().any():
        st.caption(tx.RES_LACUNA)

    cru, estilizada = _tabela(df)
    with st.expander(tx.RES_TABELA):
        st.dataframe(estilizada, width="stretch", hide_index=True, height=min((len(cru) + 1) * 35 + 3, 420))
    exp = cru.copy()
    exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100
    export[tx.aba_excel_resumo(tipo)] = (exp, {"taxa": tx.COL_TAXA, "pp_extra": [tx.COL_VAR]})


def mostrar(base: pd.DataFrame, export: dict, dia=None) -> None:
    st.caption(tx.RES_NOTA)
    anos = sorted(base["dia"].dt.year.unique(), reverse=True)
    opcoes_ano = anos + [None]
    atual = datetime.now().year
    opcao_valida("ocres_ano", opcoes_ano)
    todas = sorted({r for t in INDICADORES for r in regionais(base, t)})
    opcoes_reg = ["*"] + todas
    opcao_valida("ocres_reg", opcoes_reg)
    f1, f2, f3 = st.columns(3)
    regional = f1.selectbox(tx.RES_REGIONAL, opcoes_reg, key="ocres_reg",
                            format_func=lambda r: tx.RES_TODAS if r == "*" else r)
    regional = None if regional == "*" else regional
    freq = f2.radio(tx.RES_VISAO, VISOES, index=1, horizontal=True, key="ocres_vis", format_func=lambda g: tx.GRAN_NOMES[g])
    ano = f3.selectbox(tx.RES_ANO, opcoes_ano, index=anos.index(atual) if atual in anos else 0, key="ocres_ano",
                       format_func=lambda a: tx.RES_TODO_HISTORICO if a is None else str(a))
    ini, fim = (None, None) if ano is None else (pd.Timestamp(year=ano, month=1, day=1), pd.Timestamp(year=ano, month=12, day=31))
    freq, ini, fim = _botoes(base, freq, ini, fim)
    ini, fim = resumo_dia.aplicar(freq, ini, fim, dia)
    for tipo in ("COLETA", "ENTREGA"):
        _secao(base, tipo, regional, freq, ini, fim, export)
