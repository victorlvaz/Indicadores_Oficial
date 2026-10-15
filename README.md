# Indicadores (Streamlit)

App web com menu para navegar entre relatórios. Hoje: **Lacre / Deslacre – Linha Secundária**.

## Rodar no seu computador
```
pip install -r requirements.txt
python -m streamlit run app.py
```
(rode dentro da pasta do projeto; no Windows, se `python` não funcionar, use `py`)

## Histórico em banco de dados (Lacre / Deslacre)
Os relatórios agora são **enviados uma vez** e ficam gravados num banco; a tela lê sempre do histórico.
1. Na barra lateral, envie o relatório consolidado e clique em **Salvar no histórico**.
   - Reenviar o mesmo dia só **atualiza** as viagens (chave: ID + estação de chegada + horário planejado); não duplica e
     não apaga viagens que só estavam no envio anterior. Depois de salvar, o arquivo sai da lista.
   - A aba *Base / Diagnóstico* mostra o histórico de cargas (arquivo, quantas linhas novas e quantas atualizadas).
2. **Onde fica o banco:** por padrão, um arquivo SQLite local em `dados/historico.db` (não vai para o GitHub).
   Para usar o servidor da empresa, informe só a URL de conexão, sem mudar código:
   - arquivo `.streamlit/secrets.toml`:
     ```
     [banco]
     url = "postgresql+psycopg2://usuario:senha@servidor:5432/indicadores"
     ```
     ou a variável de ambiente `INDICADORES_DB_URL`. Exemplos para SQL Server e MySQL estão em `comum/banco.py`.
   - Instale o driver do banco (`psycopg2-binary`, `pyodbc` ou `pymysql`). As tabelas `lacre_viagens` e `lacre_cargas`
     são criadas sozinhas (o usuário precisa de permissão para criar tabelas).
   - Para levar o que já está no SQLite para o servidor, é só reenviar os relatórios (ou pedir a migração).
3. O que fica guardado é a base **já tratada** (depois das regras de exclusão). As regras agora são fixas, em
   `lacre_deslacre/config.py` — não há mais caixas de seleção na tela.
4. **Backup:** com SQLite, copie `dados/historico.db`. No servidor, o backup é da TI.
5. No Streamlit Community Cloud o disco é temporário: SQLite lá perderia o histórico. Use o servidor da empresa.

## Histórico do SM (SM状态统计)
Mesmo banco e mesmo fluxo do Lacre/Deslacre, nas tabelas `sm_viagens` e `sm_cargas`.
- Envie os relatórios JMS (Coleta e/ou Entrega) **e a extração do TECHIS** e clique em **Salvar no histórico**
  (sem o TECHIS o botão não salva, porque os SMs realizados ficariam em 0). Depois de salvar, os arquivos saem da lista.
- Chave da viagem: tipo + ID da tarefa. Reenviar atualiza a viagem; a contagem de SMs do TECHIS fica com o **maior**
  valor entre o já gravado e o do arquivo novo (um TECHIS mais recente pode não cobrir dias antigos).
- O SM realizado nunca passa do previsto (regra fixa); o previsto usa a coluna G, ou a D se a G estiver vazia, e vale a
  que tiver mais trechos. Não há mais caixas de regras na tela.
- Arquivos enviados e ainda não salvos já entram nas tabelas (aviso na tela).
- A aba **Resumo** tem filtro de regional, visão por dia/semana/mês e ano (padrão: ano corrente), com Coleta e Entrega.

## Taxa de Uso de APP (支线打卡率)
Mesmo relatório consolidado do Lacre/Deslacre, mesma lógica de histórico (botão "Salvar no histórico", tabelas
`app_viagens`, `app_cargas`, `app_transportadores`). Taxa = (check-outs + check-ins feitos) / (viagens x 2); Coleta agrupa
pela regional de saída, Entrega pela de chegada; meta 95%. Regras (passo a passo do Documents): só Concluído e Em Trânsito,
excluir rotas do mesmo SC (coletas e entregas), excluir Franqueados e, se o transportador vier vazio, usar o último valor
conhecido da viagem. Todas as regionais (inclusive GP, CE, BA e SR) entram no total, como na planilha do Lucas.
Validar: `python validar_app_uso.py "Taxa_uso_de_APP.xlsx" ["relatorio_bruto.xls"]`.

## Período e comparação
- **Período de análise:** Dia, Semana (segunda a domingo), Mês ou Ano, mais a opção *Todos (acumulado)*.
- **Comparar com:** *Período anterior* (dia anterior, semana anterior, mês anterior, ano anterior) ou
  *Mesmo período do ano passado*. As tabelas ganham a taxa comparada e a variação em **pontos percentuais** (▲ subiu,
  ▼ caiu em vermelho). Com *Todos* não há comparação.
- As abas de **tendência** seguem o período escolhido (dias, semanas, meses ou anos).

## Estrutura
```
app.py                       entrada: monta o menu a partir de relatorios.py
relatorios.py                lista dos relatórios (grupo, título, arquivo da página, ícone, descrição)
.streamlit/config.toml       tema: vermelho #E60000 como única cor de destaque (modo claro e escuro)
paginas/
  inicio.py                  página inicial com atalhos
  lacre_deslacre_tela.py     tela do Lacre/Deslacre
  sm_tela.py                 tela do SM
lacre_deslacre/              regras e cálculos do Lacre/Deslacre
  config.py  calculos.py  textos.py  apoio/*.csv
  historico.py  gravar/ler o histórico no banco     resumo_ui.py  aba Resumo
sm/                          regras e cálculos do SM (config, calculos, textos, historico, resumo_ui, apoio/*.csv)
comum/                       partes reaproveitadas por todos os relatórios
  banco.py      conexão com o banco (SQLite por padrão, URL da empresa por configuração)
  periodos.py   dia/semana/mês/ano e comparação      graficos.py  gráficos vermelho/cinza
  tema.py       cores (VERMELHO = "#E60000")
  idioma.py     bi(), frase() e cabecalho() para os textos em chinês + português
  estilos.py    cor de meta nas tabelas      exportar.py   Excel
  sparkline.py  tabela de tendência com mini-gráficos de linha e pontos
validar_lacre_deslacre.py    confere o cálculo contra a planilha finalizada
```

## Padrão visual e de idioma
- **Cor:** só vermelho `#E60000`. Taxa abaixo da meta = fundo vermelho com texto branco; meta atingida = sem cor.
  Nada de verde. Para trocar o tom: `comum/tema.py` e `.streamlit/config.toml`.
- **Idioma:** todo nome aparece em chinês + português.
  - Título da página: chinês ACIMA do português (`cabecalho("支线解封车率", "Lacre / Deslacre Linha Secundária")`).
  - Demais nomes (menu, abas, barra lateral, colunas, abas do Excel): LADO A LADO (`bi("支线", "Linha secundária")`).
  - Frases longas (avisos, ajudas): chinês na 1ª linha, português na 2ª (`frase(zh, pt)`).
- Os textos de cada relatório ficam num `textos.py` próprio. Em `lacre_deslacre/textos.py` cada termo está marcado
  `[planilha]` (já existia na planilha finalizada) ou `[revisar]` (escrito sem confirmação de falante nativo).

## Adicionar um relatório novo
1. Crie a pasta do relatório com suas regras (copie `lacre_deslacre/` como modelo): `config.py`, `calculos.py`, `textos.py`.
2. Crie a tela em `paginas/<nome>_tela.py`, começando com `cabecalho(zh, pt)` e usando os textos do `textos.py`.
3. Acrescente um item na lista `RELATORIOS` de `relatorios.py` (grupo e título com `bi()`, descrição com `frase()`).
   O menu e a página inicial se atualizam sozinhos.

## Publicar (GitHub + Streamlit Community Cloud)
- Repositório **privado**. Nunca suba relatórios reais: o `.gitignore` já bloqueia `.xls`, `.xlsx` e `.csv`
  (exceto as listas de apoio em `lacre_deslacre/apoio/`).
- Em share.streamlit.io: repositório, branch `main`, arquivo principal `app.py`.
- Atualizar o app = alterar os arquivos e enviar (commit + push) para o GitHub.
- Os relatórios são enviados pela própria tela do app; não ficam no repositório.

## Validar o Lacre/Deslacre
```
python validar_lacre_deslacre.py "planilha_finalizada.xlsx"
```
Deve terminar com "39 linhas comparadas, 0 divergências".
