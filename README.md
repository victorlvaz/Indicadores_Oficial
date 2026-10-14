# Indicadores (Streamlit)

App web com menu para navegar entre relatórios. Hoje: **Lacre / Deslacre – Linha Secundária**.

## Rodar no seu computador
```
pip install -r requirements.txt
python -m streamlit run app.py
```
(rode dentro da pasta do projeto; no Windows, se `python` não funcionar, use `py`)

## Estrutura
```
app.py                       entrada: monta o menu a partir de relatorios.py
relatorios.py                lista dos relatórios (grupo, título, arquivo da página, ícone, descrição)
.streamlit/config.toml       tema: vermelho #E60000 como única cor de destaque (modo claro e escuro)
paginas/
  inicio.py                  página inicial com atalhos
  lacre_deslacre_tela.py     tela do Lacre/Deslacre
lacre_deslacre/              regras e cálculos do Lacre/Deslacre
  config.py  calculos.py  textos.py  apoio/*.csv
comum/                       partes reaproveitadas por todos os relatórios
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
