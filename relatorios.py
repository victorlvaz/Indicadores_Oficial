"""Lista de relatórios do app. Para adicionar um relatório novo:
   1) crie a página em paginas/<nome>_tela.py
   2) acrescente um item na lista RELATORIOS abaixo.
O menu lateral e a página inicial são montados a partir desta lista.

Regra bilíngue: "grupo" e "titulo" levam chinês e português lado a lado ("支线 Linha secundária");
"descricao" leva o chinês na 1ª linha e o português na 2ª (use frase()).
"""
from comum.idioma import bi, frase

RELATORIOS = [
    {
        "grupo": bi("支线", "Linha secundária"),
        "titulo": bi("支线解封车率", "Lacre / Deslacre"),
        "arquivo": "paginas/lacre_deslacre_tela.py",
        "url": "lacre-deslacre",
        "icone": ":material/lock:",
        "descricao": frase("按区域统计封车率、解车率与封车准点率（集货与散货），含排名、目标和每日趋势。",
                           "Taxa de lacre, deslacre e pontualidade do lacre por região (Coleta e Entrega), "
                           "ranking, metas e tendência diária."),
    },
    {
        "grupo": bi("支线", "Linha secundária"),
        "titulo": bi("SM状态统计", "Estatística de Status dos SMs"),
        "arquivo": "paginas/sm_tela.py",
        "url": "sm",
        "icone": ":material/location_on:",
        "descricao": frase("按区域统计 SM 监控占比（集货与散货），数据来自 JMS 与 TECHIS，含趋势与未监控任务。",
                           "Rastreamento efetivo dos SMs por regional (Coleta e Entrega), com dados do JMS e do "
                           "TECHIS, tendência e viagens sem SM."),
    },
    {
        "grupo": bi("支线", "Linha secundária"),
        "titulo": bi("支线打卡率", "Taxa de Uso de APP"),
        "arquivo": "paginas/app_uso_tela.py",
        "url": "uso-app",
        "icone": ":material/smartphone:",
        "descricao": frase("按区域统计司机 APP 打卡率（集货与散货），含排名、目标、趋势与汇总。",
                           "Taxa de uso do APP pelo motorista (check-out e check-in) por regional (Coleta e Entrega), "
                           "ranking, meta, tendência e resumo."),
    },
    {
        "grupo": bi("支线", "Linha secundária"),
        "titulo": bi("支线准点率", "Pontualidade (Chegada e Saída)"),
        "arquivo": "paginas/pontualidade_tela.py",
        "url": "pontualidade",
        "icone": ":material/schedule:",
        "descricao": frase("按区域统计到达与发车准点率（集货与散货），含排名、目标、趋势与汇总。",
                           "Taxa de chegada e de saída no prazo por regional (Coleta e Entrega), "
                           "ranking, meta, tendência e resumo."),
    },
    {
        "grupo": bi("支线", "Linha secundária"),
        "titulo": bi("装载率", "Taxa de Ocupação"),
        "arquivo": "paginas/ocupacao_tela.py",
        "url": "ocupacao",
        "icone": ":material/local_shipping:",
        "descricao": frase("按区域和车型统计车辆装载率（集货与散货），含趋势与汇总。",
                           "Ocupação dos veículos por regional e tipo de veículo (Coleta e Entrega), "
                           "tendência e resumo."),
    },
    {
        "grupo": bi("支线", "Linha secundária"),
        "titulo": bi("浪费率", "Taxa de Desperdício"),
        "arquivo": "paginas/desperdicio_tela.py",
        "url": "desperdicio",
        "icone": ":material/trending_down:",
        "descricao": frase("按区域和车型统计装载浪费（未被占用的运力，集货与散货），含趋势与汇总。",
                           "Desperdício de capacidade (o que não foi ocupado) por regional e tipo de veículo "
                           "(Coleta e Entrega), tendência e exportação. Usa a mesma base da Taxa de Ocupação."),
    },
    {
        "grupo": bi("支线", "Linha secundária"),
        "titulo": bi("物流成本指标", "Indicadores de Custos"),
        "arquivo": "paginas/custos_tela.py",
        "url": "custos",
        "icone": ":material/payments:",
        "descricao": frase("按区域、车型和承运商类型统计运费、公里与包裹，含单票成本、每公里成本、趋势与稽核。",
                           "Frete total, KM e pacotes por regional, tipo de veículo e tipo de transportadora, "
                           "frete por pacote e por KM, tendência e auditoria de preenchimento."),
    },
    {
        "grupo": bi("设置", "Cadastros"),
        "titulo": bi("区域负责人", "Líderes regionais"),
        "arquivo": "paginas/lideres_tela.py",
        "url": "lideres",
        "icone": ":material/group:",
        "descricao": frase("登记各区域负责人，用于成本催办消息中的 @ 提醒。",
                           "Cadastro dos líderes de cada regional, usado na cobrança e nas menções do Feishu."),
    },
    {
        "grupo": bi("设置", "Cadastros"),
        "titulo": bi("发送汇总", "Envio geral"),
        "arquivo": "paginas/envio_geral_tela.py",
        "url": "envio-geral",
        "icone": ":material/send:",
        "descricao": frase("一次性把所有 JMS 指标依次发送到飞书（指标、文件），可选日/周/月/年。",
                           "Envia ao Feishu todos os indicadores com JMS, um por vez (indicador e arquivo), "
                           "com prévia e período Dia/Semana/Mês/Ano."),
    },
]
