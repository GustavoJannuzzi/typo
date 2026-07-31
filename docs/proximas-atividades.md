# Próximas atividades

Seis frentes levantadas em 31/07/2026. As seis também estão como cartões no
quadro do `/admin`. Os **prompts prontos** para abrir cada uma em um chat
separado estão no fim deste arquivo — são autocontidos de propósito, então dá
pra colar em qualquer sessão nova sem contexto anterior.

Regra que vale pras seis: `print_v4.py` é a fonte da verdade do algoritmo e o
preset `magalenha` tem que continuar reproduzindo ele bit a bit. Nada aqui
justifica quebrar isso.

---

## 1. Coleção de 6 artes — história do Brasil, texto legível

Seis peças a partir de imagens de livros de história (a pista inicial é a
história da escravidão no Brasil), com o texto **em ordem e legível**, pra
pessoa conseguir de fato ler a história na parede.

**Viável, com um porém que vale entender.** O motor já consome o texto em
ordem: a varredura vai da esquerda pra direita, linha a linha, e o cursor do
stream anda junto (`typography.py`). Então "em ordem" sai de graça com
`text.mode: phrases`. O que briga com a legibilidade é o resto do efeito —
letra pequena nas áreas claras, ondulação e rotação. As alavancas são:

- `font.size_min_mm` mais alto (o piso hoje é 1,5 mm — é o que some de perto)
- `font.size_gamma` mais baixo (menos contraste entre claro e escuro)
- `flow.flex` bem abaixo de 1,0 (menos ondulação e menos rotação de glifo)
- `layout.advance_factor` perto de 1,0 pra não colar as letras

O custo: quanto mais legível, menos a imagem aparece. É um dial entre retrato e
leitura, e cada peça da coleção pode se sentar num ponto diferente dele.

**Domínio público — o terreno é bom.** Século XIX brasileiro está livre:
Jean-Baptiste Debret (já usado em `projects/debret-antropofagia`), Johann
Moritz Rugendas, Auguste Earle e as fotografias de Marc Ferrez. Textos também:
*O Navio Negreiro* de Castro Alves (1869), *O Abolicionismo* de Joaquim Nabuco
(1883), o texto da Lei Áurea e da Lei do Ventre Livre.

**Ainda em aberto:** a curadoria das seis (quais imagens, quais textos, em que
ordem elas contam uma história maior) e a checagem de licença fonte a fonte. O
Gustavo quer **validar imagens e textos antes de plotar**.

---

## 2. QR code tipográfico — selo por obra vendida

QR feito de letras, apontando pro site, um selo único por arte vendida.

**Dá pra fazer, e o motor já pensa do jeito certo.** Um QR é uma matriz de
módulos claros e escuros — que é exatamente o tipo de entrada que o halftone
consome. O que exige cuidado é o que o leitor de QR precisa preservar:

- os três **finder patterns** dos cantos e o **timing pattern** têm que sair
  geometricamente íntegros — melhor desenhá-los sólidos do que "tipografá-los"
- a **quiet zone** de 4 módulos em volta é obrigatória
- usar correção de erro **nível H** (30%) compra a margem pra estilizar o resto
- a malha de letras precisa ficar **presa à grade dos módulos**, senão um glifo
  vaza pro módulo vizinho e o código morre

Bibliotecas: `segno` ou `qrcode` no Python. O teste de aceite é objetivo —
ler o código com o celular, de longe e de perto, impresso e em tela.

**A parte de produto:** cada selo aponta pra uma URL única (`/selo/<id>`), o
que pede uma tabela nova no Supabase e uma página no site mostrando a ficha da
peça. O `/admin` já tem auth e RLS prontos pra pendurar isso.

---

## 3. Variantes de saída por arte (A1, autoral, canvas)

Toda arte deveria sair em N formatos por padrão: A1 pra impressão comum, a
versão autoral com liberdade criativa (o trabalho oficial), e uma pra canvas /
tecido. Democratizar a impressão sem perder o conceito.

**É uma feature de configuração, não de motor.** Hoje um `project.yaml` produz
uma saída. A ideia é uma seção `variants:`, cada uma com overrides de `page` e
de estilo, e o `scripts/render.py` sabendo renderizar uma ou todas.

Medidas que já dá pra fixar: **A1 = 59,4 × 84,1 cm** via `page.mode: fixed`
com `width_cm` / `height_cm`. A autoral segue no `page.mode: from_art`, que é
onde ela é livre. Canvas provavelmente quer DPI próprio e talvez sangria — isso
precisa ser confirmado com uma gráfica de verdade antes de virar código.

**Cuidado central:** mudar tamanho físico muda quantas letras cabem, e o texto
dá menos voltas. Uma variante A1 não é a autoral reduzida — é outra
composição. Vale decidir se `font.base_line_mm` escala junto com a página ou
fica fixo (as duas escolhas são defensáveis e dão resultados bem diferentes).

---

## 4. Landing multi-idioma (pt / en / es / it)

Divulgação já engatilhada na Itália e nos EUA.

**A decisão de arquitetura vem antes do código.** Duas saídas:

- **troca no cliente** — um dicionário JSON por idioma e `data-i18n` nos
  elementos. Simples, mas o Google indexa só uma versão: ruim justamente pra
  quem vai chegar de busca lá fora.
- **uma página por idioma no build** (`/en/`, `/it/`, `/es/`) com `hreflang`.
  Mais trabalho, e é o que serve a divulgação internacional. O Vite já é MPA
  aqui (`build.rollupOptions.input`), então o caminho está aberto.

**Uma decisão de conteúdo que não é óbvia:** título e subtítulo de cada obra
são *parte da arte* — estão impressos no pôster, em português. Traduzir
"O Glorioso Retorno" na galeria seria descrever uma peça que não existe. A
tradução deveria pegar a interface e os textos de apoio, e deixar os títulos
das obras em paz (com tradução ao lado, se fizer falta).

Detecção por `navigator.language`, sempre com **troca manual visível** — quem
está no exterior e quer ler em português não pode ficar preso.

---

## 5. Automação de imagens pro Instagram

O problema real, nas palavras dele: de longe não dá pra ver que a arte é feita
de texto, e o título fica ruim de ler.

**Isso resolve com narrativa, não com filtro.** Um carrossel que vai de longe
pra perto conta sozinho o que a peça é:

1. arte inteira, com o título por cima (a arte de fundo aguenta o texto)
2. um corte intermediário, onde a malha começa a virar letra
3. um macro de verdade, onde se lê a palavra
4. a ficha técnica no estilo da identidade

Formatos: feed 4:5 (1080 × 1350), carrossel no mesmo, stories 9:16.

**Viável direto:** o export já sai em DPI alto, então os cortes saem do PNG
gerado sem re-render. Vira um script em `scripts/` que recebe o projeto e
cospe uma pasta de PNGs prontos, usando as mesmas fontes e as mesmas cores da
identidade (`site/src/styles/base.css` tem os tokens).

---

## 6. Vídeos de navegação e zoom nas artes

Vídeo navegando o site, dando zoom nas artes, com texto animado na identidade
— tudo via Claude Code.

**Dá, e o caminho confiável é captura determinística.** Playwright grava vídeo
de headless Chrome nativamente, mas gravação em tempo real fica refém do
desempenho da máquina e engasga. O caminho melhor: mover a "câmera" por
transform CSS em passos fixos, capturar frame a frame, e montar com `ffmpeg`.
Sai em 60fps limpo e o resultado é reproduzível — roda de novo, sai igual.

**Dependências novas:** `playwright` (Node) e o binário do `ffmpeg`. É a
atividade que mais adiciona peso de ferramenta ao projeto, então vale conferir
se compensa antes de instalar.

**Aviso honesto:** eu consigo escrever e rodar o pipeline, mas não consigo
*assistir* ao vídeo pra julgar se ficou bonito. O julgamento estético do
resultado é do Gustavo — eu entrego o mecanismo e os parâmetros.

---

# Prompts prontos

Um por atividade. São autocontidos: dá pra colar num chat novo, sem contexto
anterior. Todos assumem que o chat abre em `C:\Users\User\Downloads\typo`.

## Prompt 1 — Coleção de 6 artes (história do Brasil)

```
Estou no projeto typo (C:\Users\User\Downloads\typo). Leia o CLAUDE.md antes de
qualquer coisa — em especial a regra de ouro: print_v4.py é a fonte da verdade
do algoritmo e o preset magalenha tem que continuar reproduzindo ele bit a bit.

Quero montar uma coleção de 6 artes a partir de imagens de livros de história do
Brasil. A pista inicial é a história da escravidão. A exigência que manda em
tudo: o texto tem que sair EM ORDEM e LEGÍVEL — a pessoa precisa conseguir ler a
história olhando a parede.

O que já sei do motor e não precisa ser redescoberto:
- "em ordem" já sai de graça: a varredura vai da esquerda pra direita, linha a
  linha, e o cursor do stream anda junto (typography.py). Use text.mode: phrases.
- quem briga com a legibilidade é o resto do efeito. As alavancas são
  font.size_min_mm mais alto (o piso hoje é 1,5 mm), font.size_gamma mais baixo,
  flow.flex bem abaixo de 1,0 (derruba ondulação e rotação de glifo) e
  layout.advance_factor perto de 1,0 pra não colar as letras.
- o custo é real: quanto mais legível, menos a imagem aparece. É um dial entre
  retrato e leitura. Cada uma das 6 peças pode sentar num ponto diferente dele.

Domínio público que já levantei (confirme licença fonte a fonte mesmo assim):
imagens de Jean-Baptiste Debret (já uso em projects/debret-antropofagia), Johann
Moritz Rugendas, Auguste Earle e as fotografias de Marc Ferrez. Textos: O Navio
Negreiro (Castro Alves, 1869), O Abolicionismo (Joaquim Nabuco, 1883), a Lei
Áurea e a Lei do Ventre Livre.

O QUE EU QUERO NESTE CHAT, nesta ordem:
1. curadoria: proponha as 6 peças — qual imagem, qual texto, e em que ordem elas
   contam uma história maior. Justifique a sequência.
2. a checagem de licença de cada fonte, com o link.
3. NÃO renderize nada ainda. Me manda a proposta pra eu validar imagens e textos
   antes de plotar qualquer coisa.

Depois que eu validar, aí sim a gente monta os projects/ e afina os parâmetros
peça a peça.
```

## Prompt 2 — QR code tipográfico (selo por obra vendida)

```
Estou no projeto typo (C:\Users\User\Downloads\typo). Leia o CLAUDE.md antes de
qualquer coisa — em especial a regra de ouro: print_v4.py é a fonte da verdade
do algoritmo e o preset magalenha tem que continuar reproduzindo ele bit a bit.

Quero um QR code feito de letras, apontando pro site: um selo único por arte
vendida.

Por que isso encaixa: um QR é uma matriz de módulos claros e escuros, que é
exatamente o tipo de entrada que o halftone do projeto já consome. O que exige
cuidado é o que o leitor de QR precisa preservar:
- os três finder patterns dos cantos e o timing pattern têm que sair
  geometricamente íntegros. Melhor desenhá-los sólidos do que "tipografá-los".
- a quiet zone de 4 módulos em volta é obrigatória.
- usar correção de erro nível H (30%) compra a margem pra estilizar o resto.
- a malha de letras precisa ficar presa à grade dos módulos. Se um glifo vazar
  pro módulo vizinho, o código morre.

Bibliotecas candidatas: segno ou qrcode (Python). O teste de aceite é objetivo:
ler o código com o celular, de longe e de perto, impresso e em tela. Não me diga
que funciona sem esse teste passar.

Tem uma metade de produto junto: cada selo aponta pra uma URL única (/selo/<id>),
o que pede uma tabela nova no Supabase e uma página no site com a ficha da peça.
O /admin do site já tem auth e RLS prontos — dá pra pendurar isso na mesma
estrutura (veja site/src/admin/).

Comece propondo o desenho da solução (onde entra no código, o que é script novo
e o que reaproveita o motor) antes de sair escrevendo.
```

## Prompt 3 — Variantes de saída por arte (A1, autoral, canvas)

```
Estou no projeto typo (C:\Users\User\Downloads\typo). Leia o CLAUDE.md antes de
qualquer coisa — em especial a regra de ouro: print_v4.py é a fonte da verdade
do algoritmo e o preset magalenha tem que continuar reproduzindo ele bit a bit.
Rode a paridade antes de dar qualquer coisa como pronta:

  TYPO_PARITY=1 .venv/Scripts/python.exe -m pytest tests/test_smoke.py -k parity -q

Quero que toda arte saia em N formatos por padrão: A1 pra impressão comum, a
versão autoral com liberdade criativa (que é o trabalho oficial) e uma pra
canvas/tecido. A ideia é democratizar a impressão sem perder o conceito.

Isso é uma feature de configuração, não de motor. Hoje um project.yaml produz
uma saída. Quero uma seção variants:, cada variante com overrides de page e de
estilo, e o scripts/render.py sabendo renderizar uma variante ou todas.

Medidas que já dá pra fixar: A1 = 59,4 × 84,1 cm via page.mode: fixed com
width_cm / height_cm. A autoral continua em page.mode: from_art, que é onde ela
é livre. Canvas provavelmente quer DPI próprio e talvez sangria — isso eu ainda
preciso confirmar com uma gráfica de verdade, então deixe como pergunta aberta
em vez de chutar um número.

O cuidado central: mudar o tamanho físico muda quantas letras cabem, e o texto
dá menos voltas. Uma variante A1 NÃO é a autoral reduzida — é outra composição.
Me traga a decisão explícita de se font.base_line_mm escala junto com a página
ou fica fixo, com o efeito visual de cada escolha; as duas são defensáveis e dão
resultados bem diferentes.

Restrição dura: a mudança tem que ser puramente aditiva. Um project.yaml sem
seção variants: precisa continuar renderizando exatamente como hoje.
```

## Prompt 4 — Landing multi-idioma (pt / en / es / it)

```
Estou no projeto typo (C:\Users\User\Downloads\typo). O site fica em site/ —
Vite 6 em modo MPA (build.rollupOptions.input com as entradas main e admin).
Leia o CLAUDE.md pra pegar o conceito do projeto antes de mexer no conteúdo.

Quero a landing em quatro idiomas: português, inglês, espanhol e italiano. Tem
divulgação já engatilhada na Itália e nos EUA, então gente de busca lá fora é
público real, não hipótese.

A decisão de arquitetura vem antes do código. As duas saídas:
- troca no cliente: um dicionário JSON por idioma e data-i18n nos elementos.
  Simples, mas o Google indexa só uma versão — ruim justamente pro caso de uso.
- uma página por idioma no build (/en/, /it/, /es/) com hreflang. Mais trabalho,
  e é o que serve a divulgação internacional. O Vite já é MPA aqui, então o
  caminho está aberto.
Me recomende uma e diga o porquê antes de implementar.

Uma decisão de conteúdo que não é óbvia e eu quero respeitada: título e
subtítulo de cada obra são PARTE DA ARTE — estão impressos no pôster, em
português. Traduzir "O Glorioso Retorno" na galeria seria descrever uma peça que
não existe. Traduza a interface e os textos de apoio, e deixe os títulos das
obras em paz (com tradução ao lado, se fizer falta).

Detecção por navigator.language, mas SEMPRE com troca manual visível: quem está
no exterior e quer ler em português não pode ficar preso.

Cuidado com o peso: a landing hoje sai em ~18 KB e é onde o peso importa. Não
quero que a tradução engorde isso significativamente.
```

## Prompt 5 — Automação de imagens pro Instagram

```
Estou no projeto typo (C:\Users\User\Downloads\typo). Leia o CLAUDE.md pra
entender o que o motor faz: ele desenha uma imagem inteira usando letras.

O problema real que quero resolver: no Instagram, de longe não dá pra ver que a
arte é feita de texto, e o título fica ruim de ler.

Minha leitura é que isso se resolve com narrativa, não com filtro. Um carrossel
que vai de longe pra perto conta sozinho o que a peça é:
  1. a arte inteira, com o título por cima (a arte de fundo aguenta o texto)
  2. um corte intermediário, onde a malha começa a virar letra
  3. um macro de verdade, onde se lê a palavra
  4. a ficha técnica no estilo da identidade

Formatos: feed 4:5 (1080 × 1350), carrossel no mesmo, stories 9:16.

Viabilidade: o export já sai em DPI alto, então os cortes saem do PNG gerado sem
re-render nenhum. Quero um script em scripts/ que receba o nome do projeto e
cuspa uma pasta de PNGs prontos pra postar, usando as mesmas fontes e as mesmas
cores da identidade — os tokens estão em site/src/styles/base.css.

Duas coisas que quero que você decida com critério e me explique:
- como escolher ONDE cortar o macro (o recorte tem que cair num pedaço com
  palavra legível, não num vazio)
- como o título por cima da imagem 1 se relaciona com a identidade visual do
  site sem virar um selo genérico de banco de imagem

Não use o motor pra re-renderizar nada. É pós-processamento do PNG exportado.
```

## Prompt 6 — Vídeos de navegação e zoom nas artes

```
Estou no projeto typo (C:\Users\User\Downloads\typo). O site fica em site/
(Vite 6, MPA). Leia o CLAUDE.md pra entender o conceito do projeto.

Quero vídeos navegando o site, dando zoom nas artes, com texto animado na
identidade visual — tudo feito via Claude Code.

O caminho que eu quero que você considere primeiro é captura determinística. O
Playwright grava vídeo de headless Chrome nativamente, mas gravação em tempo
real fica refém do desempenho da máquina e engasga. O caminho melhor: mover a
"câmera" por transform CSS em passos fixos, capturar frame a frame, e montar com
ffmpeg. Sai em 60fps limpo e é reproduzível — roda de novo, sai igual. Se você
achar que estou errado, me diga por quê antes de seguir.

Dependências novas: playwright (Node) e o binário do ffmpeg. É a atividade que
mais adiciona peso de ferramenta ao projeto, então me diga o tamanho real do que
vai ser instalado ANTES de instalar, pra eu decidir se compensa.

Um aviso que vale pros dois lados: você consegue escrever e rodar o pipeline,
mas não consegue assistir ao vídeo pra julgar se ficou bonito. O julgamento
estético é meu. Me entregue o mecanismo e os parâmetros expostos de um jeito que
eu consiga afinar (duração, easing, ponto de zoom, tempo de cada plano) sem
precisar reescrever o script.
```
