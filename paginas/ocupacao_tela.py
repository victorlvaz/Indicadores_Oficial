"""Página: 装载率 / Taxa de Ocupação Linha Secundária (dados vêm do histórico no banco)."""
import io

import pandas as pd
import streamlit as st

from comum.sql import ids_do_arquivo
from comum import banco, feishu_envio, periodos, previa, resumo_dia
from comum.estilos import estilizar_tendencia, pct, pp
from comum import original
from ocupacao.config import COL as COL_JMS
from comum.exportar import para_excel, periodo_texto, titulo_relatorio
from comum.idioma import cabecalho, rodape
from comum.sparkline import tabela_tendencia_html
from comum import janela as janela_ui
from comum.tema import CINZA_DESTAQUE, VERDE, VERMELHO
from comum.uploads import esvaziar, manter, opcao_valida, upload_persistente
from ocupacao import historico, resumo_ui, textos as tx
from ocupacao.calculos import (TOTAL, carregar_apoio, comparar, detalhe_veiculo, ler_relatorio, preparar,
                               rotular_tabela, tabela_periodo, tendencia)
from ocupacao.config import CAPACIDADE, INDICADORES, TIPOS

cabecalho(*tx.PAGINA)


@st.cache_data(show_spinner=False, max_entries=8)
def _ler_cache(conteudo: bytes) -> pd.DataFrame:
    return ler_relatorio(io.BytesIO(conteudo))


@st.cache_data(show_spinner="Carregando histórico…", max_entries=2)
def _historico(versao: tuple) -> pd.DataFrame:
    return historico.ler(banco.engine())


def _n(v) -> str:
    return "–" if pd.isna(v) else f"{v:,.0f}".replace(",", ".")


def _estilo_resumo(tab: pd.DataFrame, comp: bool):
    """Tabela consolidada: números com ponto de milhar, % com vírgula, 1ª linha (total) em cinza, queda em vermelho."""
    c = tab.columns
    txt = tab.copy()
    txt[c[0]] = tab[c[0]].astype(str)
    for col in (c[3], c[4], c[5]):
        txt[col] = tab[col].map(_n if col != c[5] else pct)
    txt[c[6]] = tab[c[6]].map(lambda v: "–" if pd.isna(v) else str(int(v)))
    if comp:
        txt[tx.COL_COMP], txt[tx.COL_VAR] = tab[tx.COL_COMP].map(pct), tab[tx.COL_VAR].map(pp)
    est = pd.DataFrame("", index=txt.index, columns=txt.columns)
    est.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    if comp:
        est.loc[(tab[tx.COL_VAR].round(4) < 0).fillna(False), tx.COL_VAR] = f"color:{VERMELHO};font-weight:700"
        est.loc[(tab[tx.COL_VAR].round(4) > 0).fillna(False), tx.COL_VAR] = f"color:{VERDE};font-weight:700"
    return txt.style.apply(lambda _: est, axis=None)


def _estilo_detalhe(d: pd.DataFrame):
    txt = pd.DataFrame({tx.COL_REGIAO: d["regiao"], tx.COL_VEICULO: d["veiculo"], tx.COL_CAP: d["cap_veiculo"].map(_n),
                        tx.COL_VIAGENS: d["viagens"], tx.COL_PREV: d["prev"].map(_n), tx.COL_REAL: d["real"].map(_n),
                        tx.COL_TAXA: d["taxa"].map(pct)})
    est = pd.DataFrame("", index=txt.index, columns=txt.columns)
    est.loc[d["veiculo"] == "Total", :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    return txt, txt.style.apply(lambda _: est, axis=None)


manter("ocres_reg", "ocres_vis", "ocres_ano", "ocres_pil_W", "ocres_pil_M", "oc_gran", "oc_comp",
       "oc_per_D", "oc_per_W", "oc_per_M", "oc_per_Y", "oc_n_dias", "oc_escala")

# ---------- Banco ----------
try:
    eng = banco.engine()
    versao = historico.versao(eng)
except Exception as erro:
    st.error(tx.ERRO_BANCO + str(erro).split("[SQL:")[0].strip()[:400])
    st.stop()

# ---------- Carga ----------
st.sidebar.header(tx.HIST)
st.sidebar.caption(f"{tx.BANCO_EM_USO}: {banco.descricao()}")
arquivos = upload_persistente("ocupacao", tx.UPLOAD, ["xls", "xlsx"], tx.UPLOAD_AJUDA)
if arquivos:
    st.sidebar.caption(tx.PENDENTE)
    if st.sidebar.button(tx.SALVAR, type="primary", help=tx.SALVAR_AJUDA, key="oc_salvar"):
        apoio, resumos = carregar_apoio(), []
        try:
            for arq in arquivos:
                with st.spinner(tx.SALVANDO + arq.name, show_time=True):
                    df = _ler_cache(arq.getvalue())
                    b, d = preparar(df, apoio)
                    resumos.append((arq.name, historico.salvar(eng, b, arq.name, len(df), ids_brutos=ids_do_arquivo(df, COL_JMS["id"]))))
        except ValueError as erro:
            st.sidebar.error(str(erro))
        except Exception as erro:
            st.sidebar.error(tx.ERRO_BANCO + str(erro).split("[SQL:")[0].strip()[:400])
        else:
            esvaziar("ocupacao")
            st.session_state["oc_msg_salvo"] = [
                f"{nome}: {r['novas']} novas · {r['atualizadas']} atualizadas" for nome, r in resumos]
            st.rerun()
for linha in st.session_state.pop("oc_msg_salvo", []):
    st.sidebar.success(f"{tx.SALVO_OK} — {linha}")

@st.cache_data(show_spinner="Tratando os arquivos enviados…", max_entries=3)
def _pendente(pacote: tuple, ref_versao):
    """Arquivos enviados e ainda não salvos, tratados pelas mesmas regras do Salvar (banco temporário em memória)."""
    apoio_p, tmp, ids, erros = carregar_apoio(), previa.engine_memoria(), [], []
    for nome, conteudo in pacote:
        try:
            bruto = _ler_cache(conteudo)
            b_p, _ = preparar(bruto, apoio_p)
            historico.salvar(tmp, b_p, nome, len(bruto), ids_brutos=ids_do_arquivo(bruto, COL_JMS["id"]))
            ids += ids_do_arquivo(bruto, COL_JMS["id"])
        except Exception as erro:
            erros.append(f"{nome}: {str(erro).split('[SQL:')[0].strip()[:300]}")
    return historico.ler(tmp, com_original=True), ids, erros


pend, ids_pend = None, []
if arquivos:
    pend, ids_pend, erros_pend = _pendente(tuple((a.name, a.getvalue()) for a in arquivos), versao)
    for e in erros_pend:
        st.sidebar.error(e)
    pend = pend if len(pend) else None

if versao[0] == 0 and pend is None:
    st.info(tx.INFO_SEM_ARQUIVO)
    st.stop()

base = previa.combinar("oc_ver", _historico(versao) if versao[0] else None, pend, ["id"], ids_pend)   # só o enviado ou histórico + enviado
if base.empty:
    st.warning(tx.AVISO_BASE_VAZIA)
    st.stop()

# ---------- Período e comparação ----------
st.sidebar.header(tx.GRAN)
gran = st.sidebar.radio(tx.GRAN, periodos.GRANULARIDADES, horizontal=True, label_visibility="collapsed",
                        format_func=lambda g: tx.GRAN_NOMES[g], key="oc_gran")
lista = periodos.lista(base["dia"], gran)
opcoes = lista + [None]
chave_per = f"oc_per_{gran}"
opcao_valida(chave_per, opcoes)
if chave_per not in st.session_state:
    st.session_state[chave_per] = opcoes[len(lista) - 1]
ini = st.sidebar.selectbox(tx.PERIODO[gran], opcoes, key=chave_per,
                           format_func=lambda p: tx.TODOS if p is None else periodos.rotulo(p, gran))
fim = None if ini is None else periodos.fim(ini, gran)
modo_comp = st.sidebar.radio(tx.COMPARAR, ["ant", "ano"], key="oc_comp",
                             format_func=lambda m: tx.COMP_ANTERIOR if m == "ant" else tx.COMP_ANO)
n_per = st.sidebar.slider(tx.N_DIAS, 3, 10, 6, key="oc_n_dias")
escala_comum = st.sidebar.checkbox(tx.ESCALA, value=False, help=tx.ESCALA_AJUDA, key="oc_escala")

per_txt = tx.TODOS if ini is None else periodos.rotulo(ini, gran)
ini_comp = fim_comp = None
if ini is not None:
    ini_comp = (periodos.anterior if modo_comp == "ant" else periodos.ano_passado)(ini, gran)
    fim_comp = periodos.fim(ini_comp, gran)

# ---------- Abas ----------
abas = st.tabs([tx.nome_aba(t) for t in TIPOS] + [tx.nome_aba_tendencia(), tx.ABA_RESUMO, tx.ABA_BASE])
export = {}

for aba, tipo in zip(abas[:2], TIPOS):
    with aba:
        st.subheader(f"{INDICADORES[tipo]['titulo']} – {per_txt}")
        atual = tabela_periodo(base, tipo, ini, fim)
        if ini is not None:
            atual = comparar(atual, tabela_periodo(base, tipo, ini_comp, fim_comp))
        tab = rotular_tabela(atual)
        st.dataframe(_estilo_resumo(tab, ini is not None), width="stretch", hide_index=True, height=(len(tab) + 1) * 35 + 3)
        if ini is None:
            st.caption(tx.COMP_SEM_TODOS)
        else:
            st.caption(f"{tx.COMP_LEGENDA}: {periodos.rotulo(ini_comp, gran)}")
            if atual["taxa_comp"].isna().all():
                st.caption(tx.COMP_SEM_DADOS)
        exp = tab.copy()
        cols_exp = {"taxa": tx.COL_TAXA}
        if ini is not None:
            exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100
            cols_exp.update(pct_extra=[tx.COL_COMP], pp_extra=[tx.COL_VAR])
        export[tx.aba_excel_tabela(tipo)] = (exp, cols_exp, tx.nota_texto(tipo))

        st.subheader(tx.subtitulo_detalhe(tipo))
        det = detalhe_veiculo(base, tipo, ini, fim)
        cru, estilo = _estilo_detalhe(det)
        st.dataframe(estilo, width="stretch", hide_index=True, height=min((len(cru) + 1) * 35 + 3, 520))
        export[tx.aba_excel_detalhe(tipo)] = (cru, {})
        rodape(*tx.NOTAS[tipo])

with abas[2]:
    n_tab = janela_ui.escolher(gran, "oc_janela")
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
        if gran == "W" and ini is not None:      # semana: o Excel traz os DIAS da semana escolhida (não S01, S02...)
            _td = tendencia(base[base["dia"] >= pd.Timestamp(ini)], tipo, "D", fim)
            t_tab = _td if not _td.empty else t_tab
        export[tx.aba_excel_tendencia(tipo)] = (t_tab, {"sparkline": True})

with abas[3]:
    resumo_ui.mostrar(base, export, dia=resumo_dia.dia_lateral(gran, ini))

with abas[4]:
    sem_cap = sorted(v or "(?)" for v in base.loc[~base["veiculo"].isin(CAPACIDADE), "veiculo"].unique())
    if sem_cap:
        st.warning(tx.AVISO_SEM_CAPACIDADE + ", ".join(sem_cap))
    st.subheader(tx.SUB_CARGAS)
    cargas = historico.ler_cargas(eng).rename(columns={
        "carregado_em": "Carga", "arquivo": "Arquivo", "linhas_lidas": "Linhas lidas",
        "linhas_usadas": "Linhas usadas", "novas": "Novas", "atualizadas": "Atualizadas",
        "dia_min": "De", "dia_max": "Até"}).drop(columns=["id", "observacao"], errors="ignore")
    st.dataframe(cargas, width="stretch", hide_index=True, height=min((len(cargas) + 1) * 35 + 3, 240))
    st.subheader(tx.SUB_BASE)
    sub = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    st.caption(f"{len(sub):,}".replace(",", ".") + " linhas · " + per_txt)
    st.dataframe(sub.drop(columns=["original"], errors="ignore").head(5000).rename(columns=tx.COLUNAS_BASE), width="stretch", hide_index=True, height=400)

export_final = original.base_primeiro(export, eng, historico.viagens, ["id"], "dia", sub, COL_JMS)      # 1ª aba: base idêntica ao JMS
titulo_xl = titulo_relatorio("paginas/ocupacao_tela.py")                       # linha de título do Excel: nome do relatório + data
periodo_xl = periodo_texto(ini, fim, base["dia"])
nome_xl = tx.arquivo_excel("Todos" if ini is None else periodos.rotulo_curto(ini, gran).replace("/", "."))
st.sidebar.download_button(
    tx.EXPORTAR, data=lambda e=export_final, t=titulo_xl, d=periodo_xl: para_excel(e, t, d),
    file_name=nome_xl,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
feishu_envio.botao(
    chave="oc", ini=ini, fim=fim, dias=base["dia"], export=export, titulo=titulo_xl, periodo_xl=periodo_xl, nome_xl=nome_xl,
    excel=lambda: para_excel(export_final, titulo_xl, periodo_xl),
    abertura=("Indicadores de Taxa de Ocupação referente ao dia {d}.", "以下是{d}支线装载率指标。"),
    blocos=[("linha", "Base de dados: JMS (coleta e entrega)"), ("linha", "数据来源：JMS（集货与散货）"),
            ("img", None, [tx.aba_excel_tabela("COLETA")]),
            ("img", None, [tx.aba_excel_tabela("ENTREGA")]),
            ("img", [("Tendência ", False), ("COLETA", True), ("/ ", False), ("ENTREGA", True), (":", False)],
             [tx.aba_excel_tendencia("COLETA"), tx.aba_excel_tendencia("ENTREGA")]),
            ("comentario",),
            ("linha", "Segue abaixo, no detalhe, a volumetria carregada por cada tipo de veículo."),
            ("linha", "以下是按车型统计的装载量明细。"),
            ("linha", "Volumes Previsto x Volumes Carregados (Realizado)"),
            ("img", "**COLETA**:", [tx.aba_excel_detalhe("COLETA")]),
            ("img", "**ENTREGA**:", [tx.aba_excel_detalhe("ENTREGA")])])
