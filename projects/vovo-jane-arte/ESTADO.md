# Estado — a arte da vovó Jane

Presente de família: retrato tipográfico da **Jane** com o **Gilber**, feito com
a letra de *Como É Grande o Meu Amor por Você*. **A1 retrato (59,4 × 84,1 cm)**.

**A peça oficial é a v5**, aprovada pelo Gustavo em 12/08/2026.

```bash
.venv/Scripts/python.exe scripts/vovo_jane_arte.py --render
```

- arquivo: `output/vovo_jane_arte_v5_59x84cm_150dpi.pdf` (MediaBox 59,4 × 84,1 cm)
- histórico e motivo de cada versão: `output/VERSOES.md`
- tudo é gerado por **`scripts/vovo_jane_arte.py`**; os parâmetros afináveis
  estão no topo do arquivo, cada um com o número medido que o justifica

## A partitura

`projects/vovo-jane/arte que eu mais gostei.png` — 1101 × 1429 px, gerada no
Gemini. É a **terceira** referência da peça e a que ele aprovou; as duas
anteriores (medalhão sobre foto, e depois anel com a palavra na linha do arco)
foram descartadas por ele e as pastas apagadas em 14/08/2026.

Dela saem: a malha (retrato como tom), a posição dos quatro blocos de tipo, a
paisagem do Rio ao fundo e a paleta.

## A peça, em três camadas

1. **Malha** — o retrato entra como tom e o motor redesenha com as letras da
   música. Sem máscara: nesta referência não há silhueta pra achar (a testa
   dele mede 254 e o fundo 246 — o rosto é mais *claro* que o fundo). Quem
   separa figura de papel é a **paleta**, que pinta cada glifo com a cor
   amostrada da referência.
2. **Tipo** — `como / é grande`, `o / meu`, `AMOR`, `por você`, em Cambria,
   por `display.marks`. São tipo de verdade: na referência o "AMOR" ainda é
   feito de letrinha densa, e é justamente o que ele não queria.
3. **Ficha** — título, subtítulo, quadradinhos e rodapé pelo `compose` do
   motor (`titles.draw: true`), no padrão das outras obras.

## Decisões que já foram tomadas (não refazer sem motivo)

| decisão | valor | por quê |
|---|---|---|
| corpo da malha | **3,0 mm** (letra 2,4–3,75) | é o que ele aprovou olhando o PDF da v4; a v4b, com vão e letra separados, ele recusou |
| paleta ligada | 9 stops + papel | a referência modula o **valor** da letra, não o tamanho; em monocromático a peça sai chapada |
| tinta pelo inverso da cobertura | `COBERTURA = 0.42` | um glifo cobre ~40% da célula; pintar no valor que se quer ver deixa a peça duas vezes mais clara |
| fundo mais claro que o casal | `FUNDO_FORCA = 0.35` | pedido dele; separação por densidade local, não por tom (casal 205–217, paisagem 238–246, se cruzam em luminância) |
| rampa de borda | 2,6 cm, só no fundo | sem ela a malha terminava reta e desenhava um retângulo na página |
| papel | branco no PDF | imprimir em papel creme de verdade, não chapar fundo num A1 inteiro |

## A ficha está conferida

**Roberto Carlos, 1967** — sozinho, sem Erasmo Carlos. Conferido em 05/08/2026
em duas fontes independentes (`pt.wikipedia`, faixas do álbum *Roberto Carlos
em Ritmo de Aventura*, que distingue coautoria; e `letras.mus.br`). O rascunho
original trazia "Roberto Carlos e Erasmo Carlos, 1972", errado nas duas
informações.

Título `JANE E GILBER` e não o nome da música: o texto grande da arte já diz a
música, e repetir seria eco.

## Selo e certificado

Emitido em 19/08/2026: código **E9F3HH**, dono `Jane` (só o primeiro nome, por
privacidade — é o combinado do `CLAUDE.md`). PNG/PDF em
`output/selos/E9F3HH.{png,pdf}`, registro em `site/src/data/seals.json`.

`certificado.md` é rascunho meu (a carta), nunca revisado por ele — o resto
da ficha (título, subtítulo) vem direto do `project.yaml` e está conferido.
Página: `/certificado/E9F3HH/`.

O close-up da página (`site/public/art/vovo-jane-arte-detail.webp`) **não**
pode sair da busca automática do `build_site_assets.py`: ela acha a janela
mais densa em qualquer lugar da caixa de arte, e "AMOR" sólido é mais denso
que qualquer trecho de malha — o recorte cairia em cima da palavra grande, não
da letra miúda que a legenda promete. Gerado à mão excluindo as quatro caixas
de `display.marks` da busca antes de rodar `find_densest_window`. Se o PDF
mudar de versão outra vez, os dois webp em `site/public/art/` têm que ser
regenerados do mesmo jeito — não só `scripts/build_certificates.py`, que usa
a busca automática e cairia no mesmo erro.

## O que falta

1. **Plotar e julgar no papel.** É a decisão aberta e nenhuma outra depende
   dela. No monitor a peça é vista a ~8% do tamanho impresso.
2. **Resolução.** A referência tem 1101 px de largura contra os 3035 que um A1
   a 150 dpi pede — upscale de 2,69×. Não há como pedir maior: é Gemini, e
   regenerar dá outro desenho (foi o que aconteceu quando ele tentou). O motor
   é um redutor, então o tom passa; o traço fino não.
3. **A segunda peça, `vovo-jane-detalhes`** (foto do evento + *Detalhes*),
   está parada num estágio anterior. Ele ainda não comentou a ressalva que
   levantei: *Detalhes* é, ao pé da letra, música de quem foi embora.

## Insumos que ficaram

| caminho | o que é |
|---|---|
| `projects/vovo-jane/arte que eu mais gostei.png` | **a partitura** — a referência aprovada |
| `projects/vovo-jane/refs/` | material de origem da família: a selfie boa (1024×1536, restaurada, sem fundo), o rascunho dele, as referências descartadas. **Não apagar**: é original, não é gerado |
| `projects/vovo-jane/text/como-e-grande.txt` | a letra da música |
| `projects/ainda-estou-aqui-teste/` | o teste de plotagem 1:1 que estabeleceu a faixa de corpo legível |
