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

## A aba HOME (a primeira tela)

Ao abrir o programa você cai na **HOME**, um resumo de uma tela com o que o Ordis
já sabe. Nada aqui é dado novo: é a sua última análise, o progresso dos seus sets
Prime e dois calendários, organizados pra você ler em dez segundos.

- **A frase do Ordis** no topo é escolhida de uma lista fixa conforme a sua
  situação (Baro na cidade, sets prontos pra vender, muitos itens negociáveis...).
  Sem IA, sem internet.
- **Os seis cards**: valor estimado, tamanho do inventário, itens negociáveis,
  sets Prime prontos pra montar, sets a uma peça de ficar prontos e os Ducats das
  suas peças Prime. Os dois cards de sets precisam das tabelas de relíquias (aba
  RELICS); até lá mostram "-".
- **O que merece atenção** lista o que foi encontrado (itens com nota SELL, itens
  que valem mais como Ducats, Prime Sets montados, muitos duplicados, preços
  antigos...). Clique numa linha, ou em qualquer card, pra ir pra tela
  correspondente na aba Market ou Relics.
- **Baro Ki'Teer** e **Prime Resurgence** mostram contagem regressiva ao vivo, a
  data no *seu* fuso e uma barra com o quanto do ciclo já passou.
- **Coming up** são os próximos eventos, em ordem.

**Efeitos holográficos:** o emblema é projetado de uma base e de vez em quando
pisca com um glitch vermelho/ciano, os cards têm scanlines discretas e uma
varredura de luz ocasional, os números brilham e a frase do Ordis é digitada
quando muda. Só rodam enquanto a Home está na tela. Pra reduzir movimento,
coloque `"home_animations": false` em `data/settings.json`.

**Sobre essas datas:** o Ordis Market não se conecta ao jogo pra isso. O Baro é
calculado pelo ciclo fixo dele (a cada 14 dias, sexta 13:00 UTC, 48 horas) e o
Prime Resurgence pela rotação de 28 dias (quinta 18:00 UTC; ela anda em relação
ao mês do calendário, não vira todo dia 1). Batem com datas publicadas de 2023 a
2026, mas um evento especial pode deslocar uma delas, então trate como estimativa.
Quais Primes estão no cofre do Resurgence ele não tem como saber offline.

**Atualização automática de preços:** ao abrir o programa com um inventário
carregado, ele atualiza os preços do mercado sozinho, exatamente como apertar
**UPDATE MARKET** (a menos que a última análise tenha menos de 10 minutos ou você
esteja no modo offline). Pra desligar, coloque `"auto_update_market_on_start": false`
em `data/settings.json` (e `"auto_update_min_age_seconds"` muda a janela de 10 min).

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

### 7. A aba RELICS

Ao lado de **MARKET** existe a aba **RELICS**. Ela responde: *"quais sets Prime
eu consigo completar abrindo relíquias que eu já tenho?"*

- Ela usa o mesmo inventário que você importou na aba Market (peças **e**
  relíquias). Importe primeiro, depois abra a aba. Ela se atualiza sozinha
  quando você importa outro inventário.
- Na primeira vez que você abre, ela baixa uma vez as tabelas de drop das
  relíquias (uns 10 MB, do dataset público *warframe-items* do WFCD) e guarda
  no seu PC. Depois disso funciona offline. Clique em **UPDATE RELIC DATA**
  quando sair Prime novo (a linha de status avisa quando os dados têm mais de
  uma semana).
- Cada linha é um set Prime: peças que você tem, status, o que falta e **quais
  relíquias suas abrir** (as que cobrem mais primeiro, ex.: `Neo C9 ×11 → Blueprint`).
  Peças de Warframe contam tanto se você tem o Blueprint (diagrama) quanto o
  Component já construído.
- **Status:** *Completable* = tudo que falta cai de alguma relíquia sua;
  *Partial* = só parte cai; *Complete* = nada falta.
- A lista suspensa alterna entre *dá pra completar*, *parcialmente coberto*,
  *já completo*, *todo set que tenho uma peça* e *todos os sets Prime*; a caixa
  de busca acha um set. Clique numa linha pra ver o detalhe embaixo: cada peça
  que falta, quais relíquias dropam, a chance por abertura e a chance se você
  abrir todas as cópias que tem.

As chances são do refinamento que você tem (Intact é pior que Radiant).
Relíquias que não estão nos dados (muito novas, ou Requiem) são ignoradas.

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
