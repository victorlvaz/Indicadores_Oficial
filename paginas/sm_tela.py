"""Página: SM状态统计 / Estatística de Status dos SMs (Coleta e Entrega + extração do TECHIS)."""
import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from comum.exportar import para_excel
from comum.estilos import estilizar_tendencia, pct
from comum.idioma import cabecalho, rodape
from comum.uploads import manter, opcao_valida, upload_persistente
from comum.sparkline import tabela_tendencia_html
from comum.tema import CINZA_DESTAQUE, CSS_ABAIXO_META, VERMELHO
from sm import textos as tx
from sm.calculos import (aplicar_techis, base_para_exportar, carregar_apoio, colunas_internas, contagem_techis,
                         df_para_xlsx, embarque_com_espaco, filtrar_techis, juntar, ler_historico, ler_planilha,
                         ler_techis, pendentes, preparar_jms, rotular_tabela, tabela_dia, techis_ligado,
                         tendencia)
from sm.config import COL_TECHIS_EMBARQUE, LIMITAR_REALIZADO, META, REGIOES, TIPOS

cabecalho(*tx.PAGINA)


# ---------- leitura (em cache: trocar de aba ou de dia não relê os arquivos) ----------
@st.cache_data(show_spinner=False)
def _ler_jms(conteudo: bytes, nome: str) -> pd.DataFrame:
    import io
    arq = io.BytesIO(conteudo)
    arq.name = nome
    return ler_planilha(arq)


@st.cache_data(show_spinner=False)
def _ler_techis(conteudo: bytes, nome: str) -> pd.DataFrame:
    import io
    arq = io.BytesIO(conteudo)
    arq.name = nome
    return ler_techis(arq)


@st.cache_data(show_spinner=False)
def _ler_historico(conteudo: bytes) -> dict:
    import io
    return ler_historico(io.BytesIO(conteudo))


@st.cache_data(show_spinner=False)
def _excel(abas: dict) -> bytes:
    return para_excel(abas)


def _estilizar(tab: pd.DataFrame):
    """Percentual com 2 casas e vírgula, linha de total (1ª) em cinza; vermelho só se houver meta."""
    txt = tab.copy()
    txt[tx.COL_TAXA] = tab[tx.COL_TAXA].map(pct)
    txt[tx.COL_RANK] = tab[tx.COL_RANK].map(lambda v: "–" if pd.isna(v) else str(int(v)))
    estilos = pd.DataFrame("", index=txt.index, columns=txt.columns)
    estilos.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    if META is not None:
        estilos.loc[(tab[tx.COL_TAXA] < META).fillna(False), tx.COL_TAXA] = CSS_ABAIXO_META
    return txt.style.apply(lambda _: estilos, axis=None)


def _alinhar_direita(*colunas):
    try:
        return {c: st.column_config.TextColumn(alignment="right") for c in colunas}
    except TypeError:
        return {}


def _grafico(tab: pd.DataFrame):
    """Barras horizontais do rastreamento efetivo por regional (só vermelho, sem verde)."""
    d = tab[tab["regiao"] != tx.TOTAL].dropna(subset=["taxa"]).copy()
    if d.empty:
        return None
    d["rotulo"] = d["taxa"].map(pct)
    d["detalhe"] = d["real"].astype(str) + " / " + d["prev"].astype(str)
    ordem = d["regiao"].tolist()
    base = alt.Chart(d).encode(
        y=alt.Y("regiao:N", sort=ordem, title=None),
        x=alt.X("taxa:Q", scale=alt.Scale(domain=[0, 1.12]), axis=alt.Axis(format="%", title=None)),
        tooltip=[alt.Tooltip("regiao:N", title=tx.COL_REGIAO), alt.Tooltip("detalhe:N", title="SM"),
                 alt.Tooltip("rotulo:N", title=tx.COL_TAXA)])
    barras = base.mark_bar(color=VERMELHO, cornerRadiusEnd=3, height=22)
    textos = base.mark_text(align="left", dx=4, fontWeight="bold").encode(text="rotulo:N")
    total = tab.loc[tab["regiao"] == tx.TOTAL, "taxa"].iloc[0]
    camadas = [barras, textos]
    if pd.notna(total):
        camadas.append(alt.Chart(pd.DataFrame({"t": [total]})).mark_rule(strokeDash=[4, 3], color="gray")
                       .encode(x="t:Q"))
    return alt.layer(*camadas).properties(height=40 * len(d) + 20)


# ---------- Entrada ----------
manter("sm_f_status", "sm_f_sc", "sm_f_coleta", "sm_f_franq", "sm_f_pedido", "sm_f_techis_status", "sm_f_limite",
       "sm_dia", "sm_n_dias", "sm_escala", "sm_x_techis")      # não perder filtros ao trocar de relatório
# os arquivos enviados ficam guardados ao trocar de relatório (saem com ✕ ou ao desligar o servidor)
up = {
    "COLETA": upload_persistente("sm_coleta", tx.UP_COLETA, ["xls", "xlsx", "csv"], tx.UP_AJUDA_JMS),
    "ENTREGA": upload_persistente("sm_entrega", tx.UP_ENTREGA, ["xls", "xlsx", "csv"], tx.UP_AJUDA_JMS),
}
up_techis = upload_persistente("sm_techis", tx.UP_TECHIS, ["xls", "xlsx", "csv"], tx.UP_AJUDA_TECHIS)
up_hist = upload_persistente("sm_hist", tx.UP_HIST, ["xlsx"], tx.UP_AJUDA_HIST)

if not (up["COLETA"] or up["ENTREGA"] or up_techis or up_hist):
    st.info(tx.INFO_SEM_ARQUIVO)
    st.stop()

st.sidebar.header(tx.REGRAS)
f_status = st.sidebar.checkbox(tx.R_STATUS, value=True, key="sm_f_status")
f_sc = st.sidebar.checkbox(tx.R_MESMO_SC, value=True, key="sm_f_sc")
f_coleta = st.sidebar.checkbox(tx.R_COLETA, value=True, key="sm_f_coleta")
f_franq = st.sidebar.checkbox(tx.R_FRANQ, value=True, key="sm_f_franq")
f_pedido = st.sidebar.checkbox(tx.R_PEDIDO, value=True, key="sm_f_pedido")
f_techis_status = st.sidebar.checkbox(tx.R_TECHIS_STATUS, value=True, key="sm_f_techis_status")
f_limite = st.sidebar.checkbox(tx.R_LIMITE, value=LIMITAR_REALIZADO, help=tx.R_LIMITE_AJUDA, key="sm_f_limite")

# TECHIS
try:
    techis_partes = [_ler_techis(a.getvalue(), a.name) for a in up_techis or []]
except ValueError as erro:
    st.error(str(erro))
    st.stop()
techis = (pd.concat(techis_partes, ignore_index=True).drop_duplicates() if techis_partes else None)
techis_removidas = 0
if techis is not None:
    techis, techis_removidas = filtrar_techis(techis, f_techis_status)

# JMS
apoio = carregar_apoio()
partes, diags = [], []
try:
    for arq in up_hist or []:                       # histórico: dias anteriores já exportados pelo app
        for tipo, df in _ler_historico(arq.getvalue()).items():
            b, d = preparar_jms(df, tipo, apoio, filtro_status=f_status, filtro_mesmo_sc=f_sc,
                                filtro_ponto_coleta=f_coleta, filtro_franqueado=f_franq, filtro_pedido_mae=f_pedido)
            partes.append(b)
            diags.append({tx.DIAG["arquivo"]: f"{arq.name} ({tx.TIPO_PT[tipo]})", **d})
    for tipo in TIPOS:
        for arq in up[tipo] or []:
            b, d = preparar_jms(_ler_jms(arq.getvalue(), arq.name), tipo, apoio, filtro_status=f_status,
                                filtro_mesmo_sc=f_sc, filtro_ponto_coleta=f_coleta,
                                filtro_franqueado=f_franq, filtro_pedido_mae=f_pedido)
            partes.append(b)
            diags.append({tx.DIAG["arquivo"]: arq.name, **d})
except ValueError as erro:
    st.error(str(erro))
    st.stop()

base = juntar(partes)
if not base.empty:
    base = aplicar_techis(base, contagem_techis(techis), limitar=f_limite)
    if techis is None:
        st.warning(tx.INFO_SEM_TECHIS)
elif partes:
    st.warning(tx.AVISO_BASE_VAZIA)

dia = None
if not base.empty:
    dias = sorted(base["dia"].dt.date.unique())
    t2 = dt.date.today() - dt.timedelta(days=2)            # o relatório é T-2
    padrao = max([i for i, d in enumerate(dias) if d <= t2], default=len(dias) - 1)
    opcao_valida("sm_dia", dias + [None])
    dia = st.sidebar.selectbox(tx.DIA, dias + [None], index=padrao, key="sm_dia",
                               format_func=lambda d: tx.TODOS if d is None else d.strftime("%d/%m/%Y"))
    n_dias = st.sidebar.slider(tx.N_DIAS, 3, 10, 7, key="sm_n_dias")
    escala_comum = st.sidebar.checkbox(tx.ESCALA, value=False, key="sm_escala")

# ---------- Abas ----------
abas = st.tabs([tx.nome_aba("COLETA"), tx.nome_aba("ENTREGA"), tx.ABA_TENDENCIA, tx.ABA_PENDENTES,
                tx.ABA_TECHIS, tx.ABA_BASE])
export = {}

for aba, tipo in zip(abas[:2], TIPOS):
    with aba:
        if base.empty or not (base["tipo"] == tipo).any():
            st.info(tx.INFO_SEM_TIPO)
            continue
        st.subheader(tx.titulo_tabela(tipo, dia))
        tab = tabela_dia(base, tipo, dia)
        rot = rotular_tabela(tab)
        st.dataframe(_estilizar(rot), width="stretch", hide_index=True, height=(len(rot) + 1) * 35 + 3,
                     column_config=_alinhar_direita(tx.COL_TAXA, tx.COL_RANK))
        g = _grafico(tab)
        if g is not None:
            st.altair_chart(g.properties(title=tx.COL_TAXA), width="stretch")
        rodape(*[[p] for p in tx.OBS.split("  \n")])
        export[tx.aba_excel_tabela(tipo)] = (rot, {"taxa": tx.COL_TAXA}, tx.OBS.replace("  \n", "\n"))

with abas[2]:
    if base.empty:
        st.info(tx.INFO_SEM_TIPO)
    else:
        if base["dia"].nunique() < 2:
            st.info(tx.INFO_UM_DIA)
        for tipo in TIPOS:
            t = tendencia(base, tipo)
            if t.empty:
                continue
            st.subheader(tx.subtitulo_tendencia(tipo))
            if base["dia"].nunique() >= 2:
                st.html(tabela_tendencia_html(t, n_dias=n_dias, escala_comum=escala_comum))
            with st.expander(tx.EXPANDER_TENDENCIA, expanded=base["dia"].nunique() < 2):
                st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
                st.caption(tx.ACUMULADO_AJUDA)
            export[tx.aba_excel_tendencia(tipo)] = (t, {})

with abas[3]:
    if base.empty:
        st.info(tx.INFO_SEM_TIPO)
    else:
        st.caption(tx.PEND_INTRO)
        p = pendentes(base, dia)                      # dia None = todos os dias
        c1, c2 = st.columns(2)
        tipos_sel = c1.multiselect(tx.PEND_TIPO, list(TIPOS), default=list(TIPOS),
                                   format_func=lambda t: f"{tx.TIPO_ZH[t]} {tx.TIPO_PT[t]}", key="sm_p_tipo")
        regs = sorted(p["regiao"].unique(), key=lambda r: (r not in REGIOES, REGIOES.index(r) if r in REGIOES else 0, r))
        regs_sel = c2.multiselect(tx.PEND_REGIOES, regs, default=[r for r in regs if r in REGIOES], key="sm_p_reg")
        p = p[p["tipo"].isin(tipos_sel) & p["regiao"].isin(regs_sel)]
        primeiro = ["tipo", "regiao", "dia", "viagem", "id", "partida", "chegada", "placa", "transportador",
                    "sm_prev", "sm_real", "faltam", "sm_contagem"]
        p = p[primeiro + [c for c in colunas_internas(p) if c not in primeiro]]
        p["tipo"] = p["tipo"].map(lambda t: f"{tx.TIPO_ZH[t]} {tx.TIPO_PT[t]}")
        vis = p.rename(columns={**tx.COLUNAS_BASE, "faltam": "缺少 Faltam"})
        p["dia"] = p["dia"].dt.date
        vis = p.rename(columns={**tx.COLUNAS_BASE, "faltam": "缺少 Faltam"})
        st.caption(tx.pend_resumo(len(vis), int(p["faltam"].sum())))
        st.dataframe(vis, width="stretch", hide_index=True, height=420)
        st.download_button(tx.PEND_BAIXAR, data=df_para_xlsx(vis, "Viagens sem SM"),
                           file_name=f"SM_viagens_sem_SM_{'Todos' if dia is None else dia.strftime('%d.%m')}.xlsx", key="sm_p_down",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with abas[4]:
    if techis is None:
        st.info(tx.INFO_SEM_TECHIS_ABA)
    else:
        st.caption(tx.TECHIS_INTRO)
        ligado = techis_ligado(techis, base)
        espaco = embarque_com_espaco(techis)
        m = st.columns(3)
        m[0].metric(tx.TECHIS_TOTAL, f"{len(techis):,}".replace(",", "."))
        if not base.empty:
            m[1].metric(tx.TECHIS_LIGADAS, f"{int(ligado.sum()):,}".replace(",", "."))
        if espaco.any():
            m[2].metric(tx.DIAG["techis_tab"], int(espaco.sum()), help=tx.TECHIS_TAB_AJUDA)

        if "Status" in techis.columns:
            st.caption(tx.TECHIS_POR_STATUS + ": " + " · ".join(
                f"{k} {v:,}".replace(",", ".") for k, v in techis["Status"].value_counts().items()))
        filtros = st.columns(3)
        vis = techis
        for col_ui, coluna, rotulo in zip(filtros, ["Status", "Operação", "Tecnologia"],
                                          [tx.TECHIS_STATUS, tx.TECHIS_OPERACAO, tx.TECHIS_TECNOLOGIA]):
            if coluna in techis.columns:
                opcoes = sorted(techis[coluna].dropna().astype(str).unique())
                sel = col_ui.multiselect(rotulo, opcoes, key=f"sm_t_{coluna}")
                if sel:
                    vis = vis[vis[coluna].astype(str).isin(sel)]
        busca = st.text_input(tx.TECHIS_BUSCA, key="sm_t_busca").strip().upper()
        if busca:
            cols_busca = [c for c in ["Placa", "Nº SM", COL_TECHIS_EMBARQUE] if c in vis.columns]
            hit = pd.Series(False, index=vis.index)
            for c in cols_busca:
                hit |= vis[c].astype(str).str.upper().str.contains(busca, regex=False, na=False)
            vis = vis[hit]
        st.dataframe(vis, width="stretch", hide_index=True, height=480)
        st.caption(f"{len(vis):,} / {len(techis):,}".replace(",", "."))
        st.download_button(tx.TECHIS_BAIXAR, data=df_para_xlsx(vis, tx.ABA_EXCEL_TECHIS),
                           file_name=f"SISTEMA TECHIS {dt.date.today():%d.%m}.xlsx", key="sm_t_down",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with abas[5]:
    st.subheader(tx.SUB_DIAG)
    if techis is not None:
        diags.append({tx.DIAG["arquivo"]: ", ".join(a.name for a in up_techis), tx.DIAG["tipo"]: "TECHIS",
                      tx.DIAG["techis_linhas"]: len(techis),
                      tx.DIAG["techis_status"]: techis_removidas,
                      tx.DIAG["techis_tab"]: int(embarque_com_espaco(techis).sum())})
    st.dataframe(pd.DataFrame(diags).map(
        lambda v: "" if pd.isna(v) else str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)), width="stretch", hide_index=True)
    if not base.empty:
        st.subheader(tx.SUB_BASE)
        st.dataframe(base[colunas_internas(base)].rename(columns=tx.COLUNAS_BASE), width="stretch",
                     hide_index=True, height=400)
        for tipo in TIPOS:
            if (base["tipo"] == tipo).any():
                export[tx.aba_excel_base(tipo)] = (base_para_exportar(base, tipo), {"sem_pct": True})

# ---------- Exportar ----------
if export and dia is not None:
    if techis is not None and st.sidebar.checkbox(tx.EXPORTAR_TECHIS, value=False, key="sm_x_techis"):
        export[tx.ABA_EXCEL_TECHIS] = (techis, {"sem_pct": True})
    st.sidebar.download_button(
        tx.EXPORTAR, data=_excel(export), file_name=tx.arquivo_excel(dia), key="sm_down",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
