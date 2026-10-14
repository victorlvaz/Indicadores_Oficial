"""Todos os textos do relatório Lacre / Deslacre, em chinês + português.

Convenção: 支线解封车率 (chinês) vai ACIMA do português só no título da página;
em todo o resto os nomes aparecem LADO A LADO ("chinês português").

Origem do chinês:
  [planilha]  termo que já existe na planilha finalizada (支线解封车率 ... .xlsx)
  [revisar]   escrito por mim: peça a um falante nativo para conferir antes de mostrar aos gerentes
Para corrigir um nome basta editar aqui; o app inteiro se atualiza.
"""
from comum.idioma import bi, frase

# ---- título da página (chinês acima do português) ----
PAGINA = ("支线解封车率", "Lacre / Deslacre Linha Secundária")                         # [planilha]
MENU = bi("支线解封车率", "Lacre / Deslacre")                                             # [planilha]

# ---- partes dos nomes de aba / tabela ----
TIPO_ZH = {"COLETA": "集货", "ENTREGA": "散货"}                                           # [planilha]
TIPO_PT = {"COLETA": "Coleta", "ENTREGA": "Entrega"}
EVENTO_ZH = {"lacre": "封车", "deslacre": "解车"}                                         # [planilha]
EVENTO_PT = {"lacre": "Lacre", "deslacre": "Deslacre"}
TENDENCIA_ZH, TENDENCIA_PT = "趋势", "Tendência"                                         # [planilha]


def nome_aba(tipo: str, evento: str) -> str:
    return bi(TIPO_ZH[tipo] + EVENTO_ZH[evento], f"{TIPO_PT[tipo]} · {EVENTO_PT[evento]}")


def nome_aba_tendencia(evento: str) -> str:
    return bi(EVENTO_ZH[evento] + TENDENCIA_ZH, f"{TENDENCIA_PT} {EVENTO_PT[evento]}")


def subtitulo_tendencia(tipo: str, evento: str) -> str:
    return bi(TIPO_ZH[tipo] + EVENTO_ZH[evento] + TENDENCIA_ZH,
              f"{TENDENCIA_PT} – {TIPO_PT[tipo]} · {EVENTO_PT[evento]}")


def aba_excel_tabela(tipo: str, evento: str) -> str:
    return bi(TIPO_ZH[tipo] + EVENTO_ZH[evento], f"{TIPO_PT[tipo]} {EVENTO_PT[evento]}")


def aba_excel_tendencia(tipo: str, evento: str) -> str:
    return bi(TIPO_ZH[tipo] + EVENTO_ZH[evento] + TENDENCIA_ZH, f"Tend {TIPO_PT[tipo]} {EVENTO_PT[evento]}")


ABA_BASE = bi("数据源 / 核对", "Base / Diagnóstico")                                     # 数据源 [planilha]; 核对 [revisar]

# ---- barra lateral ----
UPLOAD = bi("支线运输综合报表", "Relatório consolidado (.xls / .xlsx)")                   # [planilha]
UPLOAD_AJUDA = frase("可上传一个或多个日期的报表；多天数据会填充趋势页。",                 # [revisar]
                     "Envie um ou mais dias. Com vários dias, a aba de tendência é preenchida.")
REGRAS = bi("数据处理规则", "Regras aplicadas à base")                                    # [revisar]
R_STATUS = bi("仅已完成 / 在途", "Só Concluído / Em Trânsito")                            # [planilha: 已完成, 在途]
R_MESMO_SC = bi("剔除同场线路", "Excluir rotas do mesmo SC")                              # [planilha: 同场线路]
R_COLETA = bi("集货：仅揽收网点", "Coleta: só pontos de coleta")                          # [planilha: 揽收网点]
R_FRANQ = bi("剔除加盟商承运商", "Excluir transportador Franqueado")                      # [planilha: 加盟商]
R_PEDIDO = bi("剔除主单数量为空、0 或 1", "Excluir pedido mãe vazio, 0 ou 1")             # [planilha: 主单数量]
TODOS = bi("全部（累计）", "Todos (acumulado)")
DIA = bi("日期（计划到达）", "Dia (chegada planejada)")                                    # [planilha: 计划到达]
N_DIAS = bi("趋势：折线天数", "Tendência: nº de dias na linha")                           # [revisar]
ESCALA = bi("趋势：统一刻度", "Tendência: mesma escala em todas as linhas")               # [revisar]
ESCALA_AJUDA = frase("关闭：每条线使用各自刻度（同 Excel 迷你图）。开启：便于比较各区域的走势。",   # [revisar]
                     "Desligado: cada linha usa a própria escala (como o mini-gráfico do Excel). "
                     "Ligado: permite comparar a inclinação entre regiões.")
# Rodapé das tabelas (igual ao da planilha: chinês e português, centralizado)           # [planilha]
NOTAS = {
    "lacre": (
        ["备注：每个任务单实际封车次数/应该封车次数",
         "数据源：JMS-运力平台-支线运输综合报表-封签信息",
         "时间：T-2，计划到达时间00-23:59:59"],
        ["Obs: Número real de lacre por ordem de tarefa / número previsto de lacre.",
         "Fonte: JMS – Plataforma de Capacidade – Relatório Geral de Transporte Secundário – Informação de Lacre.",
         "Período: T-2, considerando o horário planejado de chegada das 00:00 às 23:59:59."]),
    "deslacre": (
        ["备注：每个任务单实际解车次数/应该解车次数",
         "数据源：JMS-运力平台-支线运输综合报表-解封信息",
         "时间：T-2，计划到达时间00-23:59:59"],
        ["Obs: Número real de deslacre por ordem de tarefa / número previsto de deslacre.",
         "Fonte: JMS – Plataforma de Capacidade – Relatório Geral de Transporte Secundário – Informação de Deslacração.",
         "Período: T-2, considerando o horário planejado de chegada das 00:00 às 23:59:59."]),
}


def nota_texto(evento: str) -> str:
    zh, pt = NOTAS[evento]
    return "\n".join(zh + pt)


EXPORTAR = bi("导出 Excel (.xlsx)", "Exportar tudo para Excel")                          # [revisar]


def arquivo_excel(dia) -> str:
    sufixo = "Todos" if dia is None else dia.strftime("%d.%m")
    return f"支线解封车率_Lacre_Deslacre_{sufixo}.xlsx"


# ---- mensagens ----
INFO_SEM_ARQUIVO = frase("请在左侧边栏上传支线运输综合报表。",                             # [revisar]
                         "Envie o relatório consolidado da linha secundária na barra lateral.")
AVISO_BASE_VAZIA = frase("应用规则后没有剩余数据。",                                      # [revisar]
                         "Nenhuma linha restou após as regras aplicadas.")
INFO_UM_DIA = frase("数据中只有一天，请上传更多天数以查看趋势。",                           # [revisar]
                    "Só há um dia na base. Envie mais dias para ver a tendência.")
ERRO_COLUNAS = "缺少列 Colunas não encontradas no arquivo: "                              # [revisar]
EXPANDER_TENDENCIA = bi("每日完整表（含环比与累计）", "Tabela completa por dia (com variação e acumulado)")  # 环比/累计 [planilha]

# ---- aba Base / Diagnóstico ----
SUB_DIAG = bi("按规则剔除的行数", "Linhas removidas por regra")                           # [revisar]
SUB_BASE = bi("处理后数据", "Base tratada")                                               # [revisar]

DIAG = {
    "arquivo": bi("文件", "Arquivo"),                                                     # [revisar]
    "lidas": bi("读取行数", "Linhas lidas"),
    "sem_data": bi("无计划到达日期", "Sem data de chegada planejada"),
    "status": bi("剔除：状态非已完成/在途", "Removidas: status fora de Concluído/Em Trânsito"),
    "mesmo_sc": bi("剔除：同场线路", "Removidas: rota do mesmo SC"),
    "ponto_coleta": bi("剔除：非揽收网点的集货", "Removidas: coleta fora dos pontos de coleta"),
    "franqueado": bi("剔除：加盟商承运商", "Removidas: transportador Franqueado"),
    "pedido_mae": bi("剔除：主单数量为空、0 或 1", "Removidas: pedido mãe vazio, 0 ou 1"),
    "usadas": bi("使用行数", "Linhas usadas"),
}

# Colunas da "base tratada" (cabeçalhos em chinês = linha 2 da base da planilha finalizada) [planilha]
COLUNAS_BASE = {
    "id": bi("任务单号", "Número do ID"),
    "status": bi("任务状态", "Status"),
    "viagem": bi("任务名称", "Nome da viagem"),
    "tipo_linha": bi("线路类型", "Tipo de linha"),
    "tipo_transportador": bi("承运商类型", "Tipo de transportador"),
    "pedido_mae": bi("主单数量", "Pedido mãe"),
    "partida": bi("发车网点名称", "Estação de partida"),
    "reg_saida": bi("发车所属代理区", "Regional de saída"),
    "reg_chegada": bi("到车所属代理区", "Regional de chegada"),
    "cod_chegada": bi("到车网点编码", "Código de estação de chegada"),
    "chegada_plan": bi("计划到达时间", "Chegada planejada"),
    "hora_lacre": bi("封车时间", "Hora de lacre"),
    "hora_deslacre": bi("解车时间", "Hora de deslacre"),
    "dia": bi("日期", "Dia"),                                                             # [revisar]
    "lacrado": bi("已封车", "Lacrado"),                                                   # [revisar]
    "deslacrado": bi("已解车", "Deslacrado"),                                             # [revisar]
}
