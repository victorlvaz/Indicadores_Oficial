"""Exporta as tabelas para .xlsx (valores, sem fórmulas; abre normalmente no WPS Office)."""
import io
import re

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .tema import SOBRE_VERMELHO, VERMELHO

VERMELHO_XLSX = "FF0000"                      # vermelho da planilha de referência (só no Excel exportado; a tela segue o tema)
FONTE = "Calibri"
PREENCHE_VERMELHO = PatternFill("solid", fgColor=VERMELHO_XLSX)
FONTE_SOBRE_VERMELHO = Font(name=FONTE, bold=True, color=SOBRE_VERMELHO.lstrip("#"))
FONTE_TITULO = Font(name=FONTE, bold=True, size=14, color=SOBRE_VERMELHO.lstrip("#"))
FONTE_NEGRITO = Font(name=FONTE, bold=True)
CABECALHO = PREENCHE_VERMELHO
CINZA_TOTAL = PatternFill("solid", fgColor="D9D9D9")


def _eh_numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v   # v == v exclui NaN


def _paragrafos(nota: str) -> str:
    """Texto chinês em parágrafos curtos: quebra de linha depois de cada frase terminada em 。"""
    return re.sub(r"。(?=[^\s])", "。\n", nota)


def periodo_texto(ini, fim, dias: pd.Series) -> str:
    """Data no formato chinês (mês primeiro): 10.18 ou 10.12-10.18. Sem período (Todos) usa o 1º e o último dia da base."""
    if ini is None:
        ini, fim = dias.min(), dias.max()
    ini, fim = pd.Timestamp(ini), pd.Timestamp(fim if fim is not None else ini)
    f = "%m.%d" if ini.year == fim.year else "%Y.%m.%d"
    return ini.strftime(f) if ini == fim else f"{ini.strftime(f)}-{fim.strftime(f)}"


def titulo_relatorio(arquivo_tela: str) -> str:
    """Nome bilíngue do relatório (o mesmo do menu), a partir do arquivo da página."""
    from relatorios import RELATORIOS
    return next((r["titulo"] for r in RELATORIOS if r["arquivo"] == arquivo_tela), "")


def para_excel(abas: dict[str, tuple[pd.DataFrame, dict]], titulo: str = "", periodo: str = "") -> bytes:
    """abas: {nome da aba: (dataframe, {"taxa": coluna, "meta": coluna} ou {})}
    titulo/periodo: se informados, cada aba de indicador ganha uma linha mesclada no topo (nome do relatório + data)."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for nome, item in abas.items():
            df, cols = item[0], item[1]
            nota = item[2] if len(item) > 2 else ""
            nome = nome[:31]
            o = 1 if (titulo and not cols.get("sem_pct") and not cols.get("sem_titulo")) else 0   # linhas acima do cabeçalho
            df.to_excel(writer, sheet_name=nome, index=False, startrow=o)
            ws = writer.sheets[nome]
            colunas = list(df.columns)
            if o:
                ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(colunas), 2))
                c = ws.cell(1, 1, " ".join(x for x in (f"{titulo} – {nome}", periodo) if x))
                c.font, c.fill = FONTE_TITULO, CABECALHO
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                ws.row_dimensions[1].height = 30

            for cel in ws[o + 1]:
                cel.font = FONTE_SOBRE_VERMELHO
                cel.fill = CABECALHO
                cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            for i, c in enumerate(colunas, start=1):
                eh_pct = df[c].dtype.kind == "f" and (c == cols.get("meta") or c == cols.get("taxa")
                                                     or c in cols.get("pct_extra", ()) or not cols)
                if eh_pct:
                    for cel in ws[get_column_letter(i)][o + 1:]:
                        cel.number_format = "0.00%"
                if c in cols.get("pp_extra", ()):                  # valores já em pontos percentuais
                    for cel in ws[get_column_letter(i)][o + 1:]:
                        cel.number_format = '+0.00" p.p.";-0.00" p.p.";0.00" p.p."'
                ws.column_dimensions[get_column_letter(i)].width = max(10, min(len(str(c)) // 2 + 6, 28))

            if ws.max_row >= o + 2 and not cols.get("sem_pct"):                               # linha de total (1ª): cinza e negrito
                for cel in ws[o + 2]:
                    cel.fill = CINZA_TOTAL
                    cel.font = FONTE_NEGRITO

            if cols.get("taxa") and cols.get("meta"):
                ct, cm = colunas.index(cols["taxa"]) + 1, colunas.index(cols["meta"]) + 1
                for r in range(o + 2, ws.max_row + 1):
                    t, m = ws.cell(r, ct).value, ws.cell(r, cm).value
                    # células vazias podem chegar como "" (texto): só pinta se ambas forem número
                    # abaixo da meta: vermelho; atingiu a meta: sem cor
                    if _eh_numero(t) and _eh_numero(m) and t < m:
                        ws.cell(r, ct).fill = PREENCHE_VERMELHO
                        ws.cell(r, ct).font = FONTE_SOBRE_VERMELHO
            if nota:                                              # rodapé centralizado, abaixo da tabela
                linha = ws.max_row + 2
                ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=max(len(colunas), 2))
                ws.cell(linha, 1, _paragrafos(nota)).alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
                ws.row_dimensions[linha].height = 15 * (_paragrafos(nota).count("\n") + 1)
            ws.freeze_panes = f"B{o + 2}"
    return buf.getvalue()


ABA_BASE_TRATADA = "已处理数据 Base tratada"
LIMITE_LINHAS_EXCEL = 1_048_575


def base_primeiro(export: dict, base: pd.DataFrame, nome: str = ABA_BASE_TRATADA) -> dict:
    """Devolve o export com a base já tratada (período escolhido) como PRIMEIRA aba do arquivo."""
    return {nome[:31]: (base.head(LIMITE_LINHAS_EXCEL), {"sem_pct": True}), **export}
