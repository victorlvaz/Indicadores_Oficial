"""Carga única do Relatório consolidado da linha secundária (支线运输综合报表).

O mesmo arquivo alimenta três relatórios: Lacre/Deslacre, Taxa de Uso de APP e Pontualidade (Chegada e Saída).
Quem envia o arquivo em qualquer uma dessas telas atualiza as três bases de uma vez: o arquivo é lido uma única vez
e cada relatório aplica as próprias regras. Se um deles falhar, os outros continuam e o erro aparece com o nome do relatório.
Para acrescentar um relatório que usa o mesmo arquivo: importe o módulo dele e inclua um item em `_destinos()`."""
import io

import pandas as pd
import streamlit as st

from comum import banco
from comum.idioma import bi, frase
from comum.uploads import remover, upload_persistente
from lacre_deslacre import textos as tx            # textos genéricos (histórico, salvar, banco em uso...)

CHAVE_UPLOAD = "consolidado"

UPLOAD = bi("支线运输综合报表", "Relatório consolidado (.xls / .xlsx)")
UPLOAD_AJUDA = frase("一个报表同时更新：解封车率、打卡率、准点率；可上传多个日期的报表。",                      # [revisar]
                     "Um arquivo atualiza ao mesmo tempo Lacre/Deslacre, Uso de APP e Pontualidade. "
                     "Envie um ou mais dias e clique em “Salvar no histórico”.")
SALVANDO = frase("正在读取并保存到各报表，大文件可能需要 1–2 分钟，请勿关闭页面…\n",                        # [revisar]
                 "Lendo e salvando em todos os relatórios (arquivo grande: pode levar 1 a 2 minutos, não feche a página)… ")
ATUALIZA = bi("同时更新", "Atualiza")                                                                     # [revisar]


def _destinos():
    """(nome do relatório, função que recebe (engine, nome do arquivo, df lido) e devolve o resumo da gravação)."""
    from app_uso import calculos as app_c, historico as app_h
    from lacre_deslacre import calculos as lac_c, historico as lac_h
    from pontualidade import calculos as pt_c, historico as pt_h

    def lacre(eng, nome, df):
        b, _ = lac_c.preparar(df, lac_c.carregar_apoio())
        return lac_h.salvar(eng, b, nome, len(df))

    def uso_app(eng, nome, df):
        conhecidos = app_h.tipos_conhecidos(eng)
        novos = app_c.tipos_do_arquivo(df)                              # antes do filtro de franqueado
        b, _ = app_c.preparar(df, app_c.carregar_apoio(), {**conhecidos, **novos})
        app_h.guardar_tipos(eng, novos)
        return app_h.salvar(eng, b, nome, len(df))

    def pontualidade(eng, nome, df):
        b, _, descartadas = pt_c.preparar(df)
        return pt_h.salvar(eng, b, nome, len(df), descartadas)

    return [(bi("支线解封车率", "Lacre / Deslacre"), lacre),
            (bi("支线打卡率", "Uso de APP"), uso_app),
            (bi("支线准点率", "Pontualidade"), pontualidade)]


def _colunas() -> set:
    from app_uso.config import COL as c_app
    from lacre_deslacre.config import COL as c_lac
    from pontualidade.config import COL as c_pt
    return set(c_app.values()) | set(c_lac.values()) | set(c_pt.values())


@st.cache_data(show_spinner=False, max_entries=2)
def _ler(conteudo: bytes) -> pd.DataFrame:
    """Lê o Excel uma única vez, só com as colunas que algum dos relatórios usa. O arquivo vem como .xls mas costuma ser xlsx."""
    precisa = _colunas()
    uso = lambda nome: str(nome).strip() in precisa or nome in precisa
    try:
        return pd.read_excel(io.BytesIO(conteudo), engine="openpyxl", usecols=uso)
    except Exception:
        return pd.read_excel(io.BytesIO(conteudo), engine="xlrd", usecols=uso)


def _gravar(eng, nome: str, conteudo: bytes):
    """Lê o arquivo e grava em todos os relatórios. Retorna (linhas de sucesso, linhas de erro)."""
    try:
        df = _ler(conteudo)
    except Exception as erro:
        return [], [f"{nome}: {erro}"]
    ok, erros = [], []
    for rotulo, funcao in _destinos():
        try:
            r = funcao(eng, nome, df)
            ok.append(f"{rotulo}: {r['novas']} novos · {r['atualizadas']} atualizados")
        except ValueError as erro:                                    # coluna faltando etc.
            erros.append(f"{rotulo} · {nome}: {erro}")
        except Exception as erro:
            erros.append(f"{rotulo} · {nome}: {tx.ERRO_BANCO}{erro}")
    return ok, erros


def painel_carga(eng) -> None:
    """Barra lateral: histórico, banco em uso, envio do arquivo e botão salvar (igual nas três telas)."""
    st.sidebar.header(tx.HIST)
    st.sidebar.caption(f"{tx.BANCO_EM_USO}: {banco.descricao()}")
    arquivos = upload_persistente(CHAVE_UPLOAD, UPLOAD, ["xls", "xlsx"], UPLOAD_AJUDA)
    if arquivos:
        st.sidebar.caption(tx.PENDENTE)
        if st.sidebar.button(tx.SALVAR, type="primary", help=tx.SALVAR_AJUDA, key="cons_salvar"):
            salvos, ok_tudo, erros = [], [], []
            for arq in arquivos:                                      # cada arquivo é independente
                with st.spinner(SALVANDO + arq.name, show_time=True):
                    ok, err = _gravar(eng, arq.name, arq.getvalue())
                ok_tudo += [f"{arq.name} → {linha}" for linha in ok]
                erros += err
                if ok and not err:                                    # só some da lista se foi para todos os relatórios
                    salvos.append(arq.name)
            remover(CHAVE_UPLOAD, salvos)
            st.session_state["cons_msg_ok"], st.session_state["cons_msg_erro"] = ok_tudo, erros
            st.rerun()
    for linha in st.session_state.pop("cons_msg_ok", []):
        st.sidebar.success(f"{tx.SALVO_OK} — {linha}")
    for linha in st.session_state.pop("cons_msg_erro", []):
        st.sidebar.error(linha)
