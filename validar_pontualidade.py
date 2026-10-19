"""Confere a Taxa de Chegada / Taxa de Saída calculadas pelo app contra as planilhas do analista.

Uso:  PYTHONPATH=. python validar_pontualidade.py <relatorio_consolidado.xls> <Taxa_de_Chegada.xlsx> <Taxa_de_Saida.xlsx> [AAAA-MM-DD]
Compara, para o dia pedido (padrão: o da planilha), total e atrasos por regional.
Diferenças pequenas são esperadas: a planilha foi gerada com uma extração mais antiga (trechos que
ainda estavam em trânsito viravam atraso) e o relatório de hoje tem horários reais que faltavam."""
import sys

import openpyxl
import pandas as pd

from pontualidade.calculos import ler_relatorio, preparar, visao
from pontualidade.config import TIPOS


def tabela_planilha(caminho, aba, dia=None):
    ws = openpyxl.load_workbook(caminho, data_only=True)[aba]
    out = {}
    for linha in ws.iter_rows(min_row=4, values_only=True):
        if linha[0] and isinstance(linha[1], (int, float)):
            out[linha[0]] = (int(linha[1]), int(linha[2]))
    return out


def main():
    rel, chegada, saida = sys.argv[1:4]
    dia = pd.Timestamp(sys.argv[4]) if len(sys.argv) > 4 else pd.Timestamp("2026-10-14")
    b, diag, _ = preparar(ler_relatorio(rel))
    for k, v in diag.items():
        print(f"  {k}: {v}")
    casos = [("CHEGADA", chegada, {"COLETA": "Taxa de Chegada-COLETA", "ENTREGA": "Taxa de Chegada-ENTREGA"}),
             ("SAIDA", saida, {"COLETA": "Taxa de Saída-COLETA", "ENTREGA": "Taxa de Saída-ENTREGA"})]
    for ind, arq, abas in casos:
        for tipo, aba in abas.items():
            plan = tabela_planilha(arq, aba)
            v = visao(b, ind, tipo)
            v = v[v["dia"] == dia]
            g = v.groupby("regiao")[["n_prev", "n_real"]].sum()
            print(f"\n{ind} {tipo} {dia.date()}   regional: planilha (total, atrasos)  |  app (total, atrasos)")
            for r in sorted(set(plan) | set(g.index)):
                p = plan.get(r, (0, 0))
                a = (int(g.loc[r, "n_prev"]), int(g.loc[r, "n_prev"] - g.loc[r, "n_real"])) if r in g.index else (0, 0)
                marca = "" if p == a else "  <- difere"
                print(f"  {r:4} {p!s:>12} | {a!s:>12}{marca}")


if __name__ == "__main__":
    main()
