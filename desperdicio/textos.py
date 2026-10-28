"""Textos do relatório Taxa de Desperdício (浪费率), em chinês + português.
[planilha] = termo da planilha da Joilma; [revisar] = escrito por mim, peça a um falante nativo para conferir."""
from comum.idioma import bi, frase
from ocupacao.textos import (  # noqa: F401  (reexportados para a tela)
    AVISO_BASE_VAZIA, BANCO_EM_USO, COMPARAR, COMP_ANO, COMP_ANTERIOR, COMP_LEGENDA, COMP_SEM_DADOS, COMP_SEM_TODOS,
    COL_COMP, COL_VAR, COL_REGIAO, COL_VIAGENS, COL_PREV, COL_REAL, COL_VEICULO, COL_CAP, DIAG, ERRO_BANCO,
    EXPANDER_TENDENCIA, EXPORTAR, GRAN, GRAN_NOMES, HIST, INFO_SEM_ARQUIVO, INFO_UM_DIA, N_DIAS, PERIODO, SUB_BASE,
    SUB_CARGAS, TODOS, UNIDADE_TENDENCIA, ESCALA, ESCALA_AJUDA, TIPO_ZH, TIPO_PT, COLUNAS_BASE, ABA_BASE)

PAGINA = ("浪费率", "Taxa de Desperdício Linha Secundária")                                 # 浪费 [planilha]
COL_DESP_VOL = bi("浪费量", "Vol. Desperdício")                                            # [planilha]
COL_DESP = bi("浪费率", "Desperdício %")
COL_FRETE = bi("运费总计", "Frete total")                                                # [revisar]
COL_PERDA = bi("损失金额", "Perda R$")                                                    # [revisar]
AVISO_SEM_FRETE = "viagens sem frete no relatório de Custos (ficam fora da Perda R$): "                                                   # [planilha]
SEM_DADOS = frase("还没有数据：请先在“装载率”页面上传并保存报表。",
                  "Ainda não há dados: envie e salve o arquivo na página Taxa de Ocupação (a base é a mesma).")   # [revisar]


def nome_aba(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "浪费率", f"{TIPO_PT[tipo]} · Desperdício")


def nome_aba_tendencia() -> str:
    return bi("浪费率趋势", "Tendência")


def subtitulo_tabela(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "浪费率汇总表", f"Tabela consolidada de desperdício – {TIPO_PT[tipo]}")


def subtitulo_tendencia(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "浪费率趋势", f"Tendência do Desperdício na {TIPO_PT[tipo]}")


def subtitulo_detalhe(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "浪费率明细（按车型）", f"Detalhe por tipo de veículo – {TIPO_PT[tipo]}")


def aba_excel_tabela(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "浪费汇总", f"{TIPO_PT[tipo]}")


def aba_excel_detalhe(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "浪费明细", f"Det {TIPO_PT[tipo]}")


def aba_excel_tendencia(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "浪费趋势", f"Tend {TIPO_PT[tipo]}")


_PERDA_PT = " Perda R$ = frete total das viagens (relatório de Custos) × desperdício %."
_PT = ("Lógica de cálculo: desperdício = 1 − ocupação; ocupação = volume carregado ÷ capacidade do veículo, somando todas as "
       "viagens da regional de origem e limitada a 100% (acima disso, desperdício zero)." + _PERDA_PT)
_ZH = ["备注：以始发区域统计", "逻辑：浪费率 = 1 − 装载率（装载率上限100%）；损失金额 = 运费总计 × 浪费率", "运输状态：”已完成“，”在途“"]


def nota_texto(tipo: str) -> str:
    return "\n".join(_ZH + ["Obs: considerar a região de origem.", _PT])


NOTA_RODAPE = (_ZH, ["Obs: considerar a região de origem.", _PT])


def arquivo_excel(sufixo: str) -> str:
    return f"浪费率_Taxa_de_Desperdicio_{sufixo}.xlsx"
