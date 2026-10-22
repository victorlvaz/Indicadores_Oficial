"""Página: cadastro de líderes regionais (para cobrança e menções nas mensagens do Feishu)."""
import pandas as pd
import streamlit as st

from comum import banco, lideres
from comum.idioma import bi, cabecalho, frase

cabecalho("区域负责人", "Cadastro de líderes regionais")
st.write(frase("登记各区域负责人；成本催办消息会自动 @ 对应区域的负责人。",
               "Cadastre os líderes de cada regional. A mensagem de cobrança dos Custos menciona os líderes daqui."))
st.caption(frase("飞书ID（可选，格式 ou_…）：填写后 @ 才会真正提醒到本人；不填则只显示姓名文本。",
                 "ID do Feishu (opcional, formato ou_...): com ele a menção (@) avisa a pessoa de verdade; sem ele, sai só o nome em texto."))

try:
    eng = banco.engine()
    atual = lideres.ler(eng)
except Exception as erro:
    st.error(f"{bi('数据库错误', 'Erro no banco')}: {erro}")
    st.stop()

editado = st.data_editor(
    atual, num_rows="dynamic", hide_index=True, width="stretch", key="lid_editor",
    column_config={
        "regional": st.column_config.SelectboxColumn(bi("区域", "Regional"), options=lideres.REGIONAIS, required=True),
        "nome": st.column_config.TextColumn(bi("负责人", "Nome do líder"), required=True),
        "feishu_id": st.column_config.TextColumn(bi("飞书ID", "ID do Feishu (opcional)")),
    })

try:
    senha = str(st.secrets["feishu"].get("senha", "")).strip()
except Exception:
    senha = ""
liberado = True
if senha:
    liberado = st.text_input("密码 Senha", type="password", key="lid_senha") == senha

if st.button(bi("保存", "Salvar cadastro"), type="primary", disabled=not liberado):
    try:
        n = lideres.salvar(eng, editado)
        st.success(f"{bi('已保存', 'Salvo')}: {n}")
    except Exception as erro:
        st.error(f"{bi('保存失败', 'Não foi possível salvar')}: {erro}")
