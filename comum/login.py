"""Tela de login (usuário e senha únicos, definidos em Secrets) antes de qualquer relatório.

Secrets (local: .streamlit/secrets.toml · Cloud: Settings > Secrets):
    [login]
    usuario = "..."
    senha = "..."
"""
import base64
import hmac
import time

import streamlit as st

from comum.idioma import bi
from comum.logo import ARQUIVO, COR_CLARO, COR_ESCURO, PROPORCAO

CHAVE = "logado"
LARGURA_LOGO = 300


def _credenciais() -> tuple[str, str] | None:
    try:
        c = st.secrets["login"]
        u, s = str(c["usuario"]).strip(), str(c["senha"])
        return (u, s) if u and s else None
    except Exception:
        return None


def _logo_centro() -> str:
    dados = base64.b64encode(ARQUIVO.read_bytes()).decode()
    altura = round(LARGURA_LOGO / PROPORCAO)
    url = f"url(data:image/png;base64,{dados})"
    return f"""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
.login-logo {{ width: {LARGURA_LOGO}px; max-width: 80%; height: {altura}px; margin: 12vh auto 1.5rem;
    background-color: light-dark({COR_CLARO}, {COR_ESCURO});
    -webkit-mask: {url} center / contain no-repeat; mask: {url} center / contain no-repeat; }}
.login-titulo {{ text-align: center; margin: 0 0 1.25rem; opacity: .8; font-size: 1.05rem; }}
</style>
<div class="login-logo"></div>
<div class="login-titulo">{bi("指标", "Indicadores")}</div>
"""


def exigir_login() -> None:
    """Mostra a tela de login e PARA a execução enquanto a pessoa não entrar."""
    if st.session_state.get(CHAVE):
        return
    cred = _credenciais()
    st.html(_logo_centro())
    _, meio, _ = st.columns([1, 1.2, 1])
    with meio:
        if cred is None:
            st.error(f"{bi('未配置登录', 'Login não configurado')}: [login] usuario / senha em Secrets.")
            st.stop()
        with st.form("login", border=False):
            usuario = st.text_input(bi("用户", "Usuário"), key="login_usuario")
            senha = st.text_input(bi("密码", "Senha"), type="password", key="login_senha")
            entrou = st.form_submit_button(bi("登录", "Entrar"), type="primary", width="stretch")
        if entrou:
            ok_u = hmac.compare_digest(usuario.strip().encode(), cred[0].encode())
            ok_s = hmac.compare_digest(senha.encode(), cred[1].encode())
            if ok_u and ok_s:
                st.session_state[CHAVE] = True
                st.session_state.pop("login_senha", None)
                st.rerun()
            time.sleep(1)                                          # freia tentativas em sequência
            st.error(bi("用户或密码错误", "Usuário ou senha incorretos"))
    st.stop()


def botao_sair() -> None:
    if st.sidebar.button(bi("退出", "Sair"), key="login_sair", icon=":material/logout:"):
        st.session_state.pop(CHAVE, None)
        st.rerun()
