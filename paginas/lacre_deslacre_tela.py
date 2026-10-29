"""Página: 支线解封车率 / Lacre / Deslacre Linha Secundária (dados vêm do histórico no banco)."""
import pandas as pd
import streamlit as st

from comum import banco, feishu_envio, resumo_dia
from comum.exportar import sem_ba_na_coleta
from comum import previa
from comum.consolidado import painel_carga, pendente
from comum.estilos import estilizar_tabela, estilizar_tendencia
from comum import original
from lacre_deslacre.config import COL as COL_JMS
from comum.exportar import para_excel, periodo_texto, titulo_relatorio
from comum.idioma import cabecalho, rodape
from comum.sparkline import tabela_tendencia_html
from comum import janela as janela_ui
from comum.uploads import manter, opcao_valida
from lacre_deslacre import historico, periodos, resumo_ui, textos as tx
from lacre_deslacre.calculos import (base_pont_lacre, comparar, comparar_pont_lacre, dias_sem_partida, rotular_pont_lacre,
                                     rotular_tabela, tabela_periodo, tabela_pont_lacre, tendencia, tendencia_pont_lacre)
from lacre_deslacre.config import INDICADORES

cabecalho(*tx.PAGINA)


@st.cache_data(show_spinner="Carregando histórico…", max_entries=2)
def _historico(versao: tuple) -> pd.DataFrame:
    """Histórico inteiro; só é relido quando entra dado novo (a versão muda)."""
    return historico.ler(banco.engine())


def _alinhar_direita(*colunas, estreitas=()):
    """Percentuais e ranking viram texto: alinha à direita (e deixa as colunas estreitas pequenas)."""
    cfg = {}
    for c in (*colunas, *estreitas):
        try:
            cfg[c] = st.column_config.TextColumn(alignment="right" if c in colunas else "left",
                                                 width="small" if c in estreitas else None)
        except TypeError:                                  # versão antiga do Streamlit
            pass
    return cfg


manter("lac_ind", "res_reg", "res_vis", "res_ano", "res_pil_W", "res_pil_M", "lac_gran", "lac_comp", "lac_per_D", "lac_per_W", "lac_per_M", "lac_per_Y", "lac_n_dias", "lac_escala")

# ---------- Banco ----------
try:
    eng = banco.engine()
    versao = historico.versao(eng)
except Exception as erro:                                  # banco fora do ar, senha errada, sem driver...
    st.error(tx.ERRO_BANCO + str(erro).split("[SQL:")[0].strip()[:400])
    st.stop()

# ---------- Carga: sobe o relatório consolidado (alimenta Lacre, Uso de APP e Pontualidade) ----------
arquivos_pendentes = painel_carga(eng)
pend, ids_pend = pendente(arquivos_pendentes, "lacre", versao)

if versao[0] == 0 and pend is None:
    st.info(tx.INFO_SEM_ARQUIVO)
    st.stop()

base = previa.combinar("lac_ver", _historico(versao) if versao[0] else None, pend, historico.CHAVE, ids_pend)   # só o enviado ou histórico + enviado
if base.empty:
    st.warning(tx.AVISO_BASE_VAZIA)
    st.stop()

# ---------- Período e comparação ----------
st.sidebar.header(tx.GRAN)
gran = st.sidebar.radio(tx.GRAN, periodos.GRANULARIDADES, horizontal=True, label_visibility="collapsed",
                        format_func=lambda g: tx.GRAN_NOMES[g], key="lac_gran")
lista = periodos.lista(base["dia"], gran)
opcoes = lista + [None]                                    # None = "Todos"
chave_per = f"lac_per_{gran}"
opcao_valida(chave_per, opcoes)
if chave_per not in st.session_state:                      # valor inicial pelo session_state (sem 'index': evita o aviso)
    st.session_state[chave_per] = opcoes[len(lista) - 1]
ini = st.sidebar.selectbox(tx.PERIODO[gran], opcoes, key=chave_per,
                           format_func=lambda p: tx.TODOS if p is None else periodos.rotulo(p, gran))
fim = None if ini is None else periodos.fim(ini, gran)
modo_comp = st.sidebar.radio(tx.COMPARAR, ["ant", "ano"], key="lac_comp",
                             format_func=lambda m: tx.COMP_ANTERIOR if m == "ant" else tx.COMP_ANO)
n_per = st.sidebar.slider(tx.N_DIAS, 3, 10, 6, key="lac_n_dias")
escala_comum = st.sidebar.checkbox(tx.ESCALA, value=False, help=tx.ESCALA_AJUDA, key="lac_escala")

per_txt = tx.TODOS if ini is None else periodos.rotulo(ini, gran)
ini_comp = fim_comp = None
if ini is not None:
    ini_comp = (periodos.anterior if modo_comp == "ant" else periodos.ano_passado)(ini, gran)
    fim_comp = periodos.fim(ini_comp, gran)

# ---------- Indicador (igual à Pontualidade Chegada/Saída: o filtro troca a visualização) ----------
ind = st.radio(tx.INDICADOR, ["lac", "pl"], horizontal=True, key="lac_ind",
               format_func=lambda i: tx.IND_LAC if i == "lac" else tx.IND_PL)

# ---------- Abas ----------
export = {}
if ind == "lac":
    nomes = ([tx.nome_aba(t, e) for t, e in INDICADORES]
             + [tx.nome_aba_tendencia(e) for e in ("lacre", "deslacre")]
             + [tx.ABA_RESUMO, tx.ABA_BASE])
else:
    nomes = [tx.pl_nome_aba(t) for t in ("COLETA", "ENTREGA")] + [tx.PL_ABA_TEND, tx.ABA_BASE]
abas = st.tabs(nomes)

def _pct(v):
    return "–" if pd.isna(v) else f"{v * 100:.2f}%".replace(".", ",")


_falta_pl = dias_sem_partida(base)
_base_pl = base_pont_lacre(base)

if ind == "lac":

    for aba, (tipo, evento) in zip(abas[:4], INDICADORES):
        with aba:
            cfg = INDICADORES[(tipo, evento)]
            st.subheader(f"{cfg['titulo']} – {per_txt}")
            atual = tabela_periodo(base, tipo, evento, ini, fim)
            if ini is not None:
                comp = tabela_periodo(base, tipo, evento, ini_comp, fim_comp)
                atual = comparar(atual, comp)
            tab = rotular_tabela(atual, tipo, evento)
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
                if (atual["taxa_comp"].isna()).all():
                    st.caption(tx.COMP_SEM_DADOS)
            rodape(*tx.NOTAS[evento])
            exp = tab.copy()
            cols_exp = {"taxa": col_taxa, "meta": col_meta}
            if ini is not None:
                exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100                  # em pontos percentuais
                cols_exp.update(pct_extra=[tx.COL_COMP], pp_extra=[tx.COL_VAR])
            export[tx.aba_excel_tabela(tipo, evento)] = (exp, cols_exp, tx.nota_texto(evento))

    for aba, evento in zip(abas[4:6], ["lacre", "deslacre"]):
        with aba:
            n_tab = janela_ui.escolher(gran, f"lac_janela_{evento}")
            for tipo in ("COLETA", "ENTREGA"):
                t = tendencia(base, tipo, evento, gran, fim)
                if t.empty:
                    continue
                st.subheader(tx.subtitulo_tendencia(tipo, evento))
                if t.shape[1] > 4:
                    st.html(tabela_tendencia_html(t, n_dias=n_per, escala_comum=escala_comum,
                                                  unidade=tx.UNIDADE_TENDENCIA[gran]))
                    t_tab = tendencia(base, tipo, evento, gran, fim, janela=n_tab)
                    with st.expander(tx.EXPANDER_TENDENCIA):
                        st.dataframe(estilizar_tendencia(t_tab), width="stretch", hide_index=True)
                else:
                    st.info(tx.INFO_UM_DIA)
                    t_tab = t
                    st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
                if gran == "W" and ini is not None:      # semana: o Excel traz os DIAS da semana escolhida (não S01, S02...)
                    _td = tendencia(base[base["dia"] >= pd.Timestamp(ini)], tipo, evento, "D", fim)
                    t_tab = _td if not _td.empty else t_tab
                export[tx.aba_excel_tendencia(tipo, evento)] = (t_tab, {"sparkline": True})



    with abas[6]:
        resumo_ui.mostrar(base, export, dia=resumo_dia.dia_lateral(gran, ini))
    aba_base = abas[7]
else:
    if _base_pl.empty:
        with abas[0]:
            st.info(tx.PL_VAZIO)
    elif _falta_pl:
        st.warning(tx.PL_SEM_PARTIDA.format(n=_falta_pl))
    for aba, tipo in zip(abas[:2], ("COLETA", "ENTREGA")):
        with aba:
            if _base_pl.empty:
                continue
            st.subheader(f"{tx.PL_TITULO[tipo]} – {per_txt}")
            atual = tabela_pont_lacre(base, tipo, ini, fim)
            if ini is not None:
                atual = comparar_pont_lacre(atual, tabela_pont_lacre(base, tipo, ini_comp, fim_comp))
            tab = rotular_pont_lacre(atual)
            c_pont, c_meta = tx.PL_PONT, "目标 Meta"
            extra = (tx.COL_COMP, tx.COL_VAR) if ini is not None else (None, None)
            vis = tab.copy()
            for c in (tx.PL_TAXA_LAC, tx.PL_PONT_LAC):
                vis[c] = vis[c].map(_pct)
            st.dataframe(estilizar_tabela(vis, c_pont, c_meta, *extra), width="stretch", hide_index=True,
                         height=(len(vis) + 1) * 35 + 3,
                         column_config=_alinhar_direita(c_pont, c_meta, tx.PL_TAXA_LAC, tx.PL_PONT_LAC, *[c for c in extra if c],
                                                        estreitas=(tab.columns[0],)))
            if ini is not None:
                st.caption(f"{tx.COMP_LEGENDA}: {periodos.rotulo(ini_comp, gran)}")
            rodape(*tx.PL_NOTAS)
            exp = tab.copy()
            cols_exp = {"taxa": c_pont, "meta": c_meta, "pct_extra": [tx.PL_TAXA_LAC, tx.PL_PONT_LAC]}
            if ini is not None:
                exp[tx.COL_VAR] = exp[tx.COL_VAR] * 100
                cols_exp["pct_extra"].append(tx.COL_COMP)
                cols_exp["pp_extra"] = [tx.COL_VAR]
            export[tx.pl_aba_excel(tipo)] = (exp, cols_exp, tx.PL_NOTA)

    with abas[2]:
        if not _base_pl.empty:
            n_tab = janela_ui.escolher(gran, "lac_janela_pl")
            for tipo in ("COLETA", "ENTREGA"):
                t = tendencia_pont_lacre(base, tipo, gran, fim)
                if t.empty:
                    continue
                st.subheader(tx.pl_subtitulo_tend(tipo))
                if t.shape[1] > 4:
                    st.html(tabela_tendencia_html(t, n_dias=n_per, escala_comum=escala_comum,
                                                  unidade=tx.UNIDADE_TENDENCIA[gran]))
                    t_tab = tendencia_pont_lacre(base, tipo, gran, fim, janela=n_tab)
                    with st.expander(tx.EXPANDER_TENDENCIA):
                        st.dataframe(estilizar_tendencia(t_tab), width="stretch", hide_index=True)
                else:
                    st.info(tx.INFO_UM_DIA)
                    t_tab = t
                    st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
                if gran == "W" and ini is not None:
                    _td = tendencia_pont_lacre(base[base["dia"] >= pd.Timestamp(ini)], tipo, "D", fim)
                    t_tab = _td if not _td.empty else t_tab
                export[tx.pl_aba_excel_tend(tipo)] = (t_tab, {"sparkline": True})
    aba_base = abas[3]

with aba_base:
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

for _k in list(export):                       # BA não tem coleta: sai das abas de COLETA (export e bot)
    export[_k] = (sem_ba_na_coleta(_k, export[_k][0]),) + tuple(export[_k][1:])
export_final = original.base_primeiro(export, eng, historico.viagens, historico.CHAVE, "dia", sub, COL_JMS)      # 1ª aba: base idêntica ao JMS
titulo_xl = titulo_relatorio("paginas/lacre_deslacre_tela.py")                       # linha de título do Excel: nome do relatório + data
periodo_xl = periodo_texto(ini, fim, base["dia"])
nome_xl = tx.arquivo_excel("Todos" if ini is None else periodos.rotulo_curto(ini, gran).replace("/", "."))
st.sidebar.download_button(
    tx.EXPORTAR, data=lambda e=export_final, t=titulo_xl, d=periodo_xl: para_excel(e, t, d),
    file_name=nome_xl,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
feishu_envio.botao(
    chave="lac", ini=ini, fim=fim, dias=base["dia"], export=export, titulo=titulo_xl, periodo_xl=periodo_xl, nome_xl=nome_xl,
    excel=lambda: para_excel(export_final, titulo_xl, periodo_xl),
    abertura=(("Segue a **Pontualidade do lacre** da Secundária do dia {d}.", "以下是{d}二次封签准点率。") if ind == "pl" else
              ("Segue a Taxa de **Lacre** e **Deslacre** da Secundária do dia {d}.", "以下是{d}二次封签和拆签的费用。")),
    blocos=([("img", [("Pontualidade do lacre ", False), (tp, True), (":", False)], [tx.pl_aba_excel(tp)])
             for tp in ("COLETA", "ENTREGA") if tx.pl_aba_excel(tp) in export]
            + [("img", [("Tendência Pontualidade do lacre - ", False), ("COLETA", True), ("/ ", False), ("ENTREGA", True), (":", False)],
                [tx.pl_aba_excel_tend("COLETA"), tx.pl_aba_excel_tend("ENTREGA")])] if ind == "pl" and not _base_pl.empty else
            [("img", [("Lacre " if ev == "lacre" else "Deslacre ", False), (tp, True), (":", False)], [tx.aba_excel_tabela(tp, ev)])
             for tp, ev in INDICADORES]
            + [("img", [(f"Tendência {nm} - ", False), ("COLETA", True), ("/ ", False), ("ENTREGA", True), (":", False)],
                [tx.aba_excel_tendencia("COLETA", ev), tx.aba_excel_tendencia("ENTREGA", ev)])
               for ev, nm in (("lacre", "Lacre"), ("deslacre", "Deslacre"))])
    + [("comentario",)])


# ---------- Exportar um intervalo livre (de/até): o acumulado do período escolhido, comparado ao intervalo anterior de mesmo tamanho ----------
with st.sidebar.expander(tx.PER_EXPORT):
    st.caption(tx.PER_EXPORT_AJUDA)
    d_min, d_max = base["dia"].min().date(), base["dia"].max().date()
    faixa = st.date_input(tx.PER_EXPORT_DATAS, value=(max(d_min, d_max.replace(day=1)), d_max),
                          min_value=d_min, max_value=d_max, key="lac_faixa", format="DD/MM/YYYY")
    if len(faixa) != 2:
        st.caption(tx.PER_EXPORT_ESCOLHA)
    else:
        f_ini, f_fim = pd.Timestamp(faixa[0]), pd.Timestamp(faixa[1])
        sub_f = base[(base["dia"] >= f_ini) & (base["dia"] <= f_fim)]
        if sub_f.empty:
            st.caption(tx.PER_EXPORT_VAZIO)
        else:
            def _excel_faixa(ini_f=f_ini, fim_f=f_fim):
                n = (fim_f - ini_f).days + 1
                c_fim, c_ini = ini_f - pd.Timedelta(days=1), ini_f - pd.Timedelta(days=n)
                exp_f = {}
                for tipo, evento in INDICADORES:
                    atual_f = comparar(tabela_periodo(base, tipo, evento, ini_f, fim_f),
                                       tabela_periodo(base, tipo, evento, c_ini, c_fim))
                    t_f = rotular_tabela(atual_f, tipo, evento)
                    c_taxa, c_meta = t_f.columns[4], t_f.columns[5]
                    t_f[tx.COL_VAR] = t_f[tx.COL_VAR] * 100
                    exp_f[tx.aba_excel_tabela(tipo, evento)] = (
                        t_f, {"taxa": c_taxa, "meta": c_meta, "pct_extra": [tx.COL_COMP], "pp_extra": [tx.COL_VAR]},
                        tx.nota_texto(evento))
                exp_f = original.base_primeiro(exp_f, eng, historico.viagens, historico.CHAVE, "dia", base[(base["dia"] >= ini_f) & (base["dia"] <= fim_f)], COL_JMS)
                return para_excel(exp_f, titulo_xl, periodo_texto(ini_f, fim_f, base["dia"]))
            st.download_button(
                tx.PER_EXPORT_BOTAO, data=_excel_faixa, key="lac_baixar_faixa",
                file_name=tx.arquivo_excel(f"{f_ini:%d.%m}-{f_fim:%d.%m}"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
