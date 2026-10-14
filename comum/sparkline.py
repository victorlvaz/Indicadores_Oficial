"""Tabela de tendência com mini-gráficos de linha (estilo sparkline do Excel):
últimos dias em números + linha azul com pontos vermelhos nos últimos N dias.

Renderiza em HTML com estilos inline e mini-gráficos SVG embutidos como imagem, para funcionar no st.html.
"""
import base64
import html

from .tema import BORDA_TABELA as BORDA
from .tema import DESTAQUE_TOTAL as DESTAQUE
from .tema import LINHA_TENDENCIA as AZUL
from .tema import SOBRE_VERMELHO, VERMELHO

_NUM_CHINES = {2: "两", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}


def _pct(v) -> str:
    return "–" if v is None or v != v else f"{v * 100:.2f}".replace(".", ",") + "%"


def _svg(valores: list, largura=150, altura=34, margem=7, vmin=None, vmax=None) -> str:
    """Linha + pontos. Valores vazios (NaN) interrompem a linha."""
    ok = [v for v in valores if v == v]
    if not ok:
        return ""
    lo = min(ok) if vmin is None else vmin
    hi = max(ok) if vmax is None else vmax
    n = len(valores)

    def x(i):
        return margem + (i * (largura - 2 * margem) / (n - 1) if n > 1 else (largura - 2 * margem) / 2)

    def y(v):
        return altura / 2 if hi == lo else margem + (hi - v) / (hi - lo) * (altura - 2 * margem)

    trechos, atual = [], []
    for i, v in enumerate(valores):
        if v == v:
            atual.append((x(i), y(v)))
        elif atual:
            trechos.append(atual)
            atual = []
    if atual:
        trechos.append(atual)

    linhas = "".join(
        f'<polyline fill="none" stroke="{AZUL}" stroke-width="1.6" stroke-linejoin="round" '
        f'points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in t)}"/>'
        for t in trechos if len(t) > 1
    )
    pontos = "".join(
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.6" fill="{VERMELHO}"/>'
        for t in trechos for px, py in t
    )
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" '
           f'viewBox="0 0 {largura} {altura}">{linhas}{pontos}</svg>')
    # O st.html remove tags <svg> ao sanitizar o HTML; como imagem embutida (data URI) elas passam.
    dados = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (f'<img alt="" width="{largura}" height="{altura}" style="display:block;margin:auto" '
            f'src="data:image/svg+xml;base64,{dados}">')


def tabela_tendencia_html(t, n_dias: int = 6, n_valores: int = 2, escala_comum: bool = False) -> str:
    """t = saída de calculos.tendencia(): colunas [região, variação, acumulado, dd/mm, dd/mm, ...].
    Mostra os últimos `n_valores` dias em % e a linha dos últimos `n_dias` dias."""
    col_regiao = t.columns[0]
    dias = list(t.columns[3:])
    usados = dias[-n_dias:]
    mostrados = usados[-n_valores:]

    series = {i: [float(v) if v == v else float("nan") for v in t.loc[i, usados]] for i in t.index}
    vmin = vmax = None
    if escala_comum:
        todos = [v for s in series.values() for v in s if v == v]
        if todos:
            vmin, vmax = min(todos), max(todos)

    base = f"border:1px solid {BORDA};padding:5px 10px;text-align:center;"
    topo = f"background:{VERMELHO};color:{SOBRE_VERMELHO};"          # cabeçalho vermelho
    chines = _NUM_CHINES.get(len(usados), str(len(usados)))
    cab = f'<th style="{base}{topo}text-align:left">{html.escape(str(col_regiao))}</th>'
    cab += "".join(f'<th style="{base}{topo}font-weight:700">{html.escape(str(d))}</th>' for d in mostrados)
    cab += (f'<th style="{base}{topo}font-weight:700">近{chines}天趋势 '
            f'<span style="font-weight:400;font-size:12px">Últimos {len(usados)} dias</span></th>')

    linhas = []
    for pos, i in enumerate(t.index):
        destaque = pos == 0
        estilo = f"background:{DESTAQUE};font-weight:700;" if destaque else ""
        tds = f'<td style="{base}text-align:left;{estilo}">{html.escape(str(t.loc[i, col_regiao]))}</td>'
        tds += "".join(f'<td style="{base}{estilo}">{_pct(t.loc[i, d])}</td>' for d in mostrados)
        tds += f'<td style="{base}padding:2px 8px;{estilo}">{_svg(series[i], vmin=vmin, vmax=vmax)}</td>'
        linhas.append(f"<tr>{tds}</tr>")

    return (f'<table style="border-collapse:collapse;font-size:14px;margin:4px 0 12px">'
            f"<thead><tr>{cab}</tr></thead><tbody>{''.join(linhas)}</tbody></table>")
