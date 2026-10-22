"""Textos do relatório Taxa de Ocupação (装载率), em chinês + português.

Origem do chinês:
  [planilha]  termo que já existe na planilha do Lucas (ÓCUPAÇÃO SECUNDÁRIA ....xlsx)
  [revisar]   escrito por mim: peça a um falante nativo para conferir antes de mostrar aos gerentes
"""
from comum.idioma import bi, frase
from lacre_deslacre.textos import (  # noqa: F401  (reexportados para as telas)
    AVISO_BASE_VAZIA, BANCO_EM_USO, COMPARAR, COMP_ANO, COMP_ANTERIOR, COMP_LEGENDA, COMP_SEM_DADOS, COMP_SEM_TODOS,
    COL_COMP, COL_VAR, ERRO_BANCO, ERRO_COLUNAS, EXPANDER_TENDENCIA, EXPORTAR, GRAN, GRAN_NOMES, HIST, INFO_SEM_ARQUIVO,
    INFO_UM_DIA, N_DIAS, PENDENTE, PERIODO, RES_ANO, RES_DIAS_DE, RES_LACUNA, RES_NOTA, RES_PERIODO, RES_PILULA_M,
    RES_PILULA_W, RES_REGIONAL, RES_SEM_DADOS, RES_TABELA, RES_TODAS, RES_TODO_HISTORICO, RES_ULTIMO, RES_VISAO,
    SALVAR, SALVAR_AJUDA, SALVO_OK, SUB_BASE, SUB_CARGAS, TODOS, UNIDADE_TENDENCIA, ESCALA, ESCALA_AJUDA)

PAGINA = ("装载率", "Taxa de Ocupação Linha Secundária")                                   # 装载率 [planilha]
TIPO_ZH = {"COLETA": "集货", "ENTREGA": "散货"}                                            # [planilha]
TIPO_PT = {"COLETA": "Coleta", "ENTREGA": "Entrega"}

COL_REGIAO = bi("区域", "Regional")                                                        # [planilha]
COL_VIAGENS = bi("发车数", "Viagens")                                                      # [revisar]
COL_PREV = bi("应装载票数", "Volume previsto (capacidade)")                                  # [revisar]
COL_REAL = bi("实际装载票数", "Volume carregado")                                            # [revisar]
COL_TAXA = bi("装载率", "Taxa de ocupação")                                                 # [planilha]
COL_VEICULO = bi("车型", "Tipo de veículo")                                                 # [planilha]
COL_CAP = bi("核载票数", "Capacidade")                                                      # [planilha]


def nome_aba(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "装载率", f"{TIPO_PT[tipo]} · Ocupação")


def nome_aba_tendencia() -> str:
    return bi("装载率趋势", "Tendência")                                                    # [revisar]


def subtitulo_tendencia(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "装载率趋势", f"Tendência da Ocupação na {TIPO_PT[tipo]}")      # [revisar]


def subtitulo_detalhe(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "装载率明细（按车型）", f"Detalhe por tipo de veículo – {TIPO_PT[tipo]}")   # [revisar]


def aba_excel_tabela(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "汇总", f"{TIPO_PT[tipo]}")


def aba_excel_detalhe(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "明细", f"Det {TIPO_PT[tipo]}")


def aba_excel_tendencia(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "趋势", f"Tend {TIPO_PT[tipo]}")


def subtitulo_resumo(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "装载率汇总", f"Resumo – {TIPO_PT[tipo]}")                   # [revisar]


def aba_excel_resumo(tipo: str) -> str:
    return bi(TIPO_ZH[tipo] + "汇总趋势", f"Res {TIPO_PT[tipo]}")


ABA_RESUMO = bi("汇总", "Resumo")
ABA_BASE = bi("数据源 / 核对", "Base / Diagnóstico")

UPLOAD = bi("支线车辆追踪报表", "Rastreamento de linha secundária (.xls / .xlsx)")          # [revisar]
UPLOAD_AJUDA = frase("只需上传一个文件（集货与散货在同一份报表），保存到历史后即可查看。",    # [revisar]
                     "Um único arquivo (Coleta e Entrega juntas). Envie e clique em “Salvar no histórico”.")
SALVANDO = frase("正在读取并保存，大文件可能需要 1–2 分钟，请勿关闭页面…\n",
                 "Lendo e salvando (arquivo grande: pode levar 1 a 2 minutos, não feche a página)… ")

_NOTA_COMUM_PT = ("Lógica de cálculo: taxa de ocupação = volume carregado (pedidos mãe) ÷ capacidade do tipo de veículo, "
                  "limitada a 100% por regional; viagens com status “Concluído” e “Em trânsito”; sem transportador "
                  "Franqueado e sem rotas do mesmo SC.")
NOTAS = {
    "COLETA": (
        ["备注：以始发区域统计", "逻辑：装载率 = 实际装载票数 / 车型核载票数（上限100%）", "运输状态：”已完成“，”在途“"],
        ["Obs: considerar a região de origem.", _NOTA_COMUM_PT,
         "Coleta: ignora viagens com volume vazio, 0 ou 1."]),
    "ENTREGA": (
        ["备注：以始发区域统计", "逻辑：装载率 = 实际装载票数 / 车型核载票数（上限100%）", "运输状态：”已完成“，”在途“"],
        ["Obs: considerar a região de origem.", _NOTA_COMUM_PT,
         "Entrega: viagens com volume vazio contam como 0 carregado (igual à planilha); ignora volume 0 e 1."]),
}


def nota_texto(tipo: str) -> str:
    zh, pt = NOTAS[tipo]
    return "\n".join(zh + pt)


def arquivo_excel(sufixo: str) -> str:
    return f"装载率_Taxa_de_Ocupacao_{sufixo}.xlsx"


AVISO_SEM_CAPACIDADE = frase("以下车型没有核载票数，未计入装载率：", "Tipos de veículo sem capacidade cadastrada (fora do cálculo de ocupação): ")  # [revisar]

DIAG = {
    "lidas": bi("读取行数", "Linhas lidas"),
    "sem_data": bi("无计划发车时间/线路类型", "Sem data de saída planejada ou tipo de linha"),
    "status": bi("剔除：状态非已完成/在途", "Removidas: status fora de Concluído/Em Trânsito"),
    "mesmo_sc": bi("剔除：同场线路", "Removidas: rota do mesmo SC"),
    "franqueado": bi("剔除：加盟商承运商", "Removidas: transportador Franqueado"),
    "pedido_mae": bi("剔除：装载票数为空/0/1", "Removidas: pedido mãe vazio, 0 ou 1"),
    "sem_capacidade": bi("车型无核载票数（保留，不计装载率）", "Tipo de veículo sem capacidade (mantidas)"),
    "usadas": bi("使用行数", "Linhas usadas"),
}

COLUNAS_BASE = {
    "id": bi("任务单号", "Número do ID"), "status": bi("任务状态", "Status"), "viagem": bi("任务名称", "Nome da viagem"),
    "tipo_linha": bi("线路类型", "Tipo de linha"), "tipo_transportador": bi("承运商类型", "Tipo de transportador"), "condutor": bi("司机", "Condutor"),   # [revisar]
   
    "partida": bi("发车网点名称", "Estação de partida"), "reg_origem": bi("发车所属代理区", "Regional de origem"),
    "saida_plan": bi("计划发车时间", "Saída planejada"), "placa": bi("车牌", "Placa"), "veiculo": COL_VEICULO,
    "volume": bi("装载票数(原始)", "Pedido mãe (original)"), "dia": bi("日期", "Dia"), "capacidade": COL_CAP, "carregado": COL_REAL,
}

# ---- Resumo ----
RES_GRAF_REG = bi("各区域装载率", "Ocupação de cada regional")                   # [revisar]
RES_GRAF_VEIC = bi("车型装载率", "Ocupação por tipo de veículo")                              # [revisar]
RES_GRAF_TEND = bi("装载率趋势", "Ocupação por período")
RES_GRAF_AJUDA = frase("每个圆环 = 该区域自身的装载率（实际装载 / 核载）；名称后为发车数。", "Cada rosca = ocupação da própria regional (carregado ÷ capacidade); ao lado do nome, o nº de viagens.")  # [revisar]
