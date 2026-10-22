"""Botão "Enviar para o Feishu" reutilizável: abre uma janela com a prévia da mensagem (texto + imagens das tabelas),
caixas para saudação, comentário manual e Excel, e só posta no grupo depois do "Confirmar".

Cada página informa o que vai na mensagem (`abertura` e `blocos`); as imagens saem das MESMAS tabelas do Excel exportado
(`export`), então nada precisa ser calculado duas vezes."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from . import feishu
from .feishu_imagem import empilhar, tabela_png
from .idioma import bi, frase

BOTAO = bi("发送到飞书群", "Enviar para o Feishu")                                              # [revisar]
AJUDA = frase("把表格作为图片、并附上导出的 Excel，发送到运输群。", "Posta as tabelas como imagem, com o Excel exportado, no grupo de transportes.")   # [revisar]
PREVIA = frase("预览：将按此内容发送。", "Prévia: é exatamente isto que será postado no grupo.")  # [revisar]
SEM_CONFIG = ("Envio não configurado. Em Settings > Secrets do Streamlit (ou .streamlit/secrets.toml) crie o bloco [feishu] com "
              "app_id, app_secret e chat_id (veja comum/feishu.py).")
SENHA = bi("发送密码", "Senha de envio")                                                      # [revisar]
CONFIRMAR = bi("确认发送", "Confirmar envio")                                                 # [revisar]
ENVIANDO = "Enviando…"
ENVIADO = frase("已发送到飞书群。", "Mensagem enviada ao grupo.")                              # [revisar]
ERRO = "Não foi possível enviar: "
COM_SAUDACAO = "Incluir saudação (Bom dia / Boa tarde / Boa noite) / 包含问候语"                  # [revisar]
COM_EXCEL = "Enviar também o Excel exportado (em uma 2ª mensagem) / 同时发送导出的 Excel（第二条消息）"      # [revisar]
COMENTARIO = "Comentário (opcional, entra na mensagem; uma frase por linha) / 备注（可选）"        # [revisar]


def _agora_brasil() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:                                   # Windows sem o pacote tzdata
        return datetime.now(timezone(timedelta(hours=-3)))


def saudacao(agora: datetime | None = None) -> str:
    h = (agora or _agora_brasil()).hour
    return "Bom dia a todos!" if h < 12 else "Boa tarde a todos!" if h < 18 else "Boa noite a todos!"


def periodo_frases(ini, fim) -> tuple[str, str, bool]:
    """(português, chinês, é_dia_único). Data completa: "20/10/2026" / "2026年10月20日"; intervalo: "20/10/2026 a 26/10/2026"."""
    ini, fim = pd.Timestamp(ini), pd.Timestamp(fim if fim is not None else ini)
    zh = lambda d: f"{d.year}年{d.month}月{d.day}日"
    if ini == fim:
        return ini.strftime("%d/%m/%Y"), zh(ini), True
    return f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y}", f"{zh(ini)}至{zh(fim)}", False


def _partes(texto: str) -> list:
    """"a **b** c" -> ["a ", ("b", True), " c"]: o que está entre ** fica em negrito."""
    return [(t, True) if i % 2 else t for i, t in enumerate(texto.split("**")) if t != ""]


def _com_data(modelo: str, valor: str, unico: bool) -> list:
    """Troca "{d}" pela data (em negrito); num intervalo, "dia {d}" vira "período {d}". Aceita ** para negrito."""
    if not unico:
        modelo = modelo.replace("dia {d}", "período {d}")
    return _partes(modelo.replace("{d}", f"**{valor}**"))


def montar_itens(*, ini, fim, dias, export, titulo, periodo_xl, abertura, blocos, saudar: bool, comentario: str) -> list:
    """Linhas e imagens, na ordem do envio.
    abertura = (frase em português com "{d}", frase em chinês com "{d}").
    blocos   = [("linha", "texto com **negrito**") | ("img", [partes do rótulo], [chaves do export]) | ("comentario",)]; sem ("comentario",) o texto vai no fim."""
    if ini is None:
        ini, fim = dias.min(), dias.max()
    pt, zh, unico = periodo_frases(ini, fim)
    itens = []
    if saudar:
        itens.append(("linha", [saudacao()]))
    itens.append(("linha", _com_data(abertura[0], pt, unico)))
    itens.append(("linha", _com_data(abertura[1], zh, True)))
    linhas_comentario = [("linha", [t]) for t in (comentario or "").splitlines() if t.strip()]
    comentou = False
    for bloco in blocos:
        if bloco[0] == "linha":
            itens.append(("linha", _partes(bloco[1]) if isinstance(bloco[1], str) else bloco[1]))
        elif bloco[0] == "linhas":                                   # linhas já prontas (ex.: cobrança com menções)
            itens.extend(bloco[1])
        elif bloco[0] == "comentario":
            itens.extend(linhas_comentario)
            comentou = True
        else:
            _, rotulo, chaves = bloco
            pngs = []
            for k in chaves:
                if k in export:
                    df, cols = export[k][0], export[k][1]
                    pngs.append(tabela_png(df, " – ".join(x for x in (titulo, cols.get("titulo_img") or k) if x) + (f" {periodo_xl}" if periodo_xl else ""), cols))
            if pngs:
                if rotulo:
                    itens.append(("linha", _partes(rotulo) if isinstance(rotulo, str) else rotulo))
                itens.append(("imagem", empilhar(pngs)))
    if not comentou:
        itens.extend(linhas_comentario)
    return itens


def _texto_previa(linha) -> str:
    def um(p):
        if isinstance(p, str):
            return p
        if len(p) == 3:
            return f"**@{p[1]}**"
        return f"**{p[0]}**" if p[1] else p[0]
    return "".join(um(p) for p in linha)


@st.dialog(BOTAO, width="large")
def _dialogo(chave: str, parametros: dict, nome_xl: str, excel):
    cfg = feishu.configuracao(st.secrets)
    saudar = st.checkbox(COM_SAUDACAO, value=False, key=f"{chave}_bot_saudar")
    comentario = st.text_area(COMENTARIO, key=f"{chave}_bot_comentario", height=90)
    itens = montar_itens(saudar=saudar, comentario=comentario, **parametros)
    st.caption(PREVIA)
    for tipo, valor in itens:
        if tipo == "imagem":
            st.image(valor)
        else:
            st.markdown(_texto_previa(valor))
    if cfg is None:
        st.warning(SEM_CONFIG)
        return
    senha_ok = True
    if str(cfg.get("senha", "")).strip():
        senha_ok = st.text_input(SENHA, type="password", key=f"{chave}_bot_senha") == str(cfg["senha"])
    com_excel = st.checkbox(COM_EXCEL, value=True, key=f"{chave}_bot_excel")
    sinal = (parametros["periodo_xl"], str(parametros["ini"]))
    ja_enviou = st.session_state.get(f"{chave}_bot_enviado") == sinal
    if ja_enviou:
        st.success(ENVIADO)
    if st.button(CONFIRMAR, type="primary", disabled=ja_enviou or not senha_ok, key=f"{chave}_bot_confirmar"):
        try:
            with st.spinner(ENVIANDO):
                feishu.enviar_relatorio(cfg, itens, (nome_xl, excel()) if com_excel else None)
            st.session_state[f"{chave}_bot_enviado"] = sinal
            st.rerun(scope="fragment")
        except Exception as erro:
            st.error(ERRO + str(erro))


def botao(*, chave: str, ini, fim, dias: pd.Series, export: dict, titulo: str, periodo_xl: str,
          nome_xl: str, excel, abertura: tuple, blocos: list) -> None:
    """Coloca o botão na barra lateral (use logo abaixo do botão de exportar).
    excel = função sem argumentos que devolve os bytes do .xlsx exportado."""
    if st.sidebar.button(BOTAO, key=f"{chave}_bot_abrir", help=AJUDA, width="stretch"):
        st.session_state.pop(f"{chave}_bot_enviado", None)            # abrir de novo permite um novo envio
        _dialogo(chave, dict(ini=ini, fim=fim, dias=dias, export=export, titulo=titulo, periodo_xl=periodo_xl,
                             abertura=abertura, blocos=blocos), nome_xl, excel)
