"""Mensagem padrão do Lacre/Deslacre para o grupo de transportes do Feishu: saudação e frases em português
e chinês, seguidas das 4 tabelas (Lacre/Deslacre de Coleta e Entrega) como imagem."""
from datetime import datetime, timedelta, timezone

import pandas as pd

from .config import INDICADORES

def _agora_brasil() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:                                   # Windows sem o pacote tzdata
        return datetime.now(timezone(timedelta(hours=-3)))


def saudacao(agora: datetime | None = None) -> str:
    h = (agora or _agora_brasil()).hour
    return "Bom dia a todos!" if h < 12 else "Boa tarde a todos!" if h < 18 else "Boa noite a todos!"


def periodo_frases(ini, fim) -> tuple[str, str]:
    """(português, chinês): "20/10/2026" / "2026年10月20日"; intervalo: "de 20/10/2026 a 26/10/2026" / "2026年10月20日至2026年10月26日"."""
    ini, fim = pd.Timestamp(ini), pd.Timestamp(fim if fim is not None else ini)
    zh = lambda d: f"{d.year}年{d.month}月{d.day}日"
    if ini == fim:
        return ini.strftime("%d/%m/%Y"), zh(ini)
    return f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y}", f"{zh(ini)}至{zh(fim)}"


def itens_mensagem(ini, fim, imagens: dict, agora: datetime | None = None) -> list:
    """Linhas e imagens na ordem do envio. imagens = {(tipo, evento): png_bytes}."""
    pt, zh = periodo_frases(ini, fim)
    prefixo = "do dia " if pt.count("/") == 2 else "do período "
    itens = [
        ("linha", [saudacao(agora)]),
        ("linha", ["Segue a Taxa de ", ("Lacre", True), " e ", ("Deslacre", True), " da Secundária " + prefixo, (pt, True), "."]),
        ("linha", ["以下是", (zh, True), "二次封签和拆签的费用。"]),
    ]
    for chave in INDICADORES:
        if chave in imagens:
            tipo, evento = chave
            itens.append(("linha", [evento.capitalize() + " ", (tipo, True), ":"]))
            itens.append(("imagem", imagens[chave]))
    return itens
