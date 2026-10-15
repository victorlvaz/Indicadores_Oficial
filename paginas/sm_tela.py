"""Página: SM状态统计 / Estatística de Status dos SMs (Coleta e Entrega + extração do TECHIS)."""
import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from comum import banco, periodos
from comum.exportar import para_excel
from comum.estilos import estilizar_tendencia, pct, pp
from comum.idioma import cabecalho, rodape
from comum.uploads import esvaziar, manter, opcao_valida, upload_persistente
from comum.sparkline import tabela_tendencia_html
from comum.tema import CINZA_DESTAQUE, VERMELHO
from sm import historico, resumo_ui, textos as tx
from sm.calculos import (aplicar_techis, base_para_exportar, carregar_apoio, colunas_internas, comparar,
                         contagem_techis, df_para_xlsx, embarque_com_espaco, filtrar_techis, juntar, ler_planilha,
                         ler_techis, pendentes, preparar_jms, rotular_tabela, tabela_periodo, techis_ligado,
                         tendencia)
from sm.config import COL_TECHIS_EMBARQUE, LIMITAR_REALIZADO, REGIOES, TIPOS

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


@st.cache_data(show_spinner="Carregando histórico…", max_entries=2)
def _historico(versao: tuple) -> pd.DataFrame:
    """Histórico inteiro; só é relido quando entra dado novo (a versão muda)."""
    return historico.ler(banco.engine())


@st.cache_data(show_spinner=False)
def _excel(abas: dict) -> bytes:
    return para_excel(abas)


def _estilizar(tab: pd.DataFrame, comparando: bool):
    """Percentuais com 2 casas e vírgula, linha de total (1ª) em cinza, queda em vermelho."""
    txt = tab.copy()
    txt[tx.COL_TAXA] = tab[tx.COL_TAXA].map(pct)
    txt[tx.COL_RANK] = tab[tx.COL_RANK].map(lambda v: "–" if pd.isna(v) else str(int(v)))
    estilos = pd.DataFrame("", index=txt.index, columns=txt.columns)
    if comparando:
        txt[tx.COL_COMP] = tab[tx.COL_COMP].map(pct)
        txt[tx.COL_VAR] = tab[tx.COL_VAR].map(pp)
        estilos.loc[(tab[tx.COL_VAR].round(4) < 0).fillna(False), tx.COL_VAR] = f"color:{VERMELHO};font-weight:700"
    estilos.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    return txt.style.apply(lambda _: estilos, axis=None)


def _alinhar_direita(*colunas):
    try:
        return {c: st.column_config.TextColumn(alignment="right") for c in colunas if c}
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
manter("sm_gran", "sm_comp", "sm_per_D", "sm_per_W", "sm_per_M", "sm_per_Y", "sm_n_dias", "sm_escala", "sm_x_techis",
       "smres_vis", "smres_ano", "smres_pil_W", "smres_pil_M")      # não perder filtros ao trocar de relatório

# ---------- Banco ----------
try:
    eng = banco.engine()
    versao = historico.versao(eng)
except Exception as erro:                                  # banco fora do ar, senha errada, sem driver...
    st.error(tx.ERRO_BANCO + str(erro))
    st.stop()

# ---------- Carga: sobe os relatórios e salva no histórico ----------
st.sidebar.header(tx.HIST)
st.sidebar.caption(f"{tx.BANCO_EM_USO}: {banco.descricao()}")
# os arquivos enviados ficam guardados ao trocar de relatório (saem com ✕, ao salvar ou ao desligar o servidor)
up = {
    "COLETA": upload_persistente("sm_coleta", tx.UP_COLETA, ["xls", "xlsx", "csv"], tx.UP_AJUDA_JMS),
    "ENTREGA": upload_persistente("sm_entrega", tx.UP_ENTREGA, ["xls", "xlsx", "csv"], tx.UP_AJUDA_JMS),
}
up_techis = upload_persistente("sm_techis", tx.UP_TECHIS, ["xls", "xlsx", "csv"], tx.UP_AJUDA_TECHIS)
pendente = bool(up["COLETA"] or up["ENTREGA"] or up_techis)

# TECHIS (regras fixas: só Em Viagem / Finalizado)
try:
    techis_partes = [_ler_techis(a.getvalue(), a.name) for a in up_techis or []]
except ValueError as erro:
    st.sidebar.error(str(erro))
    st.stop()
techis = (pd.concat(techis_partes, ignore_index=True).drop_duplicates() if techis_partes else None)
techis_removidas = 0
if techis is not None:
    techis, techis_removidas = filtrar_techis(techis, True)

# JMS enviado e ainda não salvo (as regras do tratamento são fixas, ver sm/config.py)
apoio = carregar_apoio()
novas, diags = [], []
try:
    for tipo in TIPOS:
        for arq in up[tipo] or []:
            b, d = preparar_jms(_ler_jms(arq.getvalue(), arq.name), tipo, apoio)
            novas.append(b)
            diags.append({tx.DIAG["arquivo"]: arq.name, **d})
except ValueError as erro:
    st.sidebar.error(str(erro))
    st.stop()

if pendente:
    st.sidebar.caption(tx.PENDENTE + " " + ", ".join(a.name for g in (*up.values(), up_techis) for a in g or []))
    if st.sidebar.button(tx.SALVAR, type="primary", help=tx.SALVAR_AJUDA, key="sm_salvar"):
        if not novas:
            st.sidebar.error(tx.SALVAR_SEM_JMS)
        elif techis is None:
            st.sidebar.error(tx.SALVAR_SEM_TECHIS)
        else:
            try:
                para_salvar = aplicar_techis(juntar(novas), contagem_techis(techis), limitar=LIMITAR_REALIZADO)
                nomes = ", ".join(a.name for t in TIPOS for a in up[t] or [])
                r = historico.salvar(eng, para_salvar, nomes)
            except Exception as erro:
                st.sidebar.error(tx.ERRO_BANCO + str(erro))
            else:
                for chave in ("sm_coleta", "sm_entrega", "sm_techis"):
                    esvaziar(chave)
                st.session_state["sm_msg_salvo"] = f"{r['novas']} novas · {r['atualizadas']} atualizadas"
                st.rerun()
if "sm_msg_salvo" in st.session_state:
    st.sidebar.success(f"{tx.SALVO_OK} — {st.session_state.pop('sm_msg_salvo')}")

# ---------- Base = histórico + o que foi enviado e ainda não salvo ----------
hist = _historico(versao) if versao[0] else pd.DataFrame()
partes = []
if not hist.empty:
    partes.append(hist)
if novas:
    nova = juntar(novas)
    if not hist.empty:        # o realizado já guardado vale como mínimo (o TECHIS novo pode não cobrir o dia)
        mapa = hist.set_index(["tipo", "id"])["sm_real_hist"]
        nova["sm_real_hist"] = [mapa.get((t, i), 0) for t, i in zip(nova["tipo"], nova["id"].astype(str).str.strip())]
    else:
        nova["sm_real_hist"] = 0
    partes.append(nova)
if not partes:
    st.info(tx.INFO_SEM_ARQUIVO)
    st.stop()
base = juntar(partes)
base = aplicar_techis(base, contagem_techis(techis), limitar=LIMITAR_REALIZADO)
if pendente:
    st.info(tx.PENDENTES_AVISO)
    if techis is None and novas:
        st.warning(tx.INFO_SEM_TECHIS)
if base.empty:
    st.warning(tx.AVISO_BASE_VAZIA)
    st.stop()

# ---------- Período e comparação ----------
st.sidebar.header(tx.GRAN)
gran = st.sidebar.radio(tx.GRAN, periodos.GRANULARIDADES, horizontal=True, label_visibility="collapsed",
                        format_func=lambda g: tx.GRAN_NOMES[g], key="sm_gran")
lista = periodos.lista(base["dia"], gran)
t2 = pd.Timestamp(dt.date.today() - dt.timedelta(days=2))   # o relatório é T-2
validos = [i for i, p in enumerate(lista) if p <= t2]
padrao = validos[-1] if validos else len(lista) - 1
opcoes = lista + [None]                                     # None = "Todos"
chave_per = f"sm_per_{gran}"
opcao_valida(chave_per, opcoes)
ini = st.sidebar.selectbox(tx.DIA if gran == "D" else tx.PERIODO[gran], opcoes, index=padrao, key=chave_per,
                           format_func=lambda p: tx.TODOS if p is None else periodos.rotulo(p, gran))
fim = None if ini is None else periodos.fim(ini, gran)
modo_comp = st.sidebar.radio(tx.COMPARAR, ["ant", "ano"], key="sm_comp",
                             format_func=lambda m: tx.COMP_ANTERIOR if m == "ant" else tx.COMP_ANO)
n_per = st.sidebar.slider(tx.N_DIAS, 3, 10, 7, key="sm_n_dias")
escala_comum = st.sidebar.checkbox(tx.ESCALA, value=False, key="sm_escala")

per_txt = tx.TODOS if ini is None else periodos.rotulo(ini, gran)
ini_comp = fim_comp = None
if ini is not None:
    ini_comp = (periodos.anterior if modo_comp == "ant" else periodos.ano_passado)(ini, gran)
    fim_comp = periodos.fim(ini_comp, gran)

# ---------- Abas ----------
abas = st.tabs([tx.nome_aba("COLETA"), tx.nome_aba("ENTREGA"), tx.ABA_TENDENCIA, tx.ABA_PENDENTES,
                tx.ABA_TECHIS, tx.ABA_RESUMO, tx.ABA_BASE])
export = {}

for aba, tipo in zip(abas[:2], TIPOS):
    with aba:
        if not (base["tipo"] == tipo).any():
            st.info(tx.INFO_SEM_TIPO)
            continue
        st.subheader(tx.titulo_tabela(tipo, per_txt))
        tab = tabela_periodo(base, tipo, ini, fim)
        if ini is not None:
            tab = comparar(tab, tabela_periodo(base, tipo, ini_comp, fim_comp))
        rot = rotular_tabela(tab)
        extra = (tx.COL_COMP, tx.COL_VAR) if ini is not None else ()
        st.dataframe(_estilizar(rot, ini is not None), width="stretch", hide_index=True,
                     height=(len(rot) + 1) * 35 + 3, column_config=_alinhar_direita(tx.COL_TAXA, tx.COL_RANK, *extra))
        if ini is None:
            st.caption(tx.COMP_SEM_TODOS)
        else:
            st.caption(f"{tx.COMP_LEGENDA}: {periodos.rotulo(ini_comp, gran)}")
            if tab["taxa_comp"].isna().all():
                st.caption(tx.COMP_SEM_DADOS)
        g = _grafico(tab)
        if g is not None:
            st.altair_chart(g.properties(title=tx.COL_TAXA), width="stretch")
        rodape(*[[p] for p in tx.OBS.split("  \n")])
        exp = rot.copy()
        cols_exp = {"taxa": tx.COL_TAXA}
        if ini is not None:
            exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100
            cols_exp.update(pct_extra=[tx.COL_COMP], pp_extra=[tx.COL_VAR])
        export[tx.aba_excel_tabela(tipo)] = (exp, cols_exp, tx.OBS.replace("  \n", "\n"))

with abas[2]:
    for tipo in TIPOS:
        t = tendencia(base, tipo, gran, fim)
        if t.empty:
            continue
        st.subheader(tx.subtitulo_tendencia(tipo))
        if t.shape[1] > 4:
            st.html(tabela_tendencia_html(t, n_dias=n_per, escala_comum=escala_comum,
                                          unidade=tx.UNIDADE_TENDENCIA[gran]))
            with st.expander(tx.EXPANDER_TENDENCIA):
                st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
                st.caption(tx.ACUMULADO_AJUDA)
        else:
            st.info(tx.INFO_UM_DIA)
            st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
        export[tx.aba_excel_tendencia(tipo)] = (t, {})

with abas[3]:
    if base.empty:
        st.info(tx.INFO_SEM_TIPO)
    else:
        st.caption(tx.PEND_INTRO)
        p = pendentes(base, ini, fim)                 # ini None = todos os dias
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
        p["dia"] = p["dia"].dt.date
        vis = p.rename(columns={**tx.COLUNAS_BASE, "faltam": "缺少 Faltam"})
        st.caption(tx.pend_resumo(len(vis), int(p["faltam"].sum())))
        st.dataframe(vis, width="stretch", hide_index=True, height=420)
        st.download_button(tx.PEND_BAIXAR, data=df_para_xlsx(vis, "Viagens sem SM"),
                           file_name=f"SM_viagens_sem_SM_{'Todos' if ini is None else periodos.rotulo_curto(ini, gran).replace('/', '.')}.xlsx", key="sm_p_down",
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
    resumo_ui.mostrar(base, export)

with abas[6]:
    st.subheader(tx.SUB_CARGAS)
    cargas = historico.ler_cargas(eng).rename(columns={
        "carregado_em": "Carga", "arquivo": "Arquivo", "linhas_usadas": "Linhas usadas", "novas": "Novas",
        "atualizadas": "Atualizadas", "dia_min": "De", "dia_max": "Até"}).drop(columns=["id", "observacao"], errors="ignore")
    st.dataframe(cargas, width="stretch", hide_index=True, height=min((len(cargas) + 1) * 35 + 3, 240))
    if techis is not None:
        diags.append({tx.DIAG["arquivo"]: ", ".join(a.name for a in up_techis), tx.DIAG["tipo"]: "TECHIS",
                      tx.DIAG["techis_linhas"]: len(techis),
                      tx.DIAG["techis_status"]: techis_removidas,
                      tx.DIAG["techis_tab"]: int(embarque_com_espaco(techis).sum())})
    if diags:
        st.subheader(tx.SUB_DIAG)
        st.dataframe(pd.DataFrame(diags).map(
            lambda v: "" if pd.isna(v) else str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)),
            width="stretch", hide_index=True)
    st.subheader(tx.SUB_BASE)
    sub = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    st.caption(f"{len(sub):,}".replace(",", ".") + " linhas · " + per_txt)
    st.dataframe(sub[colunas_internas(sub)].head(5000).rename(columns=tx.COLUNAS_BASE), width="stretch",
                 hide_index=True, height=400)
    for tipo in TIPOS:
        if (sub["tipo"] == tipo).any():
            export[tx.aba_excel_base(tipo)] = (base_para_exportar(sub, tipo), {"sem_pct": True})

# ---------- Exportar ----------
if techis is not None and st.sidebar.checkbox(tx.EXPORTAR_TECHIS, value=False, key="sm_x_techis"):
    export[tx.ABA_EXCEL_TECHIS] = (techis, {"sem_pct": True})
st.sidebar.download_button(
    tx.EXPORTAR, data=_excel(export),
    file_name=tx.arquivo_excel("Todos" if ini is None else periodos.rotulo_curto(ini, gran).replace("/", ".")),
    key="sm_down", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
