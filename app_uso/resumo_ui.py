"""Aba Resumo da Taxa de Uso de APP: ranking contra a meta + mapa de calor regional x período."""
from datetime import datetime

import pandas as pd
import streamlit as st

from comum import periodos, resumo_dia
from comum.estilos import pct, pp
from comum.graficos_plotly import mapa_calor, ranking_meta
from comum.tema import CINZA_DESTAQUE, CSS_ABAIXO_META, VERDE, VERMELHO
from comum.uploads import opcao_valida
from . import textos as tx
from .calculos import regionais, resumo, resumo_regionais, tabela_periodo
from .config import INDICADORES, META

VISOES = ("D", "W", "M")


def _botoes(base, freq, ini, fim):
    """Semana ou Mês: botões de períodos; clicar mostra os DIAS dele. Em Dia não aparece nada."""
    if freq == "D":
        return freq, ini, fim
    sub = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    lista = periodos.lista(sub["dia"], freq)
    if not lista:
        return freq, ini, fim
    chave = f"appres_pil_{freq}"
    opcao_valida(chave, lista)
    st.caption(tx.RES_PILULA_W if freq == "W" else tx.RES_PILULA_M)
    per = st.pills(tx.GRAN_NOMES[freq], lista, selection_mode="single", default=lista[-1], key=chave,
                   format_func=lambda p: periodos.rotulo_curto(p, freq, com_ano=ini is None))
    if per is None:
        return freq, ini, fim
    st.caption(f"{tx.RES_DIAS_DE}: {periodos.rotulo(per, freq)}")
    return "D", per, periodos.fim(per, freq)


def _tabela(df):
    prev, real = int(df["prev"].sum()), int(df["real"].sum())
    total = {tx.RES_PERIODO: "合计 Total", tx.COL_PREV: prev, tx.COL_REAL: real,
             tx.COL_TAXA: real / prev if prev else float("nan"), "目标 Meta": META, tx.COL_VAR: float("nan")}
    corpo = pd.DataFrame({tx.RES_PERIODO: df["periodo"], tx.COL_PREV: df["prev"], tx.COL_REAL: df["real"],
                          tx.COL_TAXA: df["taxa"], "目标 Meta": META, tx.COL_VAR: df["variacao"]})
    cru = pd.concat([pd.DataFrame([total]), corpo.iloc[::-1]], ignore_index=True)
    txt = cru.copy()
    txt[tx.COL_TAXA], txt["目标 Meta"], txt[tx.COL_VAR] = cru[tx.COL_TAXA].map(pct), cru["目标 Meta"].map(pct), cru[tx.COL_VAR].map(pp)
    est = pd.DataFrame("", index=txt.index, columns=txt.columns)
    est.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    est.loc[(cru[tx.COL_TAXA] < META).fillna(False), tx.COL_TAXA] = CSS_ABAIXO_META
    est.loc[(cru[tx.COL_VAR].round(4) < 0).fillna(False), tx.COL_VAR] = f"color:{VERMELHO};font-weight:700"
    est.loc[(cru[tx.COL_VAR].round(4) > 0).fillna(False), tx.COL_VAR] = f"color:{VERDE};font-weight:700"
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
    c3.metric(tx.COL_TAXA, pct(taxa), f"{(taxa - META) * 100:+.2f}".replace(".", ",") + f" p.p. {tx.RES_VS_META}", delta_color="off")
    delta = "" if pd.isna(ultimo["variacao"]) else pp(ultimo["variacao"]).replace("▲ ", "").replace("▼ ", "")
    c4.metric(f"{tx.RES_ULTIMO} · {ultimo['periodo']}", pct(ultimo["taxa"]), delta or None, delta_color="off")

    g1, g2 = st.columns([2, 3])
    with g1:
        st.caption(tx.RES_GRAF_RANK)
        tab = tabela_periodo(base, tipo, ini, fim).iloc[1:]
        tab = tab[tab["prev"] > 0]
        if regional:
            tab = tab[tab["regiao"] == regional]
        st.plotly_chart(ranking_meta(tab, META, tx.COL_TAXA), width="stretch", theme="streamlit",
                        key=f"app_rank_{tipo}")
    with g2:
        st.caption(tx.RES_GRAF_CALOR)
        long = resumo_regionais(base, tipo, freq, ini, fim)
        regs = [r for r in regionais(base, tipo) if r in set(long["regiao"])]
        if regional:
            regs = [r for r in regs if r == regional]
        ordem = list(df["periodo"])
        st.plotly_chart(mapa_calor(long, regs, ordem, META, tx.COL_TAXA), width="stretch", theme="streamlit",
                        key=f"app_calor_{tipo}")
        st.caption(tx.RES_CALOR_AJUDA)
    if df["taxa"].isna().any():
        st.caption(tx.RES_LACUNA)

    cru, estilizada = _tabela(df)
    with st.expander(tx.RES_TABELA):
        st.dataframe(estilizada, width="stretch", hide_index=True, height=min((len(cru) + 1) * 35 + 3, 420))
    exp = cru.copy()
    exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100


def mostrar(base: pd.DataFrame, export: dict, dia=None) -> None:
    st.caption(tx.RES_NOTA)
    anos = sorted(base["dia"].dt.year.unique(), reverse=True)
    opcoes_ano = anos + [None]
    atual = datetime.now().year
    opcao_valida("appres_ano", opcoes_ano)
    todas = sorted({r for t in INDICADORES for r in regionais(base, t)})
    opcoes_reg = ["*"] + todas
    opcao_valida("appres_reg", opcoes_reg)

    f1, f2, f3 = st.columns(3)
    regional = f1.selectbox(tx.RES_REGIONAL, opcoes_reg, key="appres_reg",
                            format_func=lambda r: tx.RES_TODAS if r == "*" else r)
    regional = None if regional == "*" else regional
    freq = f2.radio(tx.RES_VISAO, VISOES, index=1, horizontal=True, key="appres_vis", format_func=lambda g: tx.GRAN_NOMES[g])
    ano = f3.selectbox(tx.RES_ANO, opcoes_ano, index=anos.index(atual) if atual in anos else 0, key="appres_ano",
                       format_func=lambda a: tx.RES_TODO_HISTORICO if a is None else str(a))
    ini, fim = (None, None) if ano is None else (pd.Timestamp(year=ano, month=1, day=1), pd.Timestamp(year=ano, month=12, day=31))
    freq, ini, fim = _botoes(base, freq, ini, fim)
    ini, fim = resumo_dia.aplicar(freq, ini, fim, dia)
    for tipo in ("COLETA", "ENTREGA"):
        _secao(base, tipo, regional, freq, ini, fim, export)
