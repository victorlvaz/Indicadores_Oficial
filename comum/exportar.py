"""Exporta as tabelas para .xlsx (valores, sem fórmulas; abre normalmente no WPS Office)."""
import io

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .tema import SOBRE_VERMELHO, VERMELHO

PREENCHE_VERMELHO = PatternFill("solid", fgColor=VERMELHO.lstrip("#"))
FONTE_SOBRE_VERMELHO = Font(bold=True, color=SOBRE_VERMELHO.lstrip("#"))
CABECALHO = PREENCHE_VERMELHO
CINZA_TOTAL = PatternFill("solid", fgColor="D9D9D9")


def _eh_numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v   # v == v exclui NaN


def para_excel(abas: dict[str, tuple[pd.DataFrame, dict]]) -> bytes:
    """abas: {nome da aba: (dataframe, {"taxa": coluna, "meta": coluna} ou {})}"""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for nome, item in abas.items():
            df, cols = item[0], item[1]
            nota = item[2] if len(item) > 2 else ""
            nome = nome[:31]
            df.to_excel(writer, sheet_name=nome, index=False)
            ws = writer.sheets[nome]
            colunas = list(df.columns)

            for cel in ws[1]:
                cel.font = FONTE_SOBRE_VERMELHO
                cel.fill = CABECALHO
                cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            for i, c in enumerate(colunas, start=1):
                eh_pct = df[c].dtype.kind == "f" and (c == cols.get("meta") or c == cols.get("taxa")
                                                     or c in cols.get("pct_extra", ()) or not cols)
                if eh_pct:
                    for cel in ws[get_column_letter(i)][1:]:
                        cel.number_format = "0.00%"
                if c in cols.get("pp_extra", ()):                  # valores já em pontos percentuais
                    for cel in ws[get_column_letter(i)][1:]:
                        cel.number_format = '+0.00" p.p.";-0.00" p.p.";0.00" p.p."'
                ws.column_dimensions[get_column_letter(i)].width = max(10, min(len(str(c)) // 2 + 6, 28))

            if ws.max_row >= 2 and not cols.get("sem_pct"):                                   # linha de total (1ª): cinza e negrito
                for cel in ws[2]:
                    cel.fill = CINZA_TOTAL
                    cel.font = Font(bold=True)

            if cols.get("taxa") and cols.get("meta"):
                ct, cm = colunas.index(cols["taxa"]) + 1, colunas.index(cols["meta"]) + 1
                for r in range(2, ws.max_row + 1):
                    t, m = ws.cell(r, ct).value, ws.cell(r, cm).value
                    # células vazias podem chegar como "" (texto): só pinta se ambas forem número
                    # abaixo da meta: vermelho; atingiu a meta: sem cor
                    if _eh_numero(t) and _eh_numero(m) and t < m:
                        ws.cell(r, ct).fill = PREENCHE_VERMELHO
                        ws.cell(r, ct).font = FONTE_SOBRE_VERMELHO
            if nota:                                              # rodapé centralizado, abaixo da tabela
                linha = ws.max_row + 2
                ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=max(len(colunas), 2))
                ws.cell(linha, 1, nota).alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
                ws.row_dimensions[linha].height = 15 * (nota.count("\n") + 1)
            ws.freeze_panes = "B2"
    return buf.getvalue()
