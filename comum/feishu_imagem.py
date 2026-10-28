"""Desenha qualquer tabela de indicador como imagem PNG, no visual da planilha exportada:
título vermelho, cabeçalho bilíngue (chinês em cima, português embaixo), linhas de total em cinza e
taxa abaixo da meta em vermelho. Usada para postar as tabelas no Feishu.

Recebe o mesmo par (DataFrame, metadados) que alimenta o Excel exportado, então todos os relatórios usam o mesmo caminho:
  metadados {"taxa": coluna, "meta": coluna, "pct_extra": [...], "pp_extra": [...]}  ou  {} (tabelas de tendência/detalhe).
"""
import io
import os
import re
from functools import lru_cache

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

VERMELHO = (255, 0, 0)                    # FF0000, o mesmo vermelho do Excel exportado
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
CINZA_TOTAL = (217, 217, 217)             # D9D9D9
CINZA_LINHA = (191, 191, 191)

# Onde procurar as fontes (Windows, Linux/Streamlit Cloud). packages.txt instala as do Linux.
_LATINA = {
    False: ["C:/Windows/Fonts/calibri.ttf", "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf"],
    True: ["C:/Windows/Fonts/calibrib.ttf", "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf"],
}
_CJK = {
    False: ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyh.ttf", "C:/Windows/Fonts/simsun.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "/System/Library/Fonts/PingFang.ttc"],
    True: ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyhbd.ttf", "C:/Windows/Fonts/simhei.ttf",
           "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
           "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "/System/Library/Fonts/PingFang.ttc"],
}


@lru_cache(maxsize=64)
def _fonte(cjk: bool, negrito: bool, tam: int):
    for caminho in (_CJK if cjk else _LATINA)[negrito]:
        if os.path.exists(caminho):
            try:
                return ImageFont.truetype(caminho, tam)
            except OSError:
                continue
    raise RuntimeError("Nenhuma fonte " + ("chinesa" if cjk else "latina") + " encontrada para desenhar a tabela. "
                       "No Streamlit Cloud inclua packages.txt com fonts-noto-cjk e fonts-crosextra-carlito.")


def _eh_cjk(ch: str) -> bool:
    o = ord(ch)
    return o >= 0x2E80 and not (0x2000 <= o <= 0x206F)


def _trechos(texto: str):
    """Quebra o texto em trechos de mesma família de fonte: [(texto, é_chinês), ...]."""
    out = []
    for ch in texto:
        c = _eh_cjk(ch)
        if out and out[-1][1] == c:
            out[-1][0] += ch
        else:
            out.append([ch, c])
    return out


def _largura(texto: str, negrito: bool, tam: int) -> int:
    return int(sum(_fonte(c, negrito, tam).getlength(t) for t, c in _trechos(texto)))


def _desenhar(d: ImageDraw.ImageDraw, caixa, texto: str, cor, negrito: bool, tam: int, alinha: str, pad: int):
    """Escreve `texto` centralizado na vertical dentro da caixa (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = caixa
    larg = _largura(texto, negrito, tam)
    x = x0 + pad if alinha == "l" else x1 - pad - larg if alinha == "r" else x0 + (x1 - x0 - larg) / 2
    meio = (y0 + y1) / 2
    for t, c in _trechos(texto):
        f = _fonte(c, negrito, tam)
        d.text((x, meio), t, font=f, fill=cor, anchor="lm")
        x += f.getlength(t)


# ---------- formatação ----------
def _pct(v, sinal=False) -> str:
    if pd.isna(v):
        return ""
    return (f"{v * 100:+.2f}" if sinal else f"{v * 100:.2f}").replace(".", ",") + "%"


def _pp(v) -> str:
    return "" if pd.isna(v) else f"{v:+.2f}".replace(".", ",") + " p.p."


def _numero(v) -> str:
    if pd.isna(v):
        return ""
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.2f}".replace(".", ",")


def _milhar(v, casas=0) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _formatador_custos(df: pd.DataFrame, cols: dict):
    """Custos: valores em R$ (frete, frete/pacote, frete/KM), números com ponto de milhar e variações em p.p."""
    pp_cols = set(cols.get("pp_extra", ()))

    def fmt(c, j, v):
        if c in pp_cols:
            return _pp(v)
        if isinstance(v, str):
            return v
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            nome = str(c)
            if any(k in nome for k in ("运费", "成本", "Frete", "frete")):
                return "R$ " + _milhar(v, 2)
            return _milhar(v, 0 if float(v).is_integer() else 2)
        return str(v)
    return fmt


def _formatador(df: pd.DataFrame, cols: dict):
    """Devolve f(coluna, índice_da_coluna, valor) -> texto."""
    if cols.get("custos"):
        return _formatador_custos(df, cols)
    pct_cols = {cols.get("taxa"), cols.get("meta"), *cols.get("pct_extra", ())} - {None}
    pp_cols = set(cols.get("pp_extra", ()))
    reais_cols = set(cols.get("reais", ()))
    sem_meta = not cols

    def eh_taxa(c) -> bool:
        s = df[c]
        if s.dtype.kind != "f":
            return False
        vals = s.dropna()
        return len(vals) > 0 and bool((vals.abs() <= 10).all()) and not bool((vals.round(0) == vals).all())

    def fmt(c, j, v):
        if c in pp_cols:
            return _pp(v)
        if c in reais_cols:
            return "" if pd.isna(v) else "R$ " + _milhar(v, 2)
        if c in pct_cols:
            return _pct(v)
        if isinstance(v, (pd.Timestamp,)) or hasattr(v, "strftime"):
            return "" if pd.isna(v) else v.strftime("%d/%m/%Y")
        if isinstance(v, str):
            return v
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if sem_meta and df[c].dtype.kind == "f" and eh_taxa(c):          # tendência: taxas; a 2ª coluna é a variação, com sinal
                return _pct(v, sinal=(j == 1))
            if df[c].dtype.kind == "f" and eh_taxa(c):
                return _pct(v)
            return _numero(v)
        return str(v)
    return fmt


SPARK_AZUL = (55, 96, 146)                 # 376092, Estilo de Mini Gráfico Escuro #5
SPARK_PONTO = (208, 0, 0)                  # D00000
COL_SPARK = "近七天趋势 Tendência 7 dias"


def _sparkline(d, caixa, valores, s: int):
    """Mini gráfico de linha (vermelho, com o último ponto marcado) dentro da célula."""
    x0, y0, x1, y1 = caixa
    pts = [(k, v) for k, v in enumerate(valores) if v == v]
    if len(pts) < 2:
        return
    lo, hi = min(v for _, v in pts), max(v for _, v in pts)
    mx, my = 10 * s, 5 * s
    n = len(valores) - 1

    def xy(k, v):
        y = (y0 + y1) / 2 if hi == lo else y1 - my - (v - lo) / (hi - lo) * (y1 - y0 - 2 * my)
        return (x0 + mx + k / n * (x1 - x0 - 2 * mx), y)
    xs = [xy(k, v) for k, v in pts]
    d.line(xs, fill=SPARK_AZUL, width=max(2, s))
    r = int(1.6 * s)
    for ux, uy in xs:                                           # um ponto em cada período, como no estilo Escuro #5
        d.ellipse([ux - r, uy - r, ux + r, uy + r], fill=SPARK_PONTO)


def _cabecalho_2_linhas(nome: str) -> tuple[str, str]:
    """"发车区域 Região Saída" -> ("发车区域", "Região Saída"); "Regional de Origem发出代理区" -> ("发出代理区", "Regional de Origem")."""
    nome = str(nome).strip()
    if not any(_eh_cjk(c) for c in nome):
        return "", nome
    zh = "".join(t for t, c in _trechos(nome) if c).strip()
    resto = re.sub(r"\s+", " ", "".join(t for t, c in _trechos(nome) if not c)).strip()
    return zh, resto


def tabela_png(df: pd.DataFrame, titulo: str, cols: dict | None = None, escala: int = 2) -> bytes:
    """Uma tabela como PNG. `cols` = metadados do export ({"taxa":..., "meta":...} ou {}); linhas de total ficam em cinza."""
    quer_spark = bool((cols or {}).get("sparkline"))
    cols = {k: v for k, v in (cols or {}).items() if k != "sparkline"}
    s = escala
    tam, tam_t = 13 * s, 16 * s
    pad, alt_lin, alt_tit = 7 * s, 23 * s, 34 * s
    df = df.reset_index(drop=True)
    df = df.loc[:, ~df.isna().all()]                              # colunas sem nenhum dado (ex.: comparação de um dia só) ficam de fora
    colunas = list(df.columns)
    dados_spark = None
    if quer_spark and len(colunas) >= 4:                           # sparkline dos últimos 7 períodos, como no Excel
        dados_spark = df[colunas[max(3, len(colunas) - 7):]].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    fmt = _formatador(df, cols)
    celulas = [[fmt(c, j, df.iloc[i][c]) for j, c in enumerate(colunas)] for i in range(len(df))]
    eh_texto = [bool(df[c].map(lambda v: isinstance(v, str)).any()) for c in colunas]
    cabec = [_cabecalho_2_linhas(c) for c in colunas]
    if dados_spark is not None:
        colunas.append(COL_SPARK)
        for lin in celulas:
            lin.append("")
        eh_texto.append(False)
        cabec.append(_cabecalho_2_linhas(COL_SPARK))

    def linha_total(i: int) -> bool:
        return i == 0 or any(("Total" in t or "合计" in t) for t in celulas[i][:2])

    larguras = []
    for j in range(len(colunas)):
        w = max([_largura(t, True, tam) for t in cabec[j] if t] + [_largura(celulas[i][j], linha_total(i), tam) for i in range(len(df))] + [0])
        larguras.append(w + 2 * pad)
    if dados_spark is not None:
        larguras[-1] = max(larguras[-1], 90 * s)
    total_w = sum(larguras)
    alt_cab = 2 * alt_lin if any(c[0] for c in cabec) else alt_lin
    larg_titulo = _largura(titulo, True, tam_t) + 4 * pad
    if larg_titulo > total_w:                                  # título mais largo que a tabela: alarga a 1ª coluna de texto
        alvo = next((j for j in range(len(colunas)) if eh_texto[j]), 0)
        larguras[alvo] += larg_titulo - total_w
        total_w = larg_titulo
    altura = alt_tit + alt_cab + alt_lin * len(df) + 1

    img = Image.new("RGB", (total_w + 1, altura), BRANCO)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, total_w, alt_tit], fill=VERMELHO)
    _desenhar(d, (0, 0, total_w, alt_tit), titulo, BRANCO, True, tam_t, "c", pad)

    x = 0
    y0, y1 = alt_tit, alt_tit + alt_cab
    for j, w in enumerate(larguras):
        d.rectangle([x, y0, x + w, y1], fill=VERMELHO, outline=BRANCO)
        zh, pt = cabec[j]
        if zh:
            _desenhar(d, (x, y0, x + w, y0 + alt_cab / 2), zh, BRANCO, True, tam, "c", pad)
            _desenhar(d, (x, y0 + alt_cab / 2, x + w, y1), pt, BRANCO, True, tam, "c", pad)
        else:
            _desenhar(d, (x, y0, x + w, y1), pt, BRANCO, True, tam, "c", pad)
        x += w

    taxa, meta = cols.get("taxa"), cols.get("meta")
    for i in range(len(df)):
        y0 = alt_tit + alt_cab + i * alt_lin
        y1 = y0 + alt_lin
        x = 0
        for j, w in enumerate(larguras):
            fundo, cor, negrito = (CINZA_TOTAL if linha_total(i) else BRANCO), PRETO, linha_total(i)
            if taxa and meta and colunas[j] == taxa:
                t, m = df.iloc[i][taxa], df.iloc[i][meta]
                if isinstance(t, (int, float)) and isinstance(m, (int, float)) and pd.notna(t) and pd.notna(m) and t < m:
                    fundo, cor, negrito = VERMELHO, BRANCO, True          # abaixo da meta: vermelho, texto branco
            d.rectangle([x, y0, x + w, y1], fill=fundo, outline=CINZA_LINHA)
            texto_cel = celulas[i][j]
            alinha = "l" if (eh_texto[j] and not texto_cel.replace(",", "").replace(".", "").replace("%", "").strip().isdigit()) else "r"
            _desenhar(d, (x, y0, x + w, y1), texto_cel, cor, negrito, tam, alinha, pad)
            if dados_spark is not None and j == len(larguras) - 1:
                _sparkline(d, (x, y0, x + w, y1), dados_spark[i], s)
            x += w

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def empilhar(pngs: list[bytes], espaco: int = 12) -> bytes:
    """Junta várias imagens (ex.: tendência de Coleta e de Entrega) numa só, uma sobre a outra."""
    if len(pngs) == 1:
        return pngs[0]
    ims = [Image.open(io.BytesIO(p)).convert("RGB") for p in pngs]
    larg = max(i.width for i in ims)
    alt = sum(i.height for i in ims) + espaco * (len(ims) - 1)
    out = Image.new("RGB", (larg, alt), BRANCO)
    y = 0
    for i in ims:
        out.paste(i, (0, y))
        y += i.height + espaco
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
