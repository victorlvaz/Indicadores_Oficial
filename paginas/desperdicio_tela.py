"""Página: 浪费率 / Taxa de Desperdício Linha Secundária.
Usa o histórico da Taxa de Ocupação (mesmo arquivo JMS): desperdício = 1 − ocupação, com a ocupação limitada a 100%."""
import pandas as pd
import streamlit as st

from comum import banco, feishu_envio, periodos, resumo_dia
from comum.estilos import estilizar_tendencia, pct, pp
from comum import original
from ocupacao.config import COL as COL_JMS
from comum.exportar import para_excel, periodo_texto, titulo_relatorio
from comum.idioma import cabecalho, rodape
from comum.sparkline import tabela_tendencia_html
from comum import janela as janela_ui
from comum.tema import CINZA_DESTAQUE, VERDE, VERMELHO
from comum.uploads import manter, opcao_valida
from desperdicio import textos as tx
from desperdicio.calculos import comparar, detalhe_veiculo, frete_por_viagem, tabela_periodo, tendencia, viagens_sem_frete
from custos import historico as hist_custos
from ocupacao import historico
from ocupacao.config import INDICADORES, TIPOS

cabecalho(*tx.PAGINA)


@st.cache_data(show_spinner="Carregando histórico…", max_entries=2)
def _historico(versao: tuple) -> pd.DataFrame:
    return historico.ler(banco.engine())


@st.cache_data(show_spinner=False, max_entries=2)
def _frete(versao: tuple) -> pd.Series:
    return frete_por_viagem(banco.engine())


def _brl(v) -> str:
    return "–" if pd.isna(v) else "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _n(v) -> str:
    return "–" if pd.isna(v) else f"{v:,.0f}".replace(",", ".")


def _estilo_resumo(tab: pd.DataFrame, comp: bool):
    """Total em cinza; variação em vermelho quando o desperdício subiu."""
    txt = tab.copy()
    txt[tx.COL_REGIAO] = tab[tx.COL_REGIAO].astype(str)
    for col in (tx.COL_PREV, tx.COL_REAL, tx.COL_DESP_VOL):
        txt[col] = tab[col].map(_n)
    txt[tx.COL_DESP] = tab[tx.COL_DESP].map(pct)
    for col in (tx.COL_FRETE, tx.COL_PERDA):
        if col in tab.columns:
            txt[col] = tab[col].map(_brl)
    txt["排名 Ranking"] = tab["排名 Ranking"].map(lambda v: "–" if pd.isna(v) else str(int(v)))
    if comp:
        txt[tx.COL_COMP], txt[tx.COL_VAR] = tab[tx.COL_COMP].map(pct), tab[tx.COL_VAR].map(pp)
    est = pd.DataFrame("", index=txt.index, columns=txt.columns)
    est.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    if comp:
        est.loc[(tab[tx.COL_VAR].round(4) > 0).fillna(False), tx.COL_VAR] = f"color:{VERMELHO};font-weight:700"
        est.loc[(tab[tx.COL_VAR].round(4) < 0).fillna(False), tx.COL_VAR] = f"color:{VERDE};font-weight:700"
    return txt.style.apply(lambda _: est, axis=None)


def _estilo_detalhe(d: pd.DataFrame):
    txt = pd.DataFrame({tx.COL_REGIAO: d["regiao"], tx.COL_VEICULO: d["veiculo"], tx.COL_CAP: d["cap_veiculo"].map(_n),
                        tx.COL_VIAGENS: d["viagens"], tx.COL_PREV: d["prev"].map(_n), tx.COL_REAL: d["real"].map(_n),
                        tx.COL_DESP_VOL: d["desp_vol"].map(_n), tx.COL_DESP: d["desp"].map(pct)})
    est = pd.DataFrame("", index=txt.index, columns=txt.columns)
    est.loc[d["veiculo"] == "Total", :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    return txt, txt.style.apply(lambda _: est, axis=None)


def _rotular(t: pd.DataFrame) -> pd.DataFrame:
    return t.rename(columns={"n": "序号 Nº", "regiao": tx.COL_REGIAO, "viagens": tx.COL_VIAGENS, "prev": tx.COL_PREV,
                             "real": tx.COL_REAL, "desp_vol": tx.COL_DESP_VOL, "desp": tx.COL_DESP, "frete": tx.COL_FRETE, "perda": tx.COL_PERDA,
                             "ranking": "排名 Ranking", "desp_comp": tx.COL_COMP, "variacao": tx.COL_VAR})


manter("dp_gran", "dp_comp", "dp_per_D", "dp_per_W", "dp_per_M", "dp_per_Y", "dp_n_dias", "dp_escala")

# ---------- Banco ----------
try:
    eng = banco.engine()
    versao = historico.versao(eng)
except Exception as erro:
    st.error(tx.ERRO_BANCO + str(erro).split("[SQL:")[0].strip()[:400])
    st.stop()

st.sidebar.caption(f"{tx.BANCO_EM_USO}: {banco.descricao()}")
if versao[0] == 0:
    st.info(tx.SEM_DADOS)
    st.stop()
base = _historico(versao)
if base.empty:
    st.warning(tx.AVISO_BASE_VAZIA)
    st.stop()
base = base.assign(frete=base["id"].astype(str).str.strip().str.upper().map(_frete(hist_custos.versao(eng))))   # frete do relatório de Custos
tem_frete = base["frete"].notna().any()
if not tem_frete:
    base = base.drop(columns="frete")

# ---------- Período e comparação ----------
st.sidebar.header(tx.GRAN)
gran = st.sidebar.radio(tx.GRAN, periodos.GRANULARIDADES, horizontal=True, label_visibility="collapsed",
                        format_func=lambda g: tx.GRAN_NOMES[g], key="dp_gran")
lista = periodos.lista(base["dia"], gran)
opcoes = lista + [None]
chave_per = f"dp_per_{gran}"
opcao_valida(chave_per, opcoes)
if chave_per not in st.session_state:
    st.session_state[chave_per] = opcoes[len(lista) - 1]
ini = st.sidebar.selectbox(tx.PERIODO[gran], opcoes, key=chave_per,
                           format_func=lambda p: tx.TODOS if p is None else periodos.rotulo(p, gran))
fim = None if ini is None else periodos.fim(ini, gran)
modo_comp = st.sidebar.radio(tx.COMPARAR, ["ant", "ano"], key="dp_comp",
                             format_func=lambda m: tx.COMP_ANTERIOR if m == "ant" else tx.COMP_ANO)
n_per = st.sidebar.slider(tx.N_DIAS, 3, 10, 6, key="dp_n_dias")
escala_comum = st.sidebar.checkbox(tx.ESCALA, value=False, help=tx.ESCALA_AJUDA, key="dp_escala")

per_txt = tx.TODOS if ini is None else periodos.rotulo(ini, gran)
ini_comp = fim_comp = None
if ini is not None:
    ini_comp = (periodos.anterior if modo_comp == "ant" else periodos.ano_passado)(ini, gran)
    fim_comp = periodos.fim(ini_comp, gran)

# ---------- Abas ----------
abas = st.tabs([tx.nome_aba(t) for t in TIPOS] + [tx.nome_aba_tendencia(), tx.ABA_BASE])
export = {}

for aba, tipo in zip(abas[:2], TIPOS):
    with aba:
        st.subheader(f"{tx.subtitulo_tabela(tipo)} – {per_txt}")
        atual = tabela_periodo(base, tipo, ini, fim)
        if ini is not None:
            atual = comparar(atual, tabela_periodo(base, tipo, ini_comp, fim_comp))
        tab = _rotular(atual)
        st.dataframe(_estilo_resumo(tab, ini is not None), width="stretch", hide_index=True, height=(len(tab) + 1) * 35 + 3)
        if ini is None:
            st.caption(tx.COMP_SEM_TODOS)
        else:
            st.caption(f"{tx.COMP_LEGENDA}: {periodos.rotulo(ini_comp, gran)}")
            if atual["desp_comp"].isna().all():
                st.caption(tx.COMP_SEM_DADOS)
        if tem_frete:
            sem, total_v = viagens_sem_frete(base, tipo, ini, fim)
            if sem:
                st.caption(f"{sem} / {total_v} " + tx.AVISO_SEM_FRETE.strip())
        exp = tab.copy()
        cols_exp = {"taxa": tx.COL_DESP}
        if tem_frete:
            cols_exp["reais"] = [tx.COL_FRETE, tx.COL_PERDA]
        if ini is not None:
            exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100
            cols_exp.update(pct_extra=[tx.COL_COMP], pp_extra=[tx.COL_VAR], var_inverso=True)
        export[tx.aba_excel_tabela(tipo)] = (exp, cols_exp, tx.nota_texto(tipo))

        st.subheader(tx.subtitulo_detalhe(tipo))
        det = detalhe_veiculo(base, tipo, ini, fim)
        cru, estilo = _estilo_detalhe(det)
        st.dataframe(estilo, width="stretch", hide_index=True, height=min((len(cru) + 1) * 35 + 3, 520))
        det_exp = cru.copy()
        det_exp[tx.COL_DESP] = det["desp"]
        export[tx.aba_excel_detalhe(tipo)] = (det_exp, {"taxa": tx.COL_DESP})
        rodape(*tx.NOTA_RODAPE)

with abas[2]:
    n_tab = janela_ui.escolher(gran, "dp_janela")
    for tipo in TIPOS:
        t = tendencia(base, tipo, gran, fim)
        if t.empty:
            continue
        st.subheader(tx.subtitulo_tendencia(tipo))
        if t.shape[1] > 4:
            st.html(tabela_tendencia_html(t, n_dias=n_per, escala_comum=escala_comum, unidade=tx.UNIDADE_TENDENCIA[gran]))
            t_tab = tendencia(base, tipo, gran, fim, janela=n_tab)
            with st.expander(tx.EXPANDER_TENDENCIA):
                st.dataframe(estilizar_tendencia(t_tab), width="stretch", hide_index=True)
        else:
            st.info(tx.INFO_UM_DIA)
            t_tab = t
            st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
        if gran == "W" and ini is not None:      # semana: o Excel traz os DIAS da semana escolhida
            _td = tendencia(base[base["dia"] >= pd.Timestamp(ini)], tipo, "D", fim)
            t_tab = _td if not _td.empty else t_tab
        export[tx.aba_excel_tendencia(tipo)] = (t_tab, {"sparkline": True})

with abas[3]:
    st.subheader(tx.SUB_BASE)
    sub = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    st.caption(f"{len(sub):,}".replace(",", ".") + " linhas · " + per_txt)
    st.dataframe(sub.drop(columns=["original"], errors="ignore").head(5000).rename(columns=tx.COLUNAS_BASE),
                 width="stretch", hide_index=True, height=400)

export_final = original.base_primeiro(export, eng, historico.viagens, ["id"], "dia", sub, COL_JMS)      # 1ª aba: base idêntica ao JMS
titulo_xl = titulo_relatorio("paginas/desperdicio_tela.py")
periodo_xl = periodo_texto(ini, fim, base["dia"])
nome_xl = tx.arquivo_excel("Todos" if ini is None else periodos.rotulo_curto(ini, gran).replace("/", "."))
st.sidebar.download_button(
    tx.EXPORTAR, data=lambda e=export_final, t=titulo_xl, d=periodo_xl: para_excel(e, t, d),
    file_name=nome_xl,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
feishu_envio.botao(
    chave="dp", ini=ini, fim=fim, dias=base["dia"], export=export, titulo=titulo_xl, periodo_xl=periodo_xl, nome_xl=nome_xl,
    excel=lambda: para_excel(export_final, titulo_xl, periodo_xl),
    abertura=("Indicadores de Taxa de Desperdício referente ao dia {d}.", "以下是{d}支线浪费率指标。"),
    blocos=[("linha", "Base de dados: JMS (coleta e entrega)"), ("linha", "数据来源：JMS（集货与散货）"),
            ("img", "**COLETA**:", [tx.aba_excel_tabela("COLETA")]),
            ("img", "**ENTREGA**:", [tx.aba_excel_tabela("ENTREGA")]),
            ("img", [("Tendência ", False), ("COLETA", True), ("/ ", False), ("ENTREGA", True), (":", False)],
             [tx.aba_excel_tendencia("COLETA"), tx.aba_excel_tendencia("ENTREGA")]),
            ("comentario",)])
