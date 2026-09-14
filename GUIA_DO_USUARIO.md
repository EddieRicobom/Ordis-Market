# ORDIS MARKET — Guia do Operador

> "Operator! Você chegou. Eu já estava começando a me preocupar com os preços sozinho." — Ordis

Este é o guia pra quem só quer **usar** o Ordis Market, sem se importar com
código. Se você quer entender como o app funciona por dentro, isso está no
`README.md` e no `ARCHITECTURE.md` — este guia aqui é só o "como usar".

---

## O que é isso, afinal?

O Ordis Market pega o seu inventário do Warframe e compara com os preços
reais do warframe.market, pra te dizer:

- quanto seu inventário vale em Platina;
- o que vale a pena vender e o que vale a pena guardar;
- se compensa mais vender uma peça Prime avulsa ou o set inteiro;
- se compensa mais vender por Platina ou guardar pros Ducats do Baro.

Ele **nunca** mexe no jogo, nunca lê a memória do Warframe, nunca faz nada
sozinho dentro do jogo. Ele só lê um arquivo que você importa e consulta
o mercado. É só uma calculadora chique com personalidade de Cephalon.

---

## Como abrir o programa

Duas formas:

1. **Mais fácil**: dê duplo clique em `run.bat`. Ele confere se você tem
   Python instalado, instala o que faltar sozinho, e abre o app.
2. Se preferir pelo terminal: `python run.py`

Na primeira vez, pode demorar um pouco pra instalar as dependências. Da
segunda vez em diante é rápido.

## Como atualizar pra uma versão nova

Recebeu uma cópia nova do Ordis Market? Só substitua todos os arquivos
dessa pasta pelos novos, e dê duplo clique em `run.bat` de novo. É só
isso — não existe nenhuma etapa separada de "compilar" ou "build" pra se
preocupar. Toda vez que você abre o app assim, ele confere sozinho se
todas as dependências estão instaladas e atualizadas, sem você precisar
rodar nada manualmente.

Se quiser confirmar que está na versão certa, olhe a barra de título da
janela (ou o textinho pequeno embaixo de "ORDIS MARKET") — os dois
mostram o número da versão atual.

> Você pode notar que também tem um arquivo `build.bat` nessa pasta.
> Ignore ele, a não ser que você especificamente queira um `.exe` único
> que não precise ter Python instalado — esse caminho é mais avançado e
> precisa ser rodado de novo a cada atualização. Pra todo mundo, `run.bat`
> já é suficiente.

---

## O fluxo completo, passo a passo

### 1. Não precisa fazer nada antes de importar

Assim que o app abre, ele já busca sozinho a lista de itens do
warframe.market e os nomes oficiais dos itens (dados da própria Digital
Extremes). Você não precisa clicar em nada pra isso acontecer.

### 2. Conseguir o seu inventário

Você tem três jeitos, escolha um:

| Botão | O que faz |
|---|---|
| **GRAB INVENTORY** | Roda um programinha externo que você já tem (tipo o warframe-api-helper) e importa o resultado sozinho. |
| **IMPORT INVENTORY** | Você escolhe manualmente um arquivo `.json` do seu inventário. |
| **WATCH FOLDER** | O Ordis Market fica de olho numa pasta e importa sozinho toda vez que aparecer um arquivo novo lá. |

**LAUNCH WARFRAME** é só um atalho pra abrir o jogo pela Steam — não tem
nada a ver com importar o inventário, é só conveniência.

> Se você já importou antes, não precisa fazer isso de novo. O app lembra
> o último inventário e a última análise, mesmo depois de fechar e abrir
> de novo.

### 3. Clique em ANALYZE INVENTORY

Essa é a etapa que realmente faz a mágica: cruza seu inventário com os
preços do mercado e preenche a tabela.

Enquanto roda, você vê uma barrinha de progresso e o Ordis comentando
sobre o processo (às vezes ele reclama um pouco, é normal).

### 4. Leia a tabela

Cada coluna significa:

| Coluna | O que é |
|---|---|
| **Item** | Nome do item. Se for um mod, aparece o rank entre parênteses, tipo "Serration (Rank 10)". |
| **Qty** | Quantos você tem. |
| **Price** | Preço atual mais barato à venda no mercado. |
| **Total** | Price × Qty — quanto essa pilha toda vale. |
| **Liquidity** | Quão fácil é vender isso (VERY HIGH = vende rápido, VERY LOW = pode demorar). |
| **Score** | Nota de 0 a 100 juntando valor + liquidez + quantidade. Quanto maior, melhor candidato a vender. |
| **Recommendation** | SELL, CONSIDER ou KEEP — o resumo direto do Score. |
| **Ducats** | Se for item Prime com valor em Ducats, mostra se compensa mais vender por Platina ou guardar pros Ducats. |
| **Wiki** | Link direto pra página do item na Wiki oficial do Warframe. |
| **Sell** | Link direto pra página do item no warframe.market, pra você postar o anúncio de venda você mesmo. |

Clique em qualquer nome de coluna pra ordenar por ela (igual Excel).
Clique de novo pra inverter a ordem.

### 5. Use os filtros se a lista estiver grande

- **Search**: digite parte do nome do item.
- **All Items / Tradable Only / Prime Only**: filtra por categoria.
- **Min Score**: só mostra itens com nota acima de X.
- **Hide Prime Sets**: esconde os sets completos montados (tipo "Mesa
  Prime Set"), se você só quer ver o preço das peças separadas.

### 6. Os botões extras (opcionais, use quando quiser)

| Botão | Quando usar |
|---|---|
| **UPDATE ITEMS** | Se acha que o catálogo está desatualizado (raro, ele já se atualiza sozinho). |
| **UPDATE MARKET** | Se quer preços mais frescos, ignorando o que já está guardado em cache. |
| **UPDATE WIKI** | Pra buscar os links da Wiki dos itens da análise atual. **Pode demorar** num inventário grande — é normal, é uma busca educada num site de terceiros, item por item. Da segunda vez em diante é rápido, porque ele lembra o que já buscou. |
| **EXPORT** | Salva a tabela atual em CSV, JSON ou Excel. |

Repare que alguns desses botões ficam **cinza (desabilitados)** até fazer
sentido usá-los — por exemplo, EXPORT só liga depois que você analisou
alguma coisa. Se um botão está cinza, passe o mouse em cima: ele te fala
o que fazer antes.

**Tudo tem uma dica explicativa (tooltip).** Todo botão, filtro e até os
títulos das colunas da tabela se explicam se você deixar o mouse parado
em cima por um instante — se tiver dúvida sobre o que algo faz, é só
esperar um pouco com o mouse ali.

---

## Como saber o que já está carregado

Logo abaixo do título, tem duas linhas de status:

- **Total Items / Tradable / Estimated Value / Last Import / Last Analysis**
  — o resumo da sua análise atual.
- **Catalog / Item Names / Wiki Links** — quantos itens, nomes e links da
  Wiki o Ordis já conhece, sem precisar clicar em nada pra descobrir.

Se você reabrir o app e essas informações já estiverem preenchidas, é
porque ele lembrou tudo sozinho — não precisa clicar em nada de novo, a
não ser que você tenha mudado alguma coisa no seu inventário.

---

## Perguntas comuns

**"Só apareceram alguns itens com preço, o resto ficou N/A."**
Provavelmente o catálogo ainda não conhece aquele item, ou ele
genuinamente não é vendável no mercado (tipo um Warframe já montado — só
as peças soltas são vendáveis). Tente clicar em UPDATE ITEMS. A mensagem
depois de analisar já te avisa se a proporção de itens reconhecidos
parece baixa.

**"UPDATE WIKI está demorando muito."**
É esperado na primeira vez, principalmente com inventários grandes. É uma
busca item por item, educada, num site de terceiros. Da próxima vez, os
nomes já resolvidos são pulados automaticamente — só demora de novo se
seu inventário mudar bastante.

**"Um item apareceu em vermelho."**
Significa que teve algum problema com ele (não foi encontrado, não é
vendável, ou o mercado não respondeu). Passe o mouse em cima do nome pra
ver o motivo exato.

**"Fechei e abri o app, sumiu tudo?"**
Não deveria — a última análise é restaurada automaticamente. Se você
reimportou um inventário diferente nesse meio tempo, aí sim a análise
antiga é apagada de propósito (porque ela seria de um inventário diferente
do atual, e mostrar ela seria enganoso).

**"Posso confiar 100% nos preços?"**
São os preços **atualmente listados** no warframe.market — não é uma
garantia de venda, é uma referência. Preço listado nem sempre é preço que
vende rápido; olhe também a coluna Liquidity.

---

## O que o Ordis Market nunca faz

- Nunca lê a memória do Warframe.
- Nunca modifica arquivos do jogo.
- Nunca automatiza jogatina, troca ou qualquer ação dentro do jogo.
- Nunca posta anúncios de venda sozinho — o botão Sell só abre a página
  pra você postar manualmente.
- Nunca precisa da sua senha ou login de nada.

Se quiser os detalhes técnicos de por que essas decisões foram tomadas,
tem tudo no `RESEARCH.md`.

---

*Dúvidas, sugestões ou bugs: é só falar. O Ordis está sempre "ouvindo",
mesmo não tendo ouvidos.*
