"""Textos do relatório de Pontualidade (Taxa de Chegada e Taxa de Saída), em chinês + português.

Os termos genéricos (período, comparação, histórico, resumo) vêm do Lacre/Deslacre para ficarem iguais.
Origem do chinês:
  [planilha]  termo que já existe nas planilhas Taxa_de_Chegada / Taxa_de_Saída
  [revisar]   escrito por mim: peça a um falante nativo para conferir antes de mostrar aos gerentes
"""
from comum.idioma import bi, frase
from lacre_deslacre.textos import (  # noqa: F401  (reexportados para as telas)
    AVISO_BASE_VAZIA, BANCO_EM_USO, COMPARAR, COMP_ANO, COMP_ANTERIOR, COMP_LEGENDA, COMP_SEM_DADOS, COMP_SEM_TODOS,
    COL_COMP, COL_VAR, ERRO_BANCO, ERRO_COLUNAS, EXPANDER_TENDENCIA, EXPORTAR, GRAN, GRAN_NOMES, HIST, INFO_SEM_ARQUIVO,
    INFO_UM_DIA, N_DIAS, PENDENTE, PERIODO, RES_ANO, RES_DIAS_DE, RES_LACUNA, RES_NOTA, RES_PERIODO, RES_PILULA_M,
    RES_PILULA_W, RES_REGIONAL, RES_SEM_DADOS, RES_TABELA, RES_TODAS, RES_TODO_HISTORICO, RES_ULTIMO, RES_VISAO,
    RES_VS_META, SALVAR, SALVAR_AJUDA, SALVO_OK, SUB_BASE, SUB_CARGAS, TODOS, UNIDADE_TENDENCIA, ESCALA, ESCALA_AJUDA)

PAGINA = ("支线准点率", "Pontualidade Linha Secundária")                                  # 准点率 [planilha]
MENU = bi("支线准点率", "Pontualidade")

IND_ZH = {"CHEGADA": "到达", "SAIDA": "发车"}                                             # [planilha]
IND_PT = {"CHEGADA": "Chegada", "SAIDA": "Saída"}
IND_NOME = {k: bi(IND_ZH[k] + "准点率", f"Taxa de {IND_PT[k]}") for k in IND_ZH}           # [planilha]
INDICADOR = bi("指标", "Indicador")                                                        # [revisar]

TIPO_ZH = {"COLETA": "集货", "ENTREGA": "散货"}                                           # [planilha]
TIPO_PT = {"COLETA": "Coleta", "ENTREGA": "Entrega"}

COL_TOTAL = {"CHEGADA": bi("总到达量", "Total de Chegada"), "SAIDA": bi("出发总数", "Total de Saídas")}                        # [planilha]
COL_ATRASO = {"CHEGADA": bi("总到达延误量", "Total de atraso na Chegada"), "SAIDA": bi("出发延误总数", "Total de atraso na Saída")}  # [planilha]
COL_TAXA = {"CHEGADA": bi("准时到达率", "Taxa de Chegada no Prazo"), "SAIDA": bi("发车准点率", "Taxa de Saída no prazo")}      # [planilha]


def titulo(ind: str, tipo: str) -> str:
    return bi(f"支线{TIPO_ZH[tipo]}{IND_ZH[ind]}准点率", f"Taxa de {IND_PT[ind]} da {TIPO_PT[tipo]} Secundária")   # [planilha]


def nome_aba(ind: str, tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + IND_ZH[ind] + "准点率", f"{TIPO_PT[tipo]} · {IND_PT[ind]}")


def nome_aba_tendencia() -> str:
    return bi("准点率趋势", "Tendência")                                                   # [planilha]


def subtitulo_tendencia(ind: str, tipo: str) -> str:
    return bi(f"{TIPO_ZH[tipo]}{IND_ZH[ind]}准点率趋势", f"Tendência de {IND_PT[ind]} da {TIPO_PT[tipo]}")   # [planilha]


def aba_excel_tabela(ind: str, tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + IND_ZH[ind], f"{IND_PT[ind]} {TIPO_PT[tipo]}")


def aba_excel_tendencia(ind: str, tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "趋势" + IND_ZH[ind][0], f"Tend {IND_PT[ind]} {TIPO_PT[tipo]}")


def subtitulo_resumo(ind: str, tipo: str) -> str:
    return bi(f"{TIPO_ZH[tipo]}{IND_ZH[ind]}准点率汇总", f"Resumo – {IND_PT[ind]} {TIPO_PT[tipo]}")   # [revisar]


def aba_excel_resumo(ind: str, tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + IND_ZH[ind] + "汇总", f"Res {IND_PT[ind]} {TIPO_PT[tipo]}")


ABA_RESUMO = bi("汇总", "Resumo")                                                         # [revisar]
ABA_BASE = bi("数据源 / 核对", "Base / Diagnóstico")

UPLOAD = bi("支线运输综合报表", "Relatório consolidado (.xls / .xlsx)")                    # [planilha]
UPLOAD_AJUDA = frase("可上传一个或多个日期的报表；保存到历史后即可查看。",                   # [revisar]
                     "Envie um ou mais dias e clique em “Salvar no histórico”.")

_NOTA_ZH = {"COLETA": "备注：以发车网点所在区域统计", "ENTREGA": "备注：以到车网点所在区域统计"}                       # [revisar]
_NOTA_PT = {"COLETA": "Obs: a Coleta considera a regional de origem (saída) em que a filial está localizada.",
            "ENTREGA": "Obs: a Entrega considera a regional de destino (chegada) em que a filial está localizada."}


def notas(ind: str, tipo: str):
    """(linhas em chinês, linhas em português) para o rodapé de cada tabela."""
    if ind == "CHEGADA":
        zh = ["逻辑：实际到达时间 ≤ 计划到达时间 为准点；无实际到达时间视为延误",
              "运输状态：”已完成“，”在途“", "统计日：计划到达时间 − 8小时（每日 08:00 起算）",
              "合计行为各区域准点率的平均值"]                                                                      # [revisar]
        pt = ["Lógica de cálculo: chegada real ≤ chegada planejada = no prazo; sem chegada real = atraso.",
              "Status do transporte considerados: “Concluído” e “Em trânsito”.",
              "Dia da operação: horário planejado de chegada − 8 horas (o dia começa às 08:00).",
              "A linha de total é a média das taxas das regionais (igual à planilha)."]
    else:
        zh = ["逻辑：实际发车时间 ≤ 计划发车时间 为准点；无实际发车时间视为延误",
              "运输状态：”已完成“，”在途“", "统计日：计划发车时间 − 8小时（每日 08:00 起算）",
              "合计行为各区域准点率的平均值"]                                                                      # [revisar]
        pt = ["Lógica de cálculo: saída real ≤ saída planejada = no prazo; sem saída real = atraso.",
              "Status do transporte considerados: “Concluído” e “Em trânsito”.",
              "Dia da operação: horário planejado de saída − 8 horas (o dia começa às 08:00).",
              "A linha de total é a média das taxas das regionais (igual à planilha)."]
    return [_NOTA_ZH[tipo]] + zh, [_NOTA_PT[tipo]] + pt


def nota_texto(ind: str, tipo: str) -> str:
    zh, pt = notas(ind, tipo)
    return "\n".join(zh + pt)


def arquivo_excel(ind: str, sufixo: str) -> str:
    return f"支线{IND_ZH[ind]}准点率_Taxa_de_{IND_PT[ind]}_{sufixo}.xlsx"


DIAG = {
    "lidas": bi("读取行数", "Linhas lidas"),
    "sem_data": bi("无计划时间", "Sem horário planejado"),
    "status": bi("剔除：状态非已完成/在途", "Removidos: status fora de Concluído/Em Trânsito"),
    "duplicadas": bi("剔除：重复行", "Removidos: trechos duplicados"),
    "futuro_chegada": bi("到达尚未到期（不计入）", "Chegadas ainda dentro do prazo (fora do cálculo)"),     # [revisar]
    "futuro_saida": bi("发车尚未到期（不计入）", "Saídas ainda dentro do prazo (fora do cálculo)"),         # [revisar]
    "usadas": bi("使用行数", "Linhas usadas"),
}

COLUNAS_BASE = {
    "id": bi("任务单号", "Número do ID"), "status": bi("任务状态", "Status"), "viagem": bi("任务名称", "Nome da viagem"),
    "tipo_linha": bi("线路类型", "Tipo de linha"), "cod_partida": bi("发车网点编码", "Código de estação de partida"),
    "partida": bi("发车网点名称", "Estação de partida"), "cod_chegada": bi("到车网点编码", "Código de estação de chegada"),
    "chegada": bi("到车网点名称", "Estação de chegada"), "reg_saida": bi("发车所属代理区", "Regional de saída"),
    "reg_chegada": bi("到车所属代理区", "Regional de chegada"), "saida_plan": bi("计划发车时间", "Saída planejada"),
    "saida_real": bi("实际发车时间", "Saída real"), "chegada_plan": bi("计划到达时间", "Chegada planejada"),
    "chegada_real": bi("实际到达时间", "Chegada real"), "dia_saida": bi("发车日期", "Dia da saída"),
    "dia_chegada": bi("到达日期", "Dia da chegada"), "ok_saida": bi("发车准点", "Saída no prazo"),
    "ok_chegada": bi("到达准点", "Chegada no prazo"), "aberto_saida": bi("发车未到期", "Saída em aberto"),
    "aberto_chegada": bi("到达未到期", "Chegada em aberto"),                                                  # [revisar]
}

SALVANDO = frase("正在读取并保存，大文件可能需要 1–2 分钟，请勿关闭页面…\n", "Lendo e salvando (arquivo grande: pode levar 1 a 2 minutos, não feche a página)… ")  # [revisar]

# ---- Resumo ----
RES_GRAF_RANK = bi("排名与目标", "Ranking vs meta")                                       # [revisar]
RES_GRAF_CALOR = bi("区域 × 周期热力图", "Mapa de calor: regional × período")             # [revisar]
RES_CALOR_AJUDA = frase("红色 = 低于目标，灰色 = 达到目标。", "Vermelho = abaixo da meta; cinza = meta atingida.")   # [revisar]
RES_META = bi("目标", "Meta")
RES_PONDERADO = frase("上方合计与目标对比按趟次加权；下表各周期在未选区域时为各区域准点率的平均值。",                      # [revisar]
                      "Os cartões acima e a linha de total são ponderados pelo nº de trechos; as linhas por período, "
                      "sem regional escolhida, são a média das taxas das regionais (igual à planilha).")
