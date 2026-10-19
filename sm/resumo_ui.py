"""Aba Resumo do SM: cobertura por regional (barras vermelho + cinza) e mini-gráficos por regional (Plotly).

Pensado para mostrar "onde está o buraco" em vez de repetir a linha e as barras de volume do Lacre/Deslacre.
"""
from datetime import datetime

import pandas as pd
import streamlit as st

from comum import periodos
from comum.estilos import pct, pp
from comum.graficos_plotly import cobertura, mini_graficos
from comum.tema import CINZA_DESTAQUE, VERMELHO
from comum.uploads import opcao_valida
from . import textos as tx
from .calculos import regioes_da, resumo, resumo_regionais, tabela_periodo
from .config import TIPOS

VISOES = ("D", "W", "M")


def _tabela(df: pd.DataFrame):
    """(tabela crua para exportar, tabela estilizada para a tela). Total do ano na 1ª linha, em cinza."""
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


def _secao(base, tipo, regional, freq, per, ini_ano, fim_ano, export):
    """per = semana/mês clicado (os gráficos passam a mostrar os dias dele); None = o ano inteiro em `freq`."""
    st.subheader(tx.subtitulo_resumo(tipo))
    if per is None:
        ini_p, fim_p, freq_g = ini_ano, fim_ano, freq
    else:
        ini_p, fim_p, freq_g = per, periodos.fim(per, freq), "D"
    tab = tabela_periodo(base, tipo, ini_p, fim_p)
    total, regs = tab.iloc[0], tab.iloc[1:]
    if regional:                                           # uma regional só: o "total" passa a ser o dela
        regs = regs[regs["regiao"] == regional]
        if regs.empty:
            st.info(tx.RES_SEM_DADOS)
            return
        total = regs.iloc[0]
    if total["prev"] == 0:
        st.info(tx.RES_SEM_DADOS)
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(tx.COL_PREV, f"{int(total['prev']):,}".replace(",", "."))
    c2.metric(tx.COL_REAL, f"{int(total['real']):,}".replace(",", "."))
    c3.metric(tx.COL_TAXA, pct(total["taxa"]))
    if per is not None:
        ant = periodos.anterior(per, freq)
        tab_ant = tabela_periodo(base, tipo, ant, periodos.fim(ant, freq))
        t_ant = (tab_ant[tab_ant["regiao"] == regional] if regional else tab_ant.iloc[[0]])["taxa"].iloc[0]
        delta = "" if pd.isna(t_ant) or pd.isna(total["taxa"]) else pp(total["taxa"] - t_ant).replace("▲ ", "").replace("▼ ", "")
        c4.metric(f"{tx.COMP_LEGENDA}: {periodos.rotulo_curto(ant, freq)}", pct(t_ant), delta or None, delta_color="off")
    else:
        c4.metric(tx.RES_FALTAM, f"{int(total['prev'] - total['real']):,}".replace(",", "."))

    st.markdown(f"**{tx.RES_COBERTURA}**")
    ordenada = regs[regs["prev"] > 0].sort_values("taxa", ascending=False)
    st.plotly_chart(cobertura(ordenada, tx.COL_REAL, tx.RES_FALTAM), width="stretch", theme="streamlit",
                    config={"displayModeBar": False}, key=f"smres_cob_{tipo}")

    st.markdown(f"**{tx.RES_MINI}**")
    rr = resumo_regionais(base, tipo, freq_g, ini_p, fim_p)
    if regional:
        rr = rr[rr["regiao"] == regional]
    ordem = list(dict.fromkeys(rr["periodo"]))
    st.plotly_chart(mini_graficos(rr, list(dict.fromkeys(rr["regiao"])), ordem, tx.RES_GRAF_TAXA), width="stretch",
                    theme="streamlit", config={"displayModeBar": False}, key=f"smres_mini_{tipo}")
    if rr["taxa"].isna().any():
        st.caption(tx.RES_LACUNA)

    serie = resumo(base, tipo, freq_g, regional, ini_p, fim_p)
    cru, estilizada = _tabela(serie)
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
    todas = regioes_da(base)
    opcoes_reg = ["*"] + todas                       # "*" = todas (None viraria o texto "Choose an option")
    opcao_valida("smres_reg", opcoes_reg)
    f0, f1, f2 = st.columns(3)
    regional = f0.selectbox(tx.RES_REGIONAL, opcoes_reg, key="smres_reg",
                            format_func=lambda r: tx.RES_TODAS if r == "*" else r)
    regional = None if regional == "*" else regional
    atual = datetime.now().year
    ano = f1.selectbox(tx.RES_ANO, opcoes_ano, index=anos.index(atual) if atual in anos else 0, key="smres_ano",
                       format_func=lambda a: tx.RES_TODO_HISTORICO if a is None else str(a))
    freq = f2.radio(tx.RES_VISAO, VISOES, index=1, horizontal=True, key="smres_vis",
                    format_func=lambda g: tx.GRAN_NOMES[g])
    sub = base if ano is None else base[base["dia"].dt.year == ano]
    ini_ano, fim_ano = (None, None) if ano is None else (pd.Timestamp(year=ano, month=1, day=1),
                                                         pd.Timestamp(year=ano, month=12, day=31))
    per = None
    if freq != "D":      # Semana ou Mês: botões clicáveis; em Dia nada aparece
        lista = periodos.lista(sub["dia"], freq)
        if lista:
            chave = f"smres_pil_{freq}"
            opcao_valida(chave, lista)
            st.caption(tx.RES_PILULA_W if freq == "W" else tx.RES_PILULA_M)
            per = st.pills(tx.GRAN_NOMES[freq], lista, selection_mode="single", default=lista[-1], key=chave,
                           format_func=lambda p: periodos.rotulo_curto(p, freq, com_ano=ano is None))
            if per is not None:
                st.caption(f"{tx.RES_DIAS_DE}: {periodos.rotulo(per, freq)}")
    for tipo in TIPOS:
        _secao(base, tipo, regional, freq, per, ini_ano, fim_ano, export)
