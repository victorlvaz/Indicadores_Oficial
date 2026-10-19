"""Textos do relatório de Custos (物流成本指标), em chinês + português.

Origem do chinês:
  [planilha]  termo que já existe na planilha (次级成本周报_Custos_Secundária … .xlsx)
  [revisar]   escrito por mim: peça a um falante nativo para conferir antes de mostrar aos gerentes
"""
from comum.idioma import bi, frase
from lacre_deslacre.textos import (  # noqa: F401  (reexportados para as telas)
    AVISO_BASE_VAZIA, BANCO_EM_USO, COMPARAR, COMP_ANO, COMP_ANTERIOR, COMP_LEGENDA, COMP_SEM_DADOS, COMP_SEM_TODOS,
    ERRO_BANCO, EXPORTAR, GRAN, GRAN_NOMES, HIST, INFO_SEM_ARQUIVO, INFO_UM_DIA, N_DIAS, PENDENTE, RES_ANO,
    RES_DIAS_DE, RES_LACUNA, RES_NOTA, RES_PERIODO, RES_PILULA_M, RES_PILULA_W, RES_REGIONAL, RES_SEM_DADOS, RES_TABELA,
    RES_TODAS, RES_TODO_HISTORICO, RES_ULTIMO, RES_VISAO, SALVAR, SALVAR_AJUDA, SALVO_OK, SUB_BASE, SUB_CARGAS, TODOS)

from lacre_deslacre.textos import PERIODO as _PERIODO_BASE
PERIODO = {**_PERIODO_BASE, "D": bi("日期", "Dia")}                                          # a data do relatório de custos é a data da viagem  [revisar]

PAGINA = ("物流成本指标", "Indicadores de Custos Linha Secundária")                          # 物流成本指标 [planilha]

COL_REGIAO = bi("区域", "Regional")                                                        # [planilha]
COL_ITEM = bi("类别", "Item")                                                              # [revisar]
COL_VIAGENS = bi("发车数", "Viagens")                                                      # [revisar]
COL_PACOTES = bi("包裹数量", "Pacotes")                                                    # [planilha]
COL_KM = bi("公里", "KM")                                                                  # [planilha]
COL_FRETE = bi("运费总计", "Frete total")                                                  # [planilha]
COL_FRETE_KM = bi("每公里成本", "Frete por KM")                                            # [revisar] (a planilha usa 每公里)
COL_FRETE_PACOTE = bi("单票成本", "Frete por pacote")                                      # [planilha]
COL_VEICULO = bi("车型", "Tipo de veículo")                                                # [planilha]
COL_TIPO = bi("承运商类型", "Tipo de transportadora")                                       # [revisar]
COL_COMP_PACOTE = bi("对比期单票成本", "Frete/pacote comparado")                            # [revisar]
COL_VAR_PACOTE = bi("单票成本变化", "Variação frete/pacote")                                # [revisar]
COL_COMP_KM = bi("对比期每公里成本", "Frete/KM comparado")                                  # [revisar]
COL_VAR_KM = bi("每公里成本变化", "Variação frete/KM")                                      # [revisar]
COL_VAR_TEND = bi("环比", "Variação±")                                                     # [revisar]
COL_ACUM = bi("累计", "Acumulado")                                                         # [revisar]

ABA_REGIONAL = bi("区域成本", "Por regional")                                              # [revisar]
ABA_VEICULO = bi("车型成本", "Por veículo")                                                # [revisar]
ABA_TIPO = bi("承运商类型成本", "Por tipo de transportadora")                               # [revisar]
ABA_TENDENCIA = bi("成本趋势", "Tendência")                                                # [revisar]
ABA_RESUMO = bi("汇总", "Resumo")
ABA_AUDITORIA = bi("稽核", "Auditoria")                                                    # [revisar]
ABA_BASE = bi("数据源 / 核对", "Base / Diagnóstico")

SUB_REGIONAL = bi("各区域运费指标", "Custos por regional")                                  # [revisar]
SUB_VEICULO = bi("各区域按车型", "Custos por regional e tipo de veículo")                   # [revisar]
SUB_TIPO = bi("各区域按承运商类型", "Custos por regional e tipo de transportadora")          # [revisar]
SUB_TEND = {"frete_pacote": bi("单票成本趋势", "Tendência do frete por pacote"),
            "frete_km": bi("每公里成本趋势", "Tendência do frete por KM")}                    # [revisar]
METRICA = bi("指标", "Indicador")                                                          # [revisar]
METRICAS = {"frete_pacote": COL_FRETE_PACOTE, "frete_km": COL_FRETE_KM}

UPLOAD = bi("区域运费报表", "Planilhas de fretes das regionais (.xlsx / .xlsm / .xlsb)")             # [revisar]
UPLOAD_AJUDA = frase("可一次选择多个区域文件；系统按文件名识别区域，保存到历史后即可查看。",   # [revisar]
                     "Selecione os arquivos de todas as regionais de uma vez. O app identifica a regional pelo nome do "
                     "arquivo. Depois clique em “Salvar no histórico”.")
SALVANDO = frase("正在读取并保存，大文件可能需要几分钟，请勿关闭页面…\n",
                 "Lendo e salvando (arquivos grandes podem levar alguns minutos, não feche a página)… ")
REGIONAL_NAO_ACHADA = frase("无法从文件名识别区域，请选择：", "Não achei a regional no nome do arquivo. Escolha: ")
ERRO_SEM_ABA = frase("未找到“支线 用车成本模板- SECUNDARIA”工作表。", "Não encontrei a aba “支线 用车成本模板- SECUNDARIA” neste arquivo.")
ERRO_SEM_CABECALHO = frase("前10行未找到表头（ID VIAGEM）。", "Não achei o cabeçalho (ID VIAGEM) nas 10 primeiras linhas da aba.")
ERRO_PYXLSB = frase("读取 .xlsb 需要安装 pyxlsb：python -m pip install pyxlsb（或把文件另存为 .xlsx）。",
                    "Para ler .xlsb falta instalar o pacote pyxlsb: python -m pip install pyxlsb (ou salve o arquivo como .xlsx).")
ERRO_COLUNAS = "Colunas não encontradas no cabeçalho / 表头缺少：" 

NOTA_PT = ("Frete total = frete da rota + ônus/bônus + aluguel + combustível + motorista + depreciação + manutenção + seguro + "
           "IPVA + pedágio + outras despesas. Frete por KM = frete total ÷ KM; frete por pacote = frete total ÷ pacotes. "
           "Viagem com o mesmo ID e os mesmos valores conta uma vez; com valores diferentes, os fretes são somados.")
NOTA_ZH = ("运费总计 = 线路运费 + 奖罚 + 租车 + 燃料 + 司机 + 折旧 + 维修 + 保险 + 车船税 + 过路费 + 其他费用；"
           "每公里成本 = 运费总计 / 公里；单票成本 = 运费总计 / 包裹数量。同一任务ID且金额相同只计一次，金额不同则运费相加。")  # [revisar]
NOTAS = ([NOTA_ZH], [NOTA_PT])

NAO_INFORMADO_NOTA = frase("“未填写”= 区域未填写承运商类型。", "“Não informado” = a regional não preencheu o tipo de transportadora.")  # [revisar]


def nota_texto() -> str:
    return NOTA_ZH + "\n" + NOTA_PT


def arquivo_excel(sufixo: str) -> str:
    return f"物流成本指标_Custos_{sufixo}.xlsx"


def aba_excel(nome: str) -> str:
    return nome


DIAG = {
    "lidas": bi("读取行数", "Linhas lidas"),
    "sem_data": bi("无日期（已剔除）", "Sem data (removidas)"),
    "iguais": bi("重复ID且金额相同（只计一次）", "ID repetido com valores iguais (conta uma vez)"),
    "diferentes": bi("重复ID且金额不同（保留并相加）", "IDs repetidos com valores diferentes (mantidos e somados)"),
    "usadas": bi("使用行数", "Linhas usadas"),
}

PEND_NOMES = {                                                                             # [revisar]
    "frota": "Frete total zerado / 运费为零", "pacote": "Sem pacotes / 无包裹数", "km": "Sem KM / 无公里数",
    "rota": "Sem rota / 无线路", "tipo": "Sem tipo de transportadora / 无承运商类型"}
PEND_COLS = {"viagens": COL_VIAGENS, "frota": bi("运费为零", "Frete zerado"), "pacote": bi("无包裹数", "Sem pacotes"),
             "km": bi("无公里数", "Sem KM"), "rota": bi("无线路", "Sem rota"), "tipo": bi("无承运商类型", "Sem tipo transp."),
             "com_pendencia": bi("有待办", "Com pendência")}
AUD_PEND = bi("填报待办（按区域）", "Pendências de preenchimento por regional")             # [revisar]
AUD_LISTA = bi("待核对的行程", "Viagens a cobrar da regional")                             # [revisar]
AUD_FILTRO = bi("待办类型", "Tipo de pendência")                                           # [revisar]
AUD_TODAS = bi("全部", "Todas")
AUD_DUP = bi("重复任务ID", "IDs de viagem repetidos")                                       # [revisar]
AUD_AJUDA_DUP = frase("“相同”：金额一致，只计一次；“不同”：金额不同，运费已相加。",         # [revisar]
                      "“Iguais”: valores idênticos, conta uma vez. “Diferentes”: valores distintos, fretes somados.")
DUP_IGUAIS = "Iguais (conta 1x) / 相同"
DUP_DIFERENTES = "Diferentes (somados) / 不同"
AUD_SEM_PEND = frase("所选周期没有待办。", "Nenhuma pendência no período escolhido.")
AUD_SEM_DUP = frase("所选周期没有重复ID。", "Nenhum ID repetido no período escolhido.")
COL_DIA = bi("日期", "Dia")
COL_ID = bi("任务单号", "ID da viagem")
COL_DESTINO = bi("目的网点", "Destino (HUB)")                                                # [revisar]
COL_TRANSP = bi("承运商", "Transportadora")                                                # [planilha]
COL_PLACA = bi("车牌", "Placa")                                                            # [planilha]
COL_PEND = bi("待办", "Pendências")                                                        # [revisar]
COL_DUP_TIPO = bi("类型", "Tipo")
COL_LINHAS = bi("行数", "Linhas")                                                          # [revisar]
COL_FRETE_SOMADO = bi("运费合计", "Frete somado")                                          # [revisar]

COLUNAS_BASE = {
    "regional": COL_REGIAO, "id": COL_ID, "seq": bi("序号", "Seq."), "dia": COL_DIA, "uf": "UF",
    "sc_origem": bi("转运中心", "SC origem"), "hub_destino": COL_DESTINO, "frota": bi("自有车队", "Frota própria"),
    "transportadora": COL_TRANSP, "placa": COL_PLACA, "veiculo": COL_VEICULO, "rota": bi("线路", "Rota completa"),
    "tipo_transp": COL_TIPO, "frete_rota": bi("结算运费", "Frete rota"), "frete_total": COL_FRETE,
    "pacotes": COL_PACOTES, "km": COL_KM, "iguais_removidas": bi("合并行数", "Linhas iguais removidas"),
}

# ---- Resumo ----
RES_GRAF_REG = bi("各区域单票成本", "Frete por pacote de cada regional")                    # [revisar]
RES_GRAF_VEIC = bi("车型单票成本", "Frete por pacote por tipo de veículo")                  # [revisar]
RES_GRAF_TEND = bi("单票成本趋势", "Frete por pacote por período")                           # [revisar]
RES_SECAO = bi("成本汇总", "Resumo de custos")                                             # [revisar]
