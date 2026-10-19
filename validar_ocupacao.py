"""Valida a Taxa de Ocupação contra a planilha concluída: python validar_ocupacao.py <relatorio.xls> <planilha.xlsx> [AAAA-MM-DD]"""
import sys

import openpyxl
import pandas as pd

from ocupacao.calculos import completar, detalhe_veiculo, ler_relatorio, preparar, tabela_periodo

raw, plan = sys.argv[1], sys.argv[2]
dia = pd.Timestamp(sys.argv[3] if len(sys.argv) > 3 else "2026-10-14")
df = ler_relatorio(raw)
b, diag = preparar(df)
b = completar(b)
for k, v in diag.items():
    print(f"{k}: {v}")

wb = openpyxl.load_workbook(plan, data_only=True)
for tipo, aba in (("COLETA", "OCUPAÇÃO装载率COLETA"), ("ENTREGA", "OCUPAÇÃO装载率ENTREGA")):
    ws = wb[aba]
    linhas = [r for r in ws.iter_rows(values_only=True)]
    i0 = next(i for i, r in enumerate(linhas) if r[0] and str(r[0]).startswith("OCUPAÇÃO SECUND")) + 2
    esp = {}
    for r in linhas[i0:]:
        if r[0] is None:
            continue
        reg = "TOTAL" if str(r[0]).startswith("Total") else r[0]
        veic = (r[1] or "Total")
        esp[(reg, str(veic).upper())] = (r[2], r[3], r[4])        # viagens, carregado, previsto
    meu = detalhe_veiculo(b, tipo, dia, dia)
    ok = dif = 0
    for _, x in meu.iterrows():
        reg = "TOTAL" if x["regiao"].startswith("总合计") else x["regiao"]
        k = (reg, str(x["veiculo"]).upper())
        e = esp.get(k)
        if e is None:
            if x["viagens"]:
                print(tipo, "só no app:", k, x["viagens"], x["real"], x["prev"]); dif += 1
            continue
        if (e[0], round(e[1] or 0), round(e[2] or 0)) == (x["viagens"], round(x["real"]), round(x["prev"])):
            ok += 1
        else:
            dif += 1
            print(tipo, "DIFERE", k, "planilha", e, "app", (x["viagens"], round(x["real"]), round(x["prev"])))
    print(f"{tipo}: {ok} linhas iguais, {dif} diferentes")
    print(tabela_periodo(b, tipo, dia, dia).to_string())
