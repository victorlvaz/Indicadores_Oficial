"""Página: 支线打卡率 / Taxa de Uso de APP Linha Secundária (dados vêm do histórico no banco)."""
import io

import pandas as pd
import streamlit as st

from app_uso import historico, resumo_ui, textos as tx
from app_uso.calculos import (calcular_partes, carregar_apoio, comparar, ler_relatorio, preparar, rotular_tabela,
                              tabela_periodo, tendencia, tipos_do_arquivo)
from app_uso.config import INDICADORES
from comum import banco, periodos
from comum.estilos import estilizar_tabela, estilizar_tendencia
from comum.exportar import para_excel
from comum.idioma import cabecalho, rodape
from comum.sparkline import tabela_tendencia_html
from comum.uploads import esvaziar, manter, opcao_valida, upload_persistente

cabecalho(*tx.PAGINA)


@st.cache_data(show_spinner=False, max_entries=8)
def _ler_cache(conteudo: bytes) -> pd.DataFrame:
    return ler_relatorio(io.BytesIO(conteudo))


@st.cache_data(show_spinner="Carregando histórico…", max_entries=2)
def _historico(versao: tuple) -> pd.DataFrame:
    return historico.ler(banco.engine())


def _alinhar_direita(*colunas, estreitas=()):
    cfg = {}
    for c in (*colunas, *estreitas):
        try:
            cfg[c] = st.column_config.TextColumn(alignment="right" if c in colunas else "left",
                                                 width="small" if c in estreitas else None)
        except TypeError:
            pass
    return cfg


manter("appres_reg", "appres_vis", "appres_ano", "appres_pil_W", "appres_pil_M", "app_gran", "app_comp",
       "app_per_D", "app_per_W", "app_per_M", "app_per_Y", "app_n_dias", "app_escala")

# ---------- Banco ----------
try:
    eng = banco.engine()
    versao = historico.versao(eng)
except Exception as erro:
    st.error(tx.ERRO_BANCO + str(erro))
    st.stop()

# ---------- Carga: sobe o relatório e salva no histórico ----------
st.sidebar.header(tx.HIST)
st.sidebar.caption(f"{tx.BANCO_EM_USO}: {banco.descricao()}")
arquivos = upload_persistente("appuso", tx.UPLOAD, ["xls", "xlsx"], tx.UPLOAD_AJUDA)
if arquivos:
    st.sidebar.caption(tx.PENDENTE)
    if st.sidebar.button(tx.SALVAR, type="primary", help=tx.SALVAR_AJUDA, key="app_salvar"):
        apoio, resumos = carregar_apoio(), []
        try:
            for arq in arquivos:
                with st.spinner(tx.SALVANDO + arq.name, show_time=True):      # arquivo grande: leitura leva de 30 s a 2 min
                    df = _ler_cache(arq.getvalue())
                with st.spinner(tx.SALVANDO + arq.name, show_time=True):
                    conhecidos = historico.tipos_conhecidos(eng)
                    novos = tipos_do_arquivo(df)                       # antes do filtro de franqueado
                    b, d = preparar(df, apoio, {**conhecidos, **novos})
                    historico.guardar_tipos(eng, novos)
                    resumos.append((arq.name, historico.salvar(eng, b, arq.name, len(df))))
        except ValueError as erro:
            st.sidebar.error(str(erro))
        except Exception as erro:
            st.sidebar.error(tx.ERRO_BANCO + str(erro))
        else:
            esvaziar("appuso")
            st.session_state["app_msg_salvo"] = [
                f"{nome}: {r['novas']} novas · {r['atualizadas']} atualizadas" for nome, r in resumos]
            st.rerun()
for linha in st.session_state.pop("app_msg_salvo", []):
    st.sidebar.success(f"{tx.SALVO_OK} — {linha}")

if versao[0] == 0:
    st.info(tx.INFO_SEM_ARQUIVO)
    st.stop()

base = _historico(versao)
if base.empty:
    st.warning(tx.AVISO_BASE_VAZIA)
    st.stop()

# ---------- Período e comparação ----------
st.sidebar.header(tx.GRAN)
gran = st.sidebar.radio(tx.GRAN, periodos.GRANULARIDADES, horizontal=True, label_visibility="collapsed",
                        format_func=lambda g: tx.GRAN_NOMES[g], key="app_gran")
lista = periodos.lista(base["dia"], gran)
opcoes = lista + [None]
chave_per = f"app_per_{gran}"
opcao_valida(chave_per, opcoes)
if chave_per not in st.session_state:                      # valor inicial pelo session_state (sem 'index': evita o aviso)
    st.session_state[chave_per] = opcoes[len(lista) - 1]
ini = st.sidebar.selectbox(tx.PERIODO[gran], opcoes, key=chave_per,
                           format_func=lambda p: tx.TODOS if p is None else periodos.rotulo(p, gran))
fim = None if ini is None else periodos.fim(ini, gran)
modo_comp = st.sidebar.radio(tx.COMPARAR, ["ant", "ano"], key="app_comp",
                             format_func=lambda m: tx.COMP_ANTERIOR if m == "ant" else tx.COMP_ANO)
n_per = st.sidebar.slider(tx.N_DIAS, 3, 10, 6, key="app_n_dias")
escala_comum = st.sidebar.checkbox(tx.ESCALA, value=False, help=tx.ESCALA_AJUDA, key="app_escala")

per_txt = tx.TODOS if ini is None else periodos.rotulo(ini, gran)
ini_comp = fim_comp = None
if ini is not None:
    ini_comp = (periodos.anterior if modo_comp == "ant" else periodos.ano_passado)(ini, gran)
    fim_comp = periodos.fim(ini_comp, gran)

# ---------- Abas ----------
tipos = list(INDICADORES)
abas = st.tabs([tx.nome_aba(t) for t in tipos] + [tx.nome_aba_tendencia(), tx.ABA_RESUMO, tx.ABA_BASE])
export = {}

for aba, tipo in zip(abas[:2], tipos):
    with aba:
        st.subheader(f"{INDICADORES[tipo]['titulo']} – {per_txt}")
        atual = tabela_periodo(base, tipo, ini, fim)
        if ini is not None:
            atual = comparar(atual, tabela_periodo(base, tipo, ini_comp, fim_comp))
        tab = rotular_tabela(atual, tipo)
        col_taxa, col_meta = tab.columns[4], tab.columns[5]
        extra = (tx.COL_COMP, tx.COL_VAR) if ini is not None else (None, None)
        st.dataframe(estilizar_tabela(tab, col_taxa, col_meta, *extra), width="stretch", hide_index=True,
                     height=(len(tab) + 1) * 35 + 3,
                     column_config=_alinhar_direita(col_taxa, col_meta, tab.columns[6], *[c for c in extra if c],
                                                    estreitas=(tab.columns[0],)))
        if ini is None:
            st.caption(tx.COMP_SEM_TODOS)
        else:
            st.caption(f"{tx.COMP_LEGENDA}: {periodos.rotulo(ini_comp, gran)}")
            if atual["taxa_comp"].isna().all():
                st.caption(tx.COMP_SEM_DADOS)
        rodape(*tx.NOTAS[tipo])
        exp = tab.copy()
        cols_exp = {"taxa": col_taxa, "meta": col_meta}
        if ini is not None:
            exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100
            cols_exp.update(pct_extra=[tx.COL_COMP], pp_extra=[tx.COL_VAR])
        export[tx.aba_excel_tabela(tipo)] = (exp, cols_exp, tx.nota_texto(tipo))

with abas[2]:
    for tipo in tipos:
        t = tendencia(base, tipo, gran, fim)
        if t.empty:
            continue
        st.subheader(tx.subtitulo_tendencia(tipo))
        if t.shape[1] > 4:
            st.html(tabela_tendencia_html(t, n_dias=n_per, escala_comum=escala_comum, unidade=tx.UNIDADE_TENDENCIA[gran]))
            with st.expander(tx.EXPANDER_TENDENCIA):
                st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
        else:
            st.info(tx.INFO_UM_DIA)
            st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
        export[tx.aba_excel_tendencia(tipo)] = (t, {})

with abas[3]:
    resumo_ui.mostrar(base, export)

with abas[4]:
    st.subheader(tx.SUB_CARGAS)
    cargas = historico.ler_cargas(eng).rename(columns={
        "carregado_em": "Carga", "arquivo": "Arquivo", "linhas_lidas": "Linhas lidas",
        "linhas_usadas": "Linhas usadas", "novas": "Novas", "atualizadas": "Atualizadas",
        "dia_min": "De", "dia_max": "Até"}).drop(columns=["id", "observacao"], errors="ignore")
    st.dataframe(cargas, width="stretch", hide_index=True, height=min((len(cargas) + 1) * 35 + 3, 240))
    st.subheader(tx.SUB_BASE)
    sub = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    st.caption(f"{len(sub):,}".replace(",", ".") + " linhas · " + per_txt)
    st.dataframe(sub.head(5000).rename(columns=tx.COLUNAS_BASE), width="stretch", hide_index=True, height=400)

st.sidebar.download_button(
    tx.EXPORTAR, data=para_excel(export),
    file_name=tx.arquivo_excel("Todos" if ini is None else periodos.rotulo_curto(ini, gran).replace("/", ".")),
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
