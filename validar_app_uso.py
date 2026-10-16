"""Valida a Taxa de Uso de APP contra a planilha do Lucas.

    python validar_app_uso.py "Taxa_uso_de_APP_Outubro_13.10.xlsx" [relatorio_bruto.xls]

1) Lê a aba de base (支线运输综合报表) da planilha e compara, por dia e regional, a taxa calculada aqui com os
   valores salvos na aba 打卡率趋势 (colunas de data).
2) Se informar o relatório bruto (.xls do sistema), aplica as regras e compara o dia dele com a planilha.
"""
import sys
import warnings

import openpyxl
import pandas as pd

from app_uso.calculos import calcular_partes, ler_relatorio, preparar
from app_uso.config import COL, INDICADORES

warnings.filterwarnings("ignore")
ABA_TENDENCIA = "打卡率趋势Tendência da taxa de ponto"
LINHAS = {"COLETA": (3, 13), "ENTREGA": (16, 26)}      # linha do total .. última regional


def base_da_planilha(caminho):
    df = pd.read_excel(caminho, sheet_name="支线运输综合报表", header=0, skiprows=[1])
    # a planilha já vem filtrada: só aplica status/SC/franqueado por segurança (não muda nada)
    b, _ = preparar(df)
    return calcular_partes(b)


def comparar_tendencia(caminho, base):
    ws = openpyxl.load_workbook(caminho, data_only=True)[ABA_TENDENCIA]
    datas = {c: ws.cell(2, c).value for c in range(4, 35) if hasattr(ws.cell(2, c).value, "year")}
    dif, total = [], 0
    for tipo, (l0, l1) in LINHAS.items():
        col = INDICADORES[tipo]["regiao_col"]
        sub = base[base["tipo_linha"] == tipo]
        for r in range(l0, l1 + 1):
            nome = ws.cell(r, 1).value
            s = sub if nome == "合计" else sub[sub[col] == nome]
            for c, d in datas.items():
                v = ws.cell(r, c).value
                x = s[s["dia"] == pd.Timestamp(d)]
                calc = x["n_real"].sum() / x["n_prev"].sum() if len(x) else None
                if isinstance(v, (int, float)):
                    total += 1
                    if calc is None or abs(calc - float(v)) > 1e-9:
                        dif.append((tipo, nome, d.date(), v, calc))
                elif calc is not None and v is not None and str(v).startswith("#"):
                    dif.append((tipo, nome, d.date(), v, calc))
    return total, dif


if __name__ == "__main__":
    caminho = sys.argv[1]
    base = base_da_planilha(caminho)
    total, dif = comparar_tendencia(caminho, base)
    print(f"Tendência: {total} valores comparados, {len(dif)} divergências")
    for d in dif[:15]:
        print("  ", d)
    if len(sys.argv) > 2:
        bruto = ler_relatorio(sys.argv[2])
        b, diag = preparar(bruto)
        b = calcular_partes(b)
        print("Bruto →", diag)
        dia = b["dia"].max()
        for tipo in INDICADORES:
            s = b[(b["tipo_linha"] == tipo) & (b["dia"] == dia)]
            print(tipo, dia.date(), int(s["n_prev"].sum()), int(s["n_real"].sum()), round(s["n_real"].sum() / s["n_prev"].sum(), 4))
