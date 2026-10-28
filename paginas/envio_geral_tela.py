"""Página: Envio geral – manda no bot do Feishu todos os indicadores com JMS, um de cada vez (indicador, depois arquivo)."""
from datetime import timedelta

import pandas as pd
import streamlit as st

from comum import envio_geral as eg, feishu, feishu_envio as fe, periodos
from comum.idioma import bi, cabecalho

cabecalho("发送汇总", "Envio geral")

NOMES = {"D": bi("日", "Dia"), "W": bi("周", "Semana"), "M": bi("月", "Mês"), "Y": bi("年", "Ano")}
hoje = fe._agora_brasil().date()


def _padrao(g: str):
    """Segunda-feira reporta a última semana fechada; mês = mês anterior; dia = ontem."""
    if g == "D":
        return hoje - timedelta(days=1)
    if g == "W":
        return hoje - timedelta(days=((hoje.weekday() - 5) % 7) or 7)      # último sábado já passado
    if g == "M":
        return hoje.replace(day=1) - timedelta(days=1)
    return hoje


st.caption(bi("按所选周期依次发送：指标、文件；某项失败不影响后续，失败项可单独重发。",
              "Envia na ordem indicador → arquivo. Se um falhar, segue para o próximo; os que falharem podem ser reenviados."))
c1, c2 = st.columns([1, 2])
gran = c1.radio(bi("周期", "Formato do período"), periodos.GRANULARIDADES, horizontal=True, format_func=NOMES.get, key="eg_gran")
data_ref = c2.date_input(bi("参考日期", "Data de referência (qualquer dia do período)"), value=_padrao(gran),
                         format="DD/MM/YYYY", key=f"eg_data_{gran}")
ini = periodos.inicio(pd.Series([pd.Timestamp(data_ref)]), gran).iloc[0]
fim = periodos.fim(ini, gran)
st.info(bi("将发送：", "Período a enviar: ") + f"**{periodos.rotulo(ini, gran)}**  ·  {ini:%d/%m/%Y} → {fim:%d/%m/%Y}")

escolhidos = st.multiselect(bi("指标", "Indicadores"), [i[0] for i in eg.INDICADORES], default=[i[0] for i in eg.INDICADORES],
                            format_func=lambda k: next(bi(i[2], i[1]) for i in eg.INDICADORES if i[0] == k), key="eg_sel")
saudar = st.checkbox(fe.COM_SAUDACAO + " (só na 1ª mensagem)", value=False, key="eg_saudar")
com_excel = st.checkbox(fe.COM_EXCEL, value=True, key="eg_excel")
com_base = st.checkbox(fe.COM_BASE, value=True, key="eg_base", disabled=not com_excel)

assinatura = (gran, str(ini), tuple(escolhidos))
if st.button(bi("生成预览", "Gerar prévia"), type="primary", disabled=not escolhidos, key="eg_gerar"):
    prev, res = {}, {}
    with st.status(bi("正在准备…", "Preparando os indicadores…"), expanded=True) as estado:
        for id_, pt, zh, pagina, pref, extras in eg.INDICADORES:
            if id_ not in escolhidos:
                continue
            st.write(f"⏳ {pt}")
            try:
                prev[id_] = eg.capturar(pagina, pref, extras, gran, ini)
            except Exception as erro:
                res[id_] = ("erro", "Preparo: " + str(erro))
        estado.update(label=bi("预览已就绪", "Prévia pronta"), state="complete", expanded=False)
    st.session_state["eg_prev"], st.session_state["eg_res"], st.session_state["eg_ass"] = prev, res, assinatura
    for k in [k for k in st.session_state if k.startswith("eg_com_")]:
        del st.session_state[k]

prev = st.session_state.get("eg_prev")
if not prev and not st.session_state.get("eg_res"):
    st.stop()
if st.session_state.get("eg_ass") != assinatura:
    st.warning(bi("周期或指标已更改，请重新生成预览。", "O período ou a seleção mudou: gere a prévia novamente."))
    st.stop()

res = st.session_state["eg_res"]
nomes = {i[0]: i[1] for i in eg.INDICADORES}


def _itens(id_: str, com_saudacao: bool) -> list:
    return eg.itens_finais(prev[id_], com_saudacao, st.session_state.get(f"eg_com_{id_}", ""))


# ---------- Prévia completa ----------
st.subheader(bi("预览", "Prévia"))
for id_ in prev:
    with st.expander(nomes[id_], expanded=False):
        st.text_area(fe.COMENTARIO, key=f"eg_com_{id_}", height=70)
        for tipo, valor in _itens(id_, saudar and id_ == next(iter(prev))):
            if tipo == "imagem":
                st.image(valor)
            else:
                st.markdown(fe._texto_previa(valor))
        st.caption("📎 " + prev[id_]["nome_xl"])
for id_, r in res.items():
    if id_ not in prev:
        st.error(f"❌ {nomes[id_]} — {r[1]}")

# ---------- Envio ----------
cfg = feishu.configuracao(st.secrets)
if cfg is None:
    st.warning(fe.SEM_CONFIG)
    st.stop()
senha_ok = True
if str(cfg.get("senha", "")).strip():
    senha_ok = st.text_input(fe.SENHA, type="password", key="eg_senha") == str(cfg["senha"])
cfg, destino_ok = fe.escolher_destino(cfg, "eg")
senha_ok = senha_ok and destino_ok


def _enviar(ids: list) -> None:
    primeiro = not any(r[0] == "ok" for r in res.values())
    barra = st.progress(0.0)
    for n, id_ in enumerate(ids):
        barra.progress(n / len(ids), text=f"{nomes[id_]}…")
        try:
            cap = prev[id_]
            arquivo = None
            if com_excel:
                arquivo = (cap["nome_xl"], cap["xl"] if com_base else cap["xl_sem_base"])
            feishu.enviar_relatorio(cfg, _itens(id_, saudar and primeiro), arquivo)
            res[id_] = ("ok",)
            primeiro = False
        except Exception as erro:
            res[id_] = ("erro", str(erro).split("[SQL:")[0].strip()[:400])
    barra.empty()


pendentes = [i for i in prev if res.get(i, ("",))[0] != "ok"]
falhas = [i for i in prev if res.get(i, ("",))[0] == "erro"]
b1, b2 = st.columns(2)
if b1.button(bi("全部发送", "Enviar todos") + f" ({len(pendentes)})", type="primary",
             disabled=not senha_ok or not pendentes, key="eg_enviar"):
    _enviar(pendentes)
    st.rerun()
if b2.button(bi("重发失败项", "Reenviar os que falharam") + f" ({len(falhas)})", disabled=not senha_ok or not falhas, key="eg_reenviar"):
    _enviar(falhas)
    st.rerun()

# ---------- Confirmação ----------
if res:
    st.subheader(bi("发送结果", "Resultado"))
    for id_ in [i[0] for i in eg.INDICADORES if i[0] in res or i[0] in prev]:
        r = res.get(id_)
        if r is None:
            st.markdown(f"⏺️ **{nomes[id_]}** — {bi('待发送', 'ainda não enviado')}")
        elif r[0] == "ok":
            st.markdown(f"✅ **{nomes[id_]}** — {bi('已发送', 'enviado (mensagem + arquivo)')}")
        else:
            st.markdown(f"❌ **{nomes[id_]}** — {r[1]}")
