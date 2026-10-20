"""Todos os textos do relatório SM, em chinês + português.

Convenção: chinês ACIMA do português só no título da página; no resto, LADO A LADO.
Origem do chinês:
  [planilha]  termo que já existe na planilha finalizada (Estatística de Status dos SMs ... .xlsx)
  [revisar]   escrito por mim: peça a um falante nativo para conferir antes de mostrar aos gerentes
"""
from comum.idioma import bi, frase

# ---- título da página ----
PAGINA = ("SM状态统计", "Estatística de Status dos SMs")                                 # [planilha]

TIPO_ZH = {"COLETA": "集货", "ENTREGA": "散货"}                                           # [planilha]
TIPO_PT = {"COLETA": "Coleta", "ENTREGA": "Entrega"}


def titulo_tabela(tipo: str, quando: str) -> str:
    return f"SM状态统计 - {TIPO_ZH[tipo]} / Estatística de Status dos SMs - {TIPO_PT[tipo]} – {quando}"


def nome_aba(tipo: str) -> str:
    return bi(f"SM {TIPO_ZH[tipo]}状态统计", f"SM {TIPO_PT[tipo]}")                       # [planilha]


def subtitulo_tendencia(tipo: str) -> str:
    return bi(f"{TIPO_ZH[tipo]}打卡率趋势", f"Tendência da {TIPO_PT[tipo]}")                # [planilha]


def aba_excel_tabela(tipo: str) -> str:
    return bi(f"SM {TIPO_ZH[tipo]}状态统计", f"SM {TIPO_PT[tipo]}")


def aba_excel_tendencia(tipo: str) -> str:
    return bi(f"{TIPO_ZH[tipo]}趋势", f"Tend {TIPO_PT[tipo]}")


def aba_excel_base(tipo: str) -> str:
    return bi(f"支线跟踪查询{TIPO_ZH[tipo]}", TIPO_PT[tipo].upper())                       # [planilha]


ABA_TENDENCIA = bi("打卡率趋势", "Tendência")                                              # [planilha]
ABA_PENDENTES = bi("未监控任务", "Viagens sem SM")                                         # [revisar]
ABA_TECHIS = bi("TECHIS系统", "Sistema TECHIS")                                            # [revisar]
ABA_BASE = bi("数据源 / 核对", "Base / Diagnóstico")                                       # [revisar]
ABA_EXCEL_TECHIS = "SISTEMA TECHIS"                                                        # [planilha]

# ---- barra lateral ----
UP_COLETA = bi("JMS 支线跟踪查询 – 集货", "JMS – Coleta")                                 # [planilha]
UP_ENTREGA = bi("JMS 支线跟踪查询 – 散货", "JMS – Entrega")                               # [planilha]
UP_TECHIS = bi("TECHIS 导出", "TECHIS (todas as viagens)")                                # [revisar]
UP_AJUDA_JMS = frase("运力平台 › 支线任务跟踪查询，按计划出发时间导出；可上传多天。",          # [revisar]
                     "Consulta de Viagens Secundárias, filtro pelo horário planejado de saída. "
                     "Pode enviar vários dias.")
UP_AJUDA_TECHIS = frase("Ger. Risco › Monitoramento › Liberação，勾选全部状态后导出。",       # [revisar]
                        "Ger. Risco › Monitoramento › Liberação, todos os status marcados, "
                        "\"Exportar Excel (todas as viagens)\".")
UP_HIST = bi("历史数据", "Histórico (Excel já exportado pelo app)")                          # [revisar]
UP_AJUDA_HIST = frase("上传之前导出的 Excel，与今天的数据合并，形成每日历史。",               # [revisar]
                      "Envie o Excel exportado nos dias anteriores: ele é somado aos arquivos de hoje e "
                      "forma o histórico por dia (tendência). Exporte de novo no fim para levar o histórico adiante.")
TODOS = bi("全部（累计）", "Todos (acumulado)")
DIA = bi("日期（计划出发）", "Dia (saída planejada)")                                       # [planilha: 规划离开日期]
N_DIAS = bi("趋势：折线周期数", "Tendência: nº de períodos na linha")                       # [revisar]
ESCALA = bi("趋势：统一刻度", "Tendência: mesma escala em todas as linhas")                # [revisar]
EXPORTAR = bi("导出 Excel (.xlsx)", "Exportar tudo para Excel")                           # [revisar]
EXPORTAR_TECHIS = bi("包含 TECHIS 数据", "Incluir aba SISTEMA TECHIS no Excel")            # [revisar]


def arquivo_excel(sufixo: str) -> str:
    return f"Estatística de Status dos SMs SM状态统计 {sufixo}.xlsx"


# ---- colunas das tabelas ----
COL_REGIAO = "发出代理区 Regional de Origem"                                              # [planilha]
COL_PREV = "应监控SM次数 SM previstos"                                                    # [planilha]
COL_REAL = "实际监控SM次数 SM realizados"                                                 # [planilha]
COL_TAXA = "有效监控占比 Rastreamento efetivo"                                            # [planilha]
COL_RANK = "排名 Ranking"                                                                 # [revisar]
TOTAL = "合计 Total"                                                                       # [planilha]
COL_VARIACAO = "环比± Variação"                                                           # [planilha]
COL_ACUMULADO = "累计 Acumulado"                                                          # [planilha]

OBS = frase("备注：每个任务单实际SM次数/应SM次数。数据源：JMS-运力平台-支线任务跟踪查询。时间：计划出发时间 00:00-23:59:59。",   # [planilha]
            "Obs.: nº real de SMs por ordem de tarefa / nº previsto de SMs. Fonte: JMS – Consulta de Viagens "
            "Secundárias. Período: horário planejado de saída das 00:00 às 23:59:59.")

# ---- mensagens ----
INFO_SEM_ARQUIVO = frase("历史数据库为空：请在左侧上传 JMS 集货、散货报表和 TECHIS 导出文件，然后点击“保存到历史”。",   # [revisar]
                         "O histórico está vazio: envie os relatórios do JMS (Coleta e Entrega) e a extração do "
                         "TECHIS na barra lateral e clique em “Salvar no histórico”.")
SALVAR_SEM_TECHIS = frase("保存前需要上传 TECHIS 导出文件（否则实际监控次数为 0）。",              # [revisar]
                          "Para salvar, envie também a extração do TECHIS (sem ela os SMs realizados ficariam em 0).")
SALVAR_SEM_JMS = frase("请先上传 JMS 报表。", "Envie antes ao menos um relatório do JMS.")      # [revisar]
PENDENTES_AVISO = frase("以下数据尚未保存到历史，已计入当前统计。",                              # [revisar]
                        "Os dados enviados ainda não foram salvos no histórico, mas já entram nas tabelas abaixo.")
INFO_SEM_TECHIS = frase("未上传 TECHIS：实际监控次数会全部为 0。",                           # [revisar]
                        "Sem o arquivo do TECHIS os SMs realizados ficam todos em 0. Envie a extração na barra lateral.")
INFO_SEM_TIPO = frase("未上传该类型的 JMS 报表。",                                          # [revisar]
                      "O relatório do JMS deste tipo não foi enviado.")
INFO_SEM_TECHIS_ABA = frase("请在左侧上传 TECHIS 导出文件。",                                # [revisar]
                            "Envie a extração do TECHIS na barra lateral para ver esta aba.")
INFO_UM_DIA = frase("数据中只有一个周期，需要更多数据才能显示趋势。",                         # [revisar]
                    "Só há um período na base. Com mais dados a tendência aparece.")
AVISO_BASE_VAZIA = frase("该周期没有数据。", "Não há dados neste período.")  # [revisar]
ERRO_COLUNAS = "缺少列 Colunas não encontradas no arquivo: "                               # [revisar]
ERRO_TECHIS = "TECHIS: 找不到列 Coluna não encontrada: "                                   # [revisar]
EXPANDER_TENDENCIA = bi("完整表（含环比与累计）", "Tabela completa (com variação e acumulado)")
ACUMULADO_AJUDA = frase("累计 = 每日占比的平均值（同表格）。",                               # [revisar]
                        "Acumulado = média das taxas de cada período (igual à planilha).")

# ---- aba Viagens sem SM ----
PEND_INTRO = frase("所选日期中实际监控次数少于应监控次数的任务单。",                         # [revisar]
                   "Viagens do período escolhido com menos SMs realizados do que o previsto.")
PEND_TIPO = bi("类型", "Tipo")                                                            # [revisar]
PEND_REGIOES = bi("代理区", "Regionais")                                                  # [planilha: 代理区]
def pend_resumo(viagens: int, sms: int) -> str:                                         # [revisar]
    return f"{viagens} 个任务单 · 缺少 {sms} 次 SM  |  {viagens} viagens · {sms} SMs faltando"


PEND_BAIXAR = bi("下载列表", "Baixar lista (.xlsx)")                                       # [revisar]

# ---- aba TECHIS ----
TECHIS_INTRO = frase("TECHIS 导出的全部行程，可筛选、搜索并下载。",                           # [revisar]
                     "Todas as viagens da extração do TECHIS: filtre, pesquise e baixe.")
TECHIS_TOTAL = bi("行程数", "Viagens")                                                     # [revisar]
TECHIS_LIGADAS = bi("匹配 JMS 任务", "Ligadas a viagens do JMS")                            # [revisar]
TECHIS_STATUS = bi("状态", "Status")
TECHIS_OPERACAO = bi("业务", "Operação")                                                   # [revisar]
TECHIS_TECNOLOGIA = bi("技术", "Tecnologia")                                               # [revisar]
TECHIS_BUSCA = bi("搜索（车牌 / SM / 任务单号）", "Buscar (placa, nº SM, nº embarque)")      # [revisar]
TECHIS_BAIXAR = bi("下载筛选结果", "Baixar filtro (.xlsx)")                                 # [revisar]
TECHIS_TAB_AJUDA = frase("任务单号末尾带空格或TAB；本应用会计入这些SM，旧表格公式不计入。",            # [revisar]
                         "Nº Embarque digitado com espaço/TAB no fim. O app conta esses SMs; "
                         "a fórmula CONT.SE da planilha antiga não contava.")
TECHIS_POR_STATUS = bi("按状态", "Por status")                                             # [revisar]

# ---- aba Base / Diagnóstico ----
SUB_DIAG = bi("按规则剔除的行数", "Linhas removidas por regra")                            # [revisar]
SUB_BASE = bi("处理后数据", "Base tratada")                                                # [revisar]

DIAG = {
    "arquivo": bi("文件", "Arquivo"),
    "tipo": bi("类型", "Tipo"),
    "lidas": bi("读取行数", "Linhas lidas"),
    "sem_data": bi("无计划出发时间", "Sem horário planejado de saída"),
    "status": bi("剔除：状态非已完成/在途", "Removidas: status fora de Concluído/Em Trânsito"),
    "mesmo_sc": bi("剔除：同场线路", "Removidas: rota do mesmo SC"),
    "ponto_coleta": bi("剔除：揽收业务网点（是）", "Removidas: unidade da lista de coleta (Sim)"),                       # [revisar]
    "franqueado": bi("剔除：加盟商", "Removidas: fornecedor Franqueado"),
    "pedido_mae": bi("剔除：主单数量为空、0 或 1", "Removidas: pedido mãe vazio, 0 ou 1"),
    "usadas": bi("使用行数", "Linhas usadas"),
    "rota_vazia": bi("线路名称为空，改用任务名称", "Info: Nome da rota (G) vazio, usou Nome da viagem (D)"),   # [revisar]
    "techis_linhas": bi("TECHIS 行数", "Linhas TECHIS"),
    "techis_status": bi("TECHIS 剔除：状态非在途/已完成", "TECHIS removidas: status fora de Em Viagem/Finalizado"),  # [revisar]
    "techis_tab": bi("任务单号含空格/TAB", "Nº Embarque com espaço/TAB"),                      # [revisar]
}

COLUNAS_BASE = {                                                                           # [planilha]
    "tipo": bi("类型", "Tipo"),
    "id": bi("任务单号", "Tarefa de transporte No."),
    "status": bi("状态", "Status"),
    "viagem": bi("任务名称", "Nome da viagem"),
    "rota": bi("线路名称", "Nome da rota"),
    "rota_usada": bi("预计次数所用线路", "Rota usada no previsto"),                               # [revisar]
    "tipo_transportador": bi("承运商类型", "Tipo de transportador"),
    "transportador": bi("承运商简称", "Transportador"),
    "pedido_mae": bi("主单数量", "Pedido mãe"),
    "partida": bi("发车网点", "PDD de saída"),
    "chegada": bi("到车网点", "PDD de chegada"),
    "saida_plan": bi("计划出发时间", "Saída planejada"),
    "placa": bi("车牌", "Placa"),
    "regiao": bi("发出代理区", "Regional de Origem"),
    "regiao_destino": bi("到达代理区", "Regional de destino"),
    "dia": bi("规划离开日期", "Data saída planejada"),
    "trechos": bi("线路节点", "Trechos"),
    "sm_prev": bi("应监控次数", "SM previsto"),
    "sm_contagem": bi("TECHIS 次数", "SMs no TECHIS"),
    "sm_real": bi("实监控次数", "SM realizado"),
}


# ---- período, comparação, histórico e resumo (compartilhados com o Lacre/Deslacre) ----
from lacre_deslacre.textos import (BANCO_EM_USO, COL_COMP, COL_VAR, COMP_ANO, COMP_ANTERIOR, COMP_LEGENDA,  # noqa: E402,F401
                                   COMP_SEM_DADOS, COMP_SEM_TODOS, COMPARAR, ERRO_BANCO, GRAN, GRAN_NOMES, HIST,
                                   PENDENTE, PERIODO, RES_ANO, RES_GRAF_TAXA, RES_GRAF_VOL, RES_LACUNA, RES_NOTA,
                                   RES_DIAS_DE, RES_PERIODO, RES_PILULA_M, RES_PILULA_W, RES_REGIONAL, RES_SEM_DADOS, RES_TABELA, RES_TODAS,
                                   RES_TODO_HISTORICO, RES_ULTIMO, RES_VISAO, SALVAR, SALVAR_AJUDA, SALVO_OK,
                                   SUB_CARGAS, UNIDADE_TENDENCIA)

ABA_RESUMO = bi("汇总", "Resumo")                                                          # [revisar]


def subtitulo_resumo(tipo: str) -> str:
    return bi(f"{TIPO_ZH[tipo]}汇总", f"Resumo – {TIPO_PT[tipo]}")                          # 汇总 [revisar]


def aba_excel_resumo(tipo: str) -> str:
    return bi(f"{TIPO_ZH[tipo]}汇总", f"Res {TIPO_PT[tipo]}")


RES_FALTAM = bi("缺少", "Faltam")                                                           # [revisar]
RES_COBERTURA = bi("各区域监控覆盖（红 = 已监控，灰 = 缺少）", "Cobertura por regional (vermelho = monitorado, cinza = faltou)")   # [revisar]
RES_MINI = bi("各区域趋势", "Evolução de cada regional")                                     # [revisar]
RES_PERIODO_SEL = bi("周期（上方图表与指标）", "Período (cartões e cobertura)")             # [revisar]
RES_TODO_PERIODO = bi("全部（所选年份）", "Todo o ano escolhido")                           # [revisar]
