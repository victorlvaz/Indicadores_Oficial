"""Carga única do Relatório consolidado da linha secundária (支线运输综合报表).

O mesmo arquivo alimenta três relatórios: Lacre/Deslacre, Taxa de Uso de APP e Pontualidade (Chegada e Saída).
Quem envia o arquivo em qualquer uma dessas telas atualiza as três bases de uma vez: o arquivo é lido uma única vez
e cada relatório aplica as próprias regras. Se um deles falhar, os outros continuam e o erro aparece com o nome do relatório.
Para acrescentar um relatório que usa o mesmo arquivo: importe o módulo dele e inclua um item em `_destinos()`."""
import io

import pandas as pd
import streamlit as st

from comum import banco, previa
from comum.sql import ids_do_arquivo
from comum.idioma import bi, frase
from comum.uploads import remover, upload_persistente
from lacre_deslacre import textos as tx            # textos genéricos (histórico, salvar, banco em uso...)

CHAVE_UPLOAD = "consolidado"

UPLOAD = bi("支线运输综合报表", "Relatório consolidado (.xls / .xlsx)")
UPLOAD_AJUDA = frase("一个报表同时更新：解封车率、打卡率、准点率；可上传多个日期的报表。",                      # [revisar]
                     "Um arquivo atualiza ao mesmo tempo Lacre/Deslacre, Uso de APP e Pontualidade. "
                     "Envie um ou mais dias e clique em “Salvar no histórico”. "
                     "Extract novo (sem Status/Tipo de transportador/Pedido mãe): envie junto o consolidado, que serve só de apoio; "
                     "o extract alimenta apenas a Pontualidade.")
AVISO_SEM_APOIO = "trechos do extract não estão no consolidado de apoio (mantidos: Franqueado/pedido mãe não puderam ser conferidos)"
IGNORADO = "não usado neste relatório"
SALVANDO = frase("正在读取并保存到各报表，大文件可能需要 1–2 分钟，请勿关闭页面…\n",                        # [revisar]
                 "Lendo e salvando em todos os relatórios (arquivo grande: pode levar 1 a 2 minutos, não feche a página)… ")
ATUALIZA = bi("同时更新", "Atualiza")                                                                     # [revisar]


def _destinos():
    """(nome do relatório, função que recebe (engine, nome do arquivo, df lido) e devolve o resumo da gravação)."""
    return [(rotulo, f) for rotulo, f, *_ in _relatorios()]


def _relatorios():
    """(nome, gravar(eng, nome, df, eng_ref=None), ler(eng, com_original), coluna do ID no arquivo, chave) de cada relatório.
    eng_ref = banco real, de onde se lê o "último tipo de transportador" quando se grava num banco temporário."""
    from app_uso import calculos as app_c, config as app_cfg, historico as app_h
    from lacre_deslacre import calculos as lac_c, config as lac_cfg, historico as lac_h
    from pontualidade import calculos as pt_c, config as pt_cfg, historico as pt_h

    def lacre(eng, nome, df, eng_ref=None, apoio_df=None, tem_extract=False):
        if pt_c.eh_extract(df):                                      # extract novo só alimenta a Pontualidade
            return {"novas": 0, "atualizadas": 0, "linhas": 0, "ignorado": True}
        b, _ = lac_c.preparar(df, lac_c.carregar_apoio())
        return lac_h.salvar(eng, b, nome, len(df), ids_brutos=ids_do_arquivo(df, lac_cfg.COL["id"]))

    def uso_app(eng, nome, df, eng_ref=None, apoio_df=None, tem_extract=False):
        if pt_c.eh_extract(df):
            return {"novas": 0, "atualizadas": 0, "linhas": 0, "ignorado": True}
        conhecidos = app_h.tipos_conhecidos(eng_ref or eng)
        novos = app_c.tipos_do_arquivo(df)                              # antes do filtro de franqueado
        b, _ = app_c.preparar(df, app_c.carregar_apoio(), {**conhecidos, **novos})
        if eng_ref is None:
            app_h.guardar_tipos(eng, novos)
        return app_h.salvar(eng, b, nome, len(df), ids_brutos=ids_do_arquivo(df, app_cfg.COL["id"]))

    def pontualidade(eng, nome, df, eng_ref=None, apoio_df=None, tem_extract=False):
        """Com extract novo no envio, a Pontualidade vem dele; o consolidado vira só apoio (Franqueado, pedido mãe, status)."""
        if pt_c.eh_extract(df):
            b, diag, descartadas = pt_c.preparar_extract(df, apoio_df)
        elif tem_extract:
            return {"novas": 0, "atualizadas": 0, "linhas": 0, "ignorado": True}
        else:
            b, diag, descartadas = pt_c.preparar(df)
        r = pt_h.salvar(eng, b, nome, len(df), descartadas)
        r["sem_apoio"] = diag.get(pt_c.tx.DIAG["sem_apoio"], 0)
        return r

    return [(bi("支线解封车率", "Lacre / Deslacre"), lacre, lac_h.ler, lac_cfg.COL["id"], lac_h.CHAVE, "lacre"),
            (bi("支线打卡率", "Uso de APP"), uso_app, app_h.ler, app_cfg.COL["id"], app_h.CHAVE, "app"),
            (bi("支线准点率", "Pontualidade"), pontualidade, pt_h.ler, pt_cfg.COL["id"], pt_h.CHAVE, "pt")]


def _contexto(pacote) -> tuple:
    """(consolidados reunidos para apoio, há extract novo no envio?). pacote = [(nome, bytes), ...]."""
    from pontualidade.calculos import eh_extract
    from pontualidade.config import COL as c_pt, PEDIDO_MAE_NOMES
    uteis = [c_pt["id"], c_pt["cod_chegada"], c_pt["status"], c_pt["tipo_transportador"], *PEDIDO_MAE_NOMES]
    cons, tem = [], False
    for _, conteudo in pacote:
        try:
            d = _ler(conteudo)
        except Exception:
            continue
        if eh_extract(d):
            tem = True
        else:
            cons.append(d[[c for c in uteis if c in d.columns]])
    return (pd.concat(cons, ignore_index=True) if cons else None), tem


@st.cache_data(show_spinner="Tratando os arquivos enviados…", max_entries=3)
def _pendente_cache(qual: str, arquivos: tuple, ref_versao):
    """(base tratada dos arquivos enviados no formato do histórico, ids brutos, erros). Cache pelo conteúdo dos arquivos."""
    eng_ref = banco.engine()
    for _, gravar, ler, col_id, chave, q in _relatorios():
        if q != qual:
            continue
        tmp = previa.engine_memoria()
        ids, erros = [], []
        apoio_df, tem_extract = _contexto(arquivos)
        for nome, conteudo in arquivos:
            try:
                df = _ler(conteudo)
                r = gravar(tmp, nome, df, eng_ref, apoio_df=apoio_df, tem_extract=tem_extract) or {}
                if r.get("ignorado"):
                    continue
                if r.get("sem_apoio"):
                    erros.append(f"⚠️ {nome}: {r['sem_apoio']} " + AVISO_SEM_APOIO)
                ids += ids_do_arquivo(df, col_id)
            except Exception as erro:
                erros.append(f"{nome}: {str(erro).split('[SQL:')[0].strip()[:300]}")
        return ler(tmp, com_original=True), ids, erros
    return None, [], []


def pendente(arquivos, qual: str, ref_versao=None):
    """Base dos arquivos enviados e ainda não salvos, para o relatório `qual` ("lacre" | "app" | "pt").
    Devolve (DataFrame ou None, ids brutos). Erros de leitura aparecem na barra lateral."""
    if not arquivos:
        return None, []
    pacote = tuple((a.name, a.getvalue()) for a in arquivos)
    df, ids, erros = _pendente_cache(qual, pacote, ref_versao)
    for e in erros:
        (st.sidebar.warning if e.startswith("⚠️") else st.sidebar.error)(e)
    return (df if df is not None and len(df) else None), ids


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
        return pd.read_excel(io.BytesIO(conteudo), engine="openpyxl")
    except Exception:
        return pd.read_excel(io.BytesIO(conteudo), engine="xlrd")


def _gravar(eng, nome: str, conteudo: bytes, apoio_df=None, tem_extract=False):
    """Lê o arquivo e grava em todos os relatórios. Retorna (linhas de sucesso, linhas de erro)."""
    try:
        df = _ler(conteudo)
    except Exception as erro:
        return [], [f"{nome}: {erro}"]
    ok, erros = [], []
    for rotulo, funcao in _destinos():
        try:
            r = funcao(eng, nome, df, apoio_df=apoio_df, tem_extract=tem_extract)
            if r.get("ignorado"):
                ok.append(f"{rotulo}: {IGNORADO}")
            else:
                ok.append(f"{rotulo}: {r['novas']} novos · {r['atualizadas']} atualizados"
                          + (f" · {r['sem_apoio']} {AVISO_SEM_APOIO}" if r.get("sem_apoio") else ""))
        except ValueError as erro:                                    # coluna faltando etc.
            erros.append(f"{rotulo} · {nome}: {erro}")
        except Exception as erro:
            erros.append(f"{rotulo} · {nome}: {tx.ERRO_BANCO}{erro}")
    return ok, erros


def painel_carga(eng) -> list:
    """Barra lateral: histórico, banco em uso, envio do arquivo e botão salvar (igual nas três telas)."""
    st.sidebar.header(tx.HIST)
    st.sidebar.caption(f"{tx.BANCO_EM_USO}: {banco.descricao()}")
    arquivos = upload_persistente(CHAVE_UPLOAD, UPLOAD, ["xls", "xlsx"], UPLOAD_AJUDA)
    if arquivos:
        st.sidebar.caption(tx.PENDENTE)
        if st.sidebar.button(tx.SALVAR, type="primary", help=tx.SALVAR_AJUDA, key="cons_salvar"):
            salvos, ok_tudo, erros = [], [], []
            apoio_df, tem_extract = _contexto([(a.name, a.getvalue()) for a in arquivos])
            for arq in arquivos:                                      # cada arquivo é independente
                with st.spinner(SALVANDO + arq.name, show_time=True):
                    ok, err = _gravar(eng, arq.name, arq.getvalue(), apoio_df, tem_extract)
                ok_tudo += [f"{arq.name} → {linha}" for linha in ok]
                erros += err
                if ok and not err:                                    # só some da lista se foi para todos os relatórios
                    salvos.append(arq.name)
            # os arquivos continuam no envio: tela e Excel mostram sempre só o que foi enviado (para tirar, use o X do arquivo)
            st.session_state["cons_msg_ok"], st.session_state["cons_msg_erro"] = ok_tudo, erros
            st.rerun()
    for linha in st.session_state.pop("cons_msg_ok", []):
        st.sidebar.success(f"{tx.SALVO_OK} — {linha}")
    for linha in st.session_state.pop("cons_msg_erro", []):
        st.sidebar.error(linha)
    return arquivos or []
