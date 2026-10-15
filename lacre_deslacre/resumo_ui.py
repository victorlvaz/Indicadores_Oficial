"""Aba Resumo: totais, taxa e gráficos por dia, semana ou mês, com filtro de regional."""
from datetime import datetime

import pandas as pd
import streamlit as st

from comum.estilos import pct, pp
from comum.graficos import grafico_taxa, grafico_volume
from comum.tema import CINZA_DESTAQUE, CSS_ABAIXO_META, VERMELHO
from comum import periodos
from comum.uploads import opcao_valida
from . import textos as tx
from comum.idioma import bi
from .calculos import regionais, resumo
from .config import INDICADORES, METAS, ROTULOS

VISOES = ("D", "W", "M")


def _tabela(df: pd.DataFrame, rot: dict, meta: float):
    """(tabela crua para exportar, tabela estilizada para a tela). Total do período na 1ª linha, em cinza."""
    prev, real = int(df["prev"].sum()), int(df["real"].sum())
    total = {tx.RES_PERIODO: "合计 Total", rot["prev"]: prev, rot["real"]: real,
             rot["taxa"]: real / prev if prev else float("nan"), "目标 Meta": meta, tx.COL_VAR: float("nan")}
    corpo = pd.DataFrame({
        tx.RES_PERIODO: df["periodo"], rot["prev"]: df["prev"], rot["real"]: df["real"],
        rot["taxa"]: df["taxa"], "目标 Meta": meta, tx.COL_VAR: df["variacao"]})
    cru = pd.concat([pd.DataFrame([total]), corpo.iloc[::-1]], ignore_index=True)   # mais recente primeiro

    txt = cru.copy()
    txt[rot["taxa"]] = cru[rot["taxa"]].map(pct)
    txt["目标 Meta"] = cru["目标 Meta"].map(pct)
    txt[tx.COL_VAR] = cru[tx.COL_VAR].map(pp)
    est = pd.DataFrame("", index=txt.index, columns=txt.columns)
    est.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    est.loc[(cru[rot["taxa"]] < meta).fillna(False), rot["taxa"]] = CSS_ABAIXO_META
    est.loc[(cru[tx.COL_VAR].round(4) < 0).fillna(False), tx.COL_VAR] = f"color:{VERMELHO};font-weight:700"
    return cru, txt.style.apply(lambda _: est, axis=None)


def _secao(base, tipo, evento, regional, freq, ini, fim, export):
    cfg, rot, meta = INDICADORES[(tipo, evento)], ROTULOS[evento], METAS[evento]
    st.subheader(tx.subtitulo_resumo(tipo, evento))
    df = resumo(base, tipo, evento, freq, regional, ini, fim)
    if df.empty or df["prev"].sum() == 0:
        st.info(tx.RES_SEM_DADOS)
        return
    prev, real = int(df["prev"].sum()), int(df["real"].sum())
    taxa = real / prev
    validos = df.dropna(subset=["taxa"])
    ultimo = validos.iloc[-1]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(rot["prev"], f"{prev:,}".replace(",", "."))
    c2.metric(rot["real"], f"{real:,}".replace(",", "."))
    dif = f"{(taxa - meta) * 100:+.2f}".replace(".", ",")
    c3.metric(rot["taxa"], pct(taxa), f"{dif} p.p. {tx.RES_VS_META}", delta_color="off")
    delta = "" if pd.isna(ultimo["variacao"]) else pp(ultimo["variacao"]).replace("▲ ", "").replace("▼ ", "")
    c4.metric(f"{tx.RES_ULTIMO} · {ultimo['periodo']}", pct(ultimo["taxa"]), delta or None, delta_color="off")

    ordem = list(df["periodo"])
    g1, g2 = st.columns(2)
    with g1:
        st.altair_chart(grafico_taxa(df, ordem, meta, pequeno=len(df) > 60, titulo_y=tx.RES_GRAF_TAXA,
                                     titulo_periodo=tx.RES_PERIODO, titulo_taxa=tx.RES_GRAF_TAXA), width="stretch")
    with g2:
        st.altair_chart(grafico_volume(df, ordem, rot["prev"], rot["real"], tx.RES_GRAF_VOL, tx.RES_PERIODO),
                        width="stretch")
    if df["taxa"].isna().any():
        st.caption(tx.RES_LACUNA)

    cru, estilizada = _tabela(df, rot, meta)
    with st.expander(tx.RES_TABELA):
        st.dataframe(estilizada, width="stretch", hide_index=True, height=min((len(cru) + 1) * 35 + 3, 420))
    exp = cru.copy()
    exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100
    export[tx.aba_excel_resumo(tipo, evento)] = (exp, {"taxa": rot["taxa"], "meta": "目标 Meta", "pp_extra": [tx.COL_VAR]})


def _botoes(base: pd.DataFrame, freq: str, ini, fim):
    """Semana ou Mês: mostra os botões de períodos. Clicar em um passa a mostrar os DIAS dele; sem seleção, o ano todo
    por semana/mês. Em Dia não há botões (nada aparece na tela)."""
    if freq == "D":
        return freq, ini, fim
    sub = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    lista = periodos.lista(sub["dia"], freq)
    if not lista:
        return freq, ini, fim
    chave = f"res_pil_{freq}"
    opcao_valida(chave, lista)
    st.caption(tx.RES_PILULA_W if freq == "W" else tx.RES_PILULA_M)
    per = st.pills(tx.GRAN_NOMES[freq], lista, selection_mode="single", default=lista[-1], key=chave,
                   format_func=lambda p: periodos.rotulo_curto(p, freq, com_ano=ini is None))
    if per is None:
        return freq, ini, fim
    st.caption(f"{tx.RES_DIAS_DE}: {periodos.rotulo(per, freq)}")
    return "D", per, periodos.fim(per, freq)


def mostrar(base: pd.DataFrame, export: dict) -> None:
    """Desenha a aba inteira. Lacre primeiro, depois Deslacre; cada um com Coleta e Entrega."""
    st.caption(tx.RES_NOTA)
    anos = sorted(base["dia"].dt.year.unique(), reverse=True)
    opcoes_ano = anos + [None]
    atual = datetime.now().year
    opcao_valida("res_ano", opcoes_ano)

    todas = sorted({r for t, e in INDICADORES for r in regionais(base, t, e)})
    opcoes_reg = ["*"] + todas            # "*" = todas (None viraria o texto "Choose an option")
    opcao_valida("res_reg", opcoes_reg)

    f1, f2, f3 = st.columns([1, 1, 1])
    regional = f1.selectbox(tx.RES_REGIONAL, opcoes_reg, key="res_reg",
                            format_func=lambda r: tx.RES_TODAS if r == "*" else r)
    regional = None if regional == "*" else regional
    freq = f2.radio(tx.RES_VISAO, VISOES, index=1, horizontal=True, key="res_vis",
                    format_func=lambda g: tx.GRAN_NOMES[g])
    ano = f3.selectbox(tx.RES_ANO, opcoes_ano, index=anos.index(atual) if atual in anos else 0, key="res_ano",
                       format_func=lambda a: tx.RES_TODO_HISTORICO if a is None else str(a))
    ini, fim = (None, None) if ano is None else (pd.Timestamp(year=ano, month=1, day=1), pd.Timestamp(year=ano, month=12, day=31))
    freq, ini, fim = _botoes(base, freq, ini, fim)

    for evento in ("lacre", "deslacre"):
        st.header(bi("封车", "Lacre") if evento == "lacre" else bi("解车", "Deslacre"))
        for tipo in ("COLETA", "ENTREGA"):
            _secao(base, tipo, evento, regional, freq, ini, fim, export)
