"""Textos do relatório Taxa de Uso de APP, em chinês + português.

Os termos genéricos (período, comparação, histórico, resumo) vêm do Lacre/Deslacre para ficarem iguais.
Origem do chinês:
  [planilha]  termo que já existe na planilha do Lucas (Taxa_uso_de_APP ... .xlsx)
  [revisar]   escrito por mim: peça a um falante nativo para conferir antes de mostrar aos gerentes
"""
from comum.idioma import bi, frase
from lacre_deslacre.textos import (  # noqa: F401  (reexportados para as telas)
    AVISO_BASE_VAZIA, BANCO_EM_USO, COMPARAR, COMP_ANO, COMP_ANTERIOR, COMP_LEGENDA, COMP_SEM_DADOS, COMP_SEM_TODOS,
    COL_COMP, COL_VAR, ERRO_BANCO, ERRO_COLUNAS, EXPANDER_TENDENCIA, EXPORTAR, GRAN, GRAN_NOMES, HIST, INFO_SEM_ARQUIVO,
    INFO_UM_DIA, N_DIAS, PENDENTE, PERIODO, RES_ANO, RES_DIAS_DE, RES_LACUNA, RES_NOTA, RES_PERIODO, RES_PILULA_M,
    RES_PILULA_W, RES_REGIONAL, RES_SEM_DADOS, RES_TABELA, RES_TODAS, RES_TODO_HISTORICO, RES_ULTIMO, RES_VISAO,
    RES_VS_META, SALVAR, SALVAR_AJUDA, SALVO_OK, SUB_BASE, SUB_CARGAS, TODOS, UNIDADE_TENDENCIA, ESCALA, ESCALA_AJUDA)

PAGINA = ("支线打卡率", "Taxa de Uso de APP Linha Secundária")                             # 打卡率 [planilha]
MENU = bi("支线打卡率", "Taxa de Uso de APP")

TIPO_ZH = {"COLETA": "集货", "ENTREGA": "散货"}                                           # [planilha]
TIPO_PT = {"COLETA": "Coleta", "ENTREGA": "Entrega"}

COL_PREV = bi("应打次数", "Qtd. prevista")                                                # [planilha]
COL_REAL = bi("实际打卡次数", "Qtd. realizada")                                           # [planilha]
COL_TAXA = bi("打卡率", "Taxa de ponto")                                                  # [planilha]


def nome_aba(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "打卡率", f"{TIPO_PT[tipo]} · Taxa de ponto")


def nome_aba_tendencia() -> str:
    return bi("打卡率趋势", "Tendência")                                                  # [planilha]


def subtitulo_tendencia(tipo: str) -> str:
    return {"COLETA": bi("集货打卡率趋势", "Tendência Uso do APP na Coleta"),              # [planilha]
            "ENTREGA": bi("散货打卡率趋势", "Tendência Uso do APP na Entrega")}[tipo]


def aba_excel_tabela(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "汇总", f"{TIPO_PT[tipo]}")                                  # 汇总 [planilha]


def aba_excel_tendencia(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "趋势", f"Tend {TIPO_PT[tipo]}")


def subtitulo_resumo(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "打卡率汇总", f"Resumo – {TIPO_PT[tipo]}")                   # [revisar]


def aba_excel_resumo(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "汇总趋势", f"Res {TIPO_PT[tipo]}")


ABA_RESUMO = bi("汇总", "Resumo")                                                         # [revisar]
ABA_BASE = bi("数据源 / 核对", "Base / Diagnóstico")

UPLOAD = bi("支线运输综合报表", "Relatório consolidado (.xls / .xlsx)")                    # [planilha]
UPLOAD_AJUDA = frase("可上传一个或多个日期的报表；保存到历史后即可查看。",                   # [revisar]
                     "Envie um ou mais dias e clique em “Salvar no histórico”.")

NOTAS = {
    "COLETA": (
        ["备注：以网点所在始发区域", '逻辑：支线"集货"线路实际打卡次数/应打卡次数',
         "运输状态：”已完成“，”在途“", "统计时间：T-2,在计划到达时间00:00-23:59:59内"],
        ["Obs: considerar a região de origem em que a filial está localizada.",
         "Lógica de cálculo: taxa de registro de ponto das rotas de coleta da linha secundária = quantidade efetiva de "
         "registros de ponto ÷ quantidade prevista de registros de ponto.",
         "Status do transporte considerados: “Concluído” e “Em trânsito”.",
         "Período de apuração: T-2, considerando os embarques com horário previsto de chegada entre 00:00:00 e 23:59:59."]),
    "ENTREGA": (
        ["备注：以网点所在到达区域", '逻辑：支线"散货"线路实际打卡次数/应打卡次数',
         "运输状态：”已完成“，”在途“", "统计时间：T-2,在计划到达时间00:00-23:59:59内"],
        ["Obs: considerar a região de destino em que a filial está localizada.",
         "Lógica de cálculo: taxa de registro de ponto das rotas de entrega da linha secundária = quantidade efetiva de "
         "registros de ponto ÷ quantidade prevista de registros de ponto.",
         "Status do transporte considerados: “Concluído” e “Em trânsito”.",
         "Período de apuração: T-2, considerando os embarques com horário previsto de chegada entre 00:00:00 e 23:59:59."]),
}


def nota_texto(tipo: str) -> str:
    zh, pt = NOTAS[tipo]
    return "\n".join(zh + pt)


def arquivo_excel(sufixo: str) -> str:
    return f"支线打卡率_Taxa_de_Uso_de_APP_{sufixo}.xlsx"


DIAG = {
    "lidas": bi("读取行数", "Linhas lidas"),
    "sem_data": bi("无计划到达日期", "Sem data de chegada planejada"),
    "status": bi("剔除：状态非已完成/在途", "Removidas: status fora de Concluído/Em Trânsito"),
    "mesmo_sc": bi("剔除：同场线路", "Removidas: rota do mesmo SC"),
    "pedido_mae": bi("剔除：主单数量为空、0 或 1", "Removidas: pedido mãe vazio, 0 ou 1"),
    "tipo_preenchido": bi("承运商类型空白，已按上次报表补全", "Transportador vazio preenchido com o último relatório"),
    "tipo_vazio": bi("承运商类型仍为空（保留）", "Transportador ainda vazio (mantidas)"),
    "ponto_coleta": bi("剔除：揽收业务网点的集货（客户场地）", "Removidas: coleta em ponto de coleta (base do cliente)"),
    "franqueado": bi("剔除：加盟商承运商", "Removidas: transportador Franqueado"),
    "usadas": bi("使用行数", "Linhas usadas"),
}

COLUNAS_BASE = {
    "id": bi("任务单号", "Número do ID"), "status": bi("任务状态", "Status"), "viagem": bi("任务名称", "Nome da viagem"),
    "tipo_linha": bi("线路类型", "Tipo de linha"), "tipo_transportador": bi("承运商类型", "Tipo de transportador"), "condutor": bi("司机", "Condutor"),   # [revisar]
   
    "partida": bi("发车网点名称", "Estação de partida"), "reg_saida": bi("发车所属代理区", "Regional de saída"),
    "reg_chegada": bi("到车所属代理区", "Regional de chegada"), "cod_chegada": bi("到车网点编码", "Código de estação de chegada"),
    "chegada_plan": bi("计划到达时间", "Chegada planejada"), "hora_checkout": bi("司机出车打卡时间", "Check-out do motorista"),   # [revisar]
    "hora_checkin": bi("司机到车打卡时间", "Check-in do motorista"), "dia": bi("日期", "Dia"),
    "saiu_ok": bi("已出车打卡", "Check-out feito"), "chegou_ok": bi("已到车打卡", "Check-in feito"),                       # [revisar]
    "n_prev": COL_PREV, "n_real": COL_REAL,
}

SALVANDO = frase("正在读取并保存，大文件可能需要 1–2 分钟，请勿关闭页面…\n", "Lendo e salvando (arquivo grande: pode levar 1 a 2 minutos, não feche a página)… ")  # [revisar]

# ---- Resumo ----
RES_GRAF_RANK = bi("排名与目标", "Ranking vs meta")                                       # [revisar]
RES_GRAF_CALOR = bi("区域 × 周期热力图", "Mapa de calor: regional × período")             # [revisar]
RES_CALOR_AJUDA = frase("红色 = 低于目标，灰色 = 达到目标。", "Vermelho = abaixo da meta; cinza = meta atingida.")   # [revisar]
RES_META = bi("目标", "Meta")
