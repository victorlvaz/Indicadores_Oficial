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


def subtitulo_resumo(tipo: str, evento: str) -> str:
    return bi(TIPO_ZH[tipo] + EVENTO_ZH[evento] + "汇总", f"Resumo – {TIPO_PT[tipo]} · {EVENTO_PT[evento]}")   # 汇总 [revisar]


def aba_excel_resumo(tipo: str, evento: str) -> str:
    return bi(TIPO_ZH[tipo] + EVENTO_ZH[evento] + "汇总", f"Res {TIPO_PT[tipo]} {EVENTO_PT[evento]}")


def aba_excel_tendencia(tipo: str, evento: str) -> str:
    return bi(TIPO_ZH[tipo] + EVENTO_ZH[evento] + TENDENCIA_ZH, f"Tend {TIPO_PT[tipo]} {EVENTO_PT[evento]}")


ABA_RESUMO = bi("汇总", "Resumo")                                                       # [revisar]
ABA_BASE = bi("数据源 / 核对", "Base / Diagnóstico")                                     # 数据源 [planilha]; 核对 [revisar]

# ---- barra lateral ----
UPLOAD = bi("支线运输综合报表", "Relatório consolidado (.xls / .xlsx)")                   # [planilha]
UPLOAD_AJUDA = frase("可上传一个或多个日期的报表；多天数据会填充趋势页。",                 # [revisar]
                     "Envie um ou mais dias. Com vários dias, a aba de tendência é preenchida.")
TODOS = bi("全部（累计）", "Todos (acumulado)")
DIA = bi("日期（计划到达）", "Dia (chegada planejada)")                                    # [planilha: 计划到达]
GRAN = bi("统计周期", "Período de análise")                                              # [revisar]
GRAN_NOMES = {"D": bi("日", "Dia"), "W": bi("周", "Semana"), "M": bi("月", "Mês"), "Y": bi("年", "Ano")}   # [revisar]
PERIODO = {"D": DIA, "W": bi("选择周（周一至周日）", "Semana (segunda a domingo)"),         # [revisar]
           "M": bi("选择月份", "Mês"), "Y": bi("选择年份", "Ano")}
COMPARAR = bi("对比", "Comparar com")                                                    # [revisar]
COMP_ANTERIOR = bi("上一周期", "Período anterior")                                       # [revisar]
COMP_ANO = bi("去年同期", "Mesmo período do ano passado")                                # [revisar]
COL_COMP = bi("对比期", "Taxa comp.")                                           # [revisar]
COL_VAR = bi("变化", "Var. p.p.")                                         # [revisar]
COMP_LEGENDA = bi("对比", "Comparando com")                                              # [revisar]
COMP_SEM_TODOS = frase("选择“全部”时不进行对比。", "Com “Todos” não há comparação; escolha um período.")   # [revisar]
COMP_SEM_DADOS = frase("对比期没有数据。", "Não há dados no período comparado.")           # [revisar]
UNIDADE_TENDENCIA = {"D": ("天", "dias"), "W": ("周", "semanas"), "M": ("个月", "meses"), "Y": ("年", "anos")}  # [revisar]
N_DIAS = bi("趋势：折线周期数", "Tendência: nº de períodos na linha")                      # [revisar]
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


def arquivo_excel(sufixo: str) -> str:
    return f"支线解封车率_Lacre_Deslacre_{sufixo}.xlsx"


# ---- mensagens ----
INFO_SEM_ARQUIVO = frase("历史数据库为空：请在左侧边栏上传报表并点击“保存到历史”。",             # [revisar]
                         "O histórico está vazio: envie o relatório na barra lateral e clique em “Salvar no histórico”.")
HIST = bi("历史数据库", "Histórico (banco de dados)")                                    # [revisar]
SALVAR = bi("保存到历史", "Salvar no histórico")                                          # [revisar]
SALVAR_AJUDA = frase("把已上传的报表处理后存入数据库；同一天重复上传只会更新，不会重复。",          # [revisar]
                     "Aplica as regras e grava no banco. Reenviar o mesmo dia só atualiza, não duplica.")
PENDENTE = frase("以下文件尚未保存：", "Arquivos ainda não salvos no histórico:")           # [revisar]
SALVO_OK = bi("已保存", "Salvo")                                                          # [revisar]
ERRO_BANCO = frase("无法连接数据库：", "Não foi possível acessar o banco de dados: ")        # [revisar]
SUB_CARGAS = bi("上传记录", "Histórico de cargas")                                        # [revisar]
BANCO_EM_USO = bi("数据库", "Banco em uso")                                              # [revisar]
INFO_SQLITE = frase("当前使用本地 SQLite 文件；连接公司数据库只需填写连接地址（见 README）。",     # [revisar]
                    "Usando arquivo SQLite local. Para o banco da empresa, basta informar a URL (veja o README).")
AVISO_BASE_VAZIA = frase("该周期没有数据。", "Não há dados neste período.")                  # [revisar]
INFO_UM_DIA = frase("数据中只有一个周期，需要更多数据才能显示趋势。",                         # [revisar]
                    "Só há um período na base. Com mais dados a tendência aparece.")
ERRO_COLUNAS = "缺少列 Colunas não encontradas no arquivo: "                              # [revisar]
EXPANDER_TENDENCIA = bi("完整表（含环比与累计）", "Tabela completa (com variação e acumulado)")  # 环比/累计 [planilha]

# ---- aba Base / Diagnóstico ----
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


# ---- aba Resumo ----
RES_REGIONAL = bi("区域", "Regional")                                                    # [revisar]
RES_TODAS = bi("全部区域", "Todas")                                                      # [revisar]
RES_VISAO = bi("查看方式", "Visão")                                                      # [revisar]
RES_ANO = bi("年份", "Ano")                                                              # [revisar]
RES_TODO_HISTORICO = bi("全部历史", "Todo o histórico")                                  # [revisar]
RES_NOTA = frase("本页筛选独立于左侧边栏的周期。", "Os filtros desta aba são independentes do período da barra lateral.")   # [revisar]
RES_PERIODO = bi("周期", "Período")                                                      # [revisar]
RES_ULTIMO = bi("最近周期", "Último período")                                            # [revisar]
RES_VS_META = bi("对比目标", "vs meta")                                                  # [revisar]
RES_TABELA = bi("数据表", "Tabela de apoio")                                             # [revisar]
RES_SEM_DADOS = frase("所选筛选条件下没有数据。", "Sem dados para o filtro escolhido.")   # [revisar]
RES_GRAF_TAXA = bi("比率", "Taxa")                                                       # [revisar]
RES_GRAF_VOL = bi("数量", "Volume")                                                      # [revisar]
RES_LACUNA = frase("空白处表示该周期没有上传数据。", "Pontos vazios = período sem dados no histórico.")   # [revisar]


RES_PILULA_W = frase("点击某一周查看每日数据；再次点击返回全年。", "Clique em uma semana para ver os dias dela; clique de novo para voltar ao ano.")   # [revisar]
RES_PILULA_M = frase("点击某个月查看每日数据；再次点击返回全年。", "Clique em um mês para ver os dias dele; clique de novo para voltar ao ano.")   # [revisar]
RES_DIAS_DE = bi("每日数据", "Dias de")                                                    # [revisar]
