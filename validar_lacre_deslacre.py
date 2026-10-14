"""Valida o cálculo em Python contra os valores salvos na planilha finalizada.

    python validar_lacre_deslacre.py "planilha_finalizada.xlsx"

Sem argumento, procura na pasta do projeto um .xlsx que tenha a aba de base
(支线运输综合报表) e usa esse arquivo.

Lê a aba de base da planilha, aplica as mesmas regras e compara previsto/realizado de
cada região nas 4 abas (Coleta/Entrega x Lacre/Deslacre) para o dia da célula H1.
"""
import sys
import warnings
from pathlib import Path

import openpyxl
import pandas as pd

from lacre_deslacre.calculos import ler_relatorio, preparar, tabela_dia
from lacre_deslacre.config import INDICADORES

warnings.filterwarnings("ignore")

ABAS = {
    ("COLETA", "lacre"): "集货封车LACRE-COLETA",
    ("COLETA", "deslacre"): "集货解车DESLACRE-COLETA",
    ("ENTREGA", "lacre"): "散货封车LACRE-ENTEGA",
    ("ENTREGA", "deslacre"): "散货解车DESLACRE-ENTREGA",
}


ABA_BASE = "支线运输综合报表"


def achar_planilha() -> str | None:
    """Procura na pasta do script um .xlsx que contenha a aba de base."""
    candidatos = []
    for arq in sorted(Path(__file__).parent.glob("*.xlsx")):
        if arq.name.startswith("~$"):
            continue
        try:
            wb = openpyxl.load_workbook(arq, read_only=True)
            if ABA_BASE in wb.sheetnames:
                candidatos.append(arq)
            wb.close()
        except Exception:
            pass
    if len(candidatos) == 1:
        print("Usando a planilha encontrada na pasta:", candidatos[0].name)
        return str(candidatos[0])
    return None


def main(caminho: str) -> int:
    wb = openpyxl.load_workbook(caminho, data_only=True)
    bruto = ler_relatorio(caminho, sheet_name=ABA_BASE)
    base, diag = preparar(bruto)
    print("Diagnóstico:", diag)

    erros = comparados = 0
    for chave, aba in ABAS.items():
        ws = wb[aba]
        dia = pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(ws["H1"].value))
        tab = tabela_dia(base, *chave, dia).set_index("regiao")
        for r in range(3, ws.max_row + 1):
            reg, prev, real = ws.cell(r, 2).value, ws.cell(r, 3).value, ws.cell(r, 4).value
            if reg is None:
                continue
            reg = "合计 Total" if reg == "合计" else reg
            py = tab.loc[reg]
            comparados += 1
            if (py["prev"], py["real"]) != (prev, real):
                erros += 1
                print(f"DIFERE {chave} {reg}: planilha {prev}/{real} vs python {py['prev']}/{py['real']}")
    print(f"{comparados} linhas comparadas, {erros} divergências")
    return 1 if erros else 0


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else achar_planilha()
    if not caminho:
        print("Não encontrei a planilha finalizada.\n"
              "Copie o arquivo .xlsx (o de nome chinês) para a mesma pasta do validar.py e rode de novo,\n"
              'ou informe o caminho:  python validar_lacre_deslacre.py "caminho\\da\\planilha.xlsx"')
        sys.exit(2)
    sys.exit(main(caminho))
