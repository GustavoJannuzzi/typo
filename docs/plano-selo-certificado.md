# Plano — Selo tipográfico e página de certificado

Spec de implementação. O selo (o QR feito de letras) **já existe e passa nos
testes**; o que falta é a metade de produto: a página que o QR abre.

Leia o `CLAUDE.md` antes. Em especial a **regra de ouro**: `print_v4.py` é a
fonte da verdade do algoritmo e o preset `magalenha` tem que continuar
reproduzindo ele bit a bit. **Nada neste plano toca no motor de render.**

```bash
# antes de dar qualquer etapa como pronta
TYPO_PARITY=1 .venv/Scripts/python.exe -m pytest -q
```

---

## 1. Estado atual — o que já está pronto

| arquivo | o que faz | estado |
| --- | --- | --- |
| `src/typo/seal.py` | desenha o QR com as letras da obra | ✅ 26 testes |
| `scripts/make_seal.py` | CLI: gera PNG + PDF, se autoverifica | ✅ |
| `tests/test_seal.py` | decodifica de volta com `zxing-cpp` | ✅ |
| `pyproject.toml` | extras `[seal]` (segno) e `[dev]` (zxing-cpp) | ✅ |

O selo de referência sai **V4, ECC H, 33×33 módulos, 1,71 mm por módulo,
6,94 cm, 381 letras, 148 sólidos**, e lê de volta em nativo, 800 px e 400 px.

**Pendência que não é de código:** o teste de celular (imprimir e escanear de
perto e de longe) ainda não foi feito. Ele não bloqueia nada deste plano, mas
bloqueia emitir selo de obra vendida.

---

## 2. Decisões já tomadas — não re-discutir

| decisão | valor | porquê |
| --- | --- | --- |
| Domínio | `https://typo-jet.vercel.app` | aprovado pelo Gustavo. Se mudar, ele reemite os selos e avisa os clientes — é decisão dele, assumida. |
| Onde mora | **estático, gerado na build** | o site já gera `/en/`, `/es/`, `/it/` e `/admin/` como pastas reais. Uma pasta por selo é o mesmo padrão: zero infra nova, zero RLS, prévia de link no WhatsApp. |
| Banco | **nenhum** | entra só quando for preciso emitir selo sem deploy. Hoje não é. |
| Nome do comprador | **não aparece** | evita dado pessoal em URL pública, e a obra pode ser revendida. |
| Conteúdo | carta + contagem + imagem/zoom | escolha do Gustavo. **Sem ficha técnica** — é uma linha adicionar depois se ele mudar de ideia. |
| Tiragem | opcional por obra | mostra edição só quando existir. |
| Idioma | **só pt**, com `noindex` | é artefato pessoal, não vitrine de busca. |
| Caminho | `/certificado/<CODE>/` | medido: `/S/`, `/SELO/` e `/CERTIFICADO/` custam **os mesmos 33 módulos**. O nome legível é de graça. |
| `core_ratio` | `0.18` | medido contra QR liso: 0.00→2/23 leituras, 0.10→20/23, 0.18→23/23, acima não compra nada. Ver docstring de `SealSpec`. |

---

## 3. A contagem — fórmula validada

O conteúdo mais forte do e-mail de entrega (`emails/entrega-emicida.html`) é
**gerável**, não escrito à mão. A fórmula foi validada contra aquele e-mail
como gabarito, e bateu **10/10 nas ocorrências de palavra**.

### A fórmula

```
volta            = "   ".join(linhas_do_txt) + "   "     # modo `phrases`
nao_espacos      = quantidade de chars != " " em `volta`
voltas           = works.json[slug].glyphs / nao_espacos
ocorrencias(p)   = round( conta_de_p_em_uma_volta * voltas )
```

### Por que `nao_espacos` e não `len(volta)`

Em `typography.py:126-131` o cursor do stream **anda no espaço**, mas
`stats.glyphs` **não conta espaço**:

```python
ch = streams[rid][cursors[rid] % stream_lens[rid]]
cursors[rid] += 1
if ch == " ":
    x += fs * layout.space_advance_factor
    continue        # <- sem stats.glyphs += 1
```

Então cada volta completa contribui exatamente `nao_espacos` para o total de
glifos. Dividir por `len(volta)` daria voltas a menos e a contagem inteira sairia
errada.

### Verificação contra o gabarito (emicida, `glyphs = 40413`)

```
frases ............ 62            gabarito: 62         OK
volta ............. 2081 chars, 1584 nao-espaco
voltas ............ 25,51         gabarito: "25 e meia"  OK

levanta / anda / vai ......... 357   gabarito 357   OK
sonho / quem / sei / onde .... 102   gabarito 102   OK
somos / seguir / nossa ....... 77    gabarito 77    OK
```

### A única divergência

Total de palavras: calculado **9.516**, e-mail diz **9.542** (−26, 0,27%). O
e-mail usou 374 palavras por volta; `volta.split()` dá 373. É diferença de
definição na borda da volta, não erro de fórmula.

**Regra a fixar:** `palavras_por_volta = len(volta.split())` (373). O gerador
passa a ser o canônico daqui pra frente; o número do e-mail antigo fica como
está. Não persiga os 26.

### Limitação conhecida

Obras com `text.regions` (várias correntes, ex. `cadeirada-datena`) têm um
cursor por região — a matemática de "voltas" acima não vale. Nessas, ou a
contagem é por região, ou o certificado sai sem a seção. **Detecte e falhe alto**
em vez de gerar número errado num certificado.

---

## 4. Modelo de dados

Três arquivos, cada um com um dono claro. Todos **vão pro git**.

### 4.1 `site/src/data/seals.json` — o registro (gerado por `make_seal.py`)

```jsonc
[
  {
    "code": "7QK4M2",                                    // Crockford base32, 6 chars
    "work": "ouro-marrom",                               // slug, casa com works.json
    "payload": "HTTPS://TYPO-JET.VERCEL.APP/CERTIFICADO/7QK4M2",
    "edition": null,                                     // ou { "n": 3, "total": 5 }
    "issuedOn": "2026-08-03",
    "sizeCm": 6.94,
    "dpi": 600
  }
]
```

- **O `payload` é gravado, não recalculado.** Ele é o que está impresso no
  papel. Se o domínio mudar, selos antigos mantêm o payload antigo e o novo
  entra só nos novos — sem isso, mudar o domínio reescreveria silenciosamente o
  histórico e a página não bateria mais com o papel.
- Ordenado por `issuedOn`, depois `code`. Diff estável no git.

### 4.2 `projects/<slug>/certificado.md` — a carta (escrita à mão)

O **único** conteúdo manual do sistema.

```markdown
---
palavra: levanta          # a palavra-herói da contagem
titulo: O Glorioso Retorno   # opcional; default = works.json title
---

Esta arte não foi desenhada com traço — foi escrita. Cada sombra do retrato é
uma letra de *Levanta e Anda*, e as letras mudam de tamanho conforme a foto
escurece. Onde o terno é mais fundo, a palavra cresce. Onde a camisa é clara,
ela quase some.

Por isso ela funciona de dois jeitos. De longe, é o Emicida. De perto, é a
música inteira.
```

Frontmatter YAML + corpo em Markdown (parágrafos e `*itálico*` bastam).
**Sem esse arquivo, a obra não gera certificado** — e isso é o certo: obra sem
carta não deve virar página pela metade.

### 4.3 `site/src/data/certificates.json` — o calculado (gerado por `build_certificates.py`)

Uma entrada **por obra**, não por selo — todo selo da mesma obra compartilha.

```jsonc
{
  "emicida": {
    "title": "O GLORIOSO RETORNO",
    "subtitle": "EMICIDA · LEVANTA E ANDA",
    "carta": "<p>Esta arte não foi desenhada…</p><p>Por isso…</p>",
    "contagem": {
      "palavra": "levanta",
      "vezes": 357,
      "frases": 62,
      "voltas": 25.51,
      "letras": 40413,
      "palavras": 9516,
      "ranking": [
        { "palavra": "levanta", "vezes": 357 },
        { "palavra": "anda", "vezes": 357 }
        // … 10 no total
      ]
    },
    "art": {
      "full": "/art/emicida-full.webp",
      "detail": "/art/emicida-detail.webp"
    }
  }
}
```

---

## 5. Etapas de implementação

Ordem importa: 1→2→3 são independentes do site e destravam o resto.

### Etapa 1 — tirar o registro de dentro do `.gitignore` 🐞

**Bug atual.** `make_seal.py` escreve `projects/<slug>/output/selos/selos.csv`, e
`projects/*/output/*` está no `.gitignore:10`. O registro do que foi vendido
sumiria num clone limpo.

**Fazer:**

1. Em `scripts/make_seal.py`, trocar `ledger_add` / `ledger_codes` por leitura e
   escrita de `site/src/data/seals.json` (caminho: `ROOT / "site/src/data/seals.json"`).
2. Manter PNG e PDF em `projects/<slug>/output/selos/` — **isso está certo**:
   são reproduzíveis a partir do código + payload, mesma regra dos outros
   outputs.
3. A checagem de unicidade passa a varrer o JSON inteiro (todos os slugs), não
   só a pasta da obra. Hoje dois projetos diferentes podem sortear o mesmo
   código.
4. Escrever com `indent=2`, `ensure_ascii=False`, `sort_keys` nas chaves de cada
   objeto, e ordenar a lista — diff de git legível.
5. Apagar `projects/ouro-marrom/output/selos/` (o `7QK4M2` foi selo de teste).

**Aceite:** gerar dois selos de projetos diferentes; `git status` mostra
`site/src/data/seals.json` modificado; rodar de novo com o mesmo `--code` falha
com erro claro.

### Etapa 2 — domínio de verdade em `make_seal.py`

**Fazer:**

1. `DEFAULT_BASE_URL = "https://typo-jet.vercel.app"`.
2. Trocar `/S/` por `/CERTIFICADO/` em `build_payload()` (custa 0 módulos —
   medido).
3. Ler `SITE_URL` de `site/src/config.js` por regex
   (`/SITE_URL:\s*"([^"]*)"/`). Se estiver preenchido **e** diferente do
   `--base-url` efetivo, **avisar em stderr** — não falhar, não sobrescrever.
   O aviso de "CONFIG.SITE_URL vazio" some quando ele preencher.
4. Atualizar a docstring do módulo.

**Aceite:** `make_seal.py <obra>` imprime
`payload: HTTPS://TYPO-JET.VERCEL.APP/CERTIFICADO/XXXXXX`, o selo continua V4/33
módulos, e `pytest tests/test_seal.py` continua verde.

### Etapa 3 — `scripts/build_certificates.py`

O script que calcula a contagem. **Nenhuma alteração no motor.**

**Entradas:** `site/src/data/seals.json`, `site/src/data/works.json`,
`projects/<slug>/project.yaml`, `projects/<slug>/certificado.md`,
`projects/<slug>/text/*.txt`.
**Saída:** `site/src/data/certificates.json`.

**Algoritmo:**

1. Ler `seals.json`; juntar os slugs distintos (só gera pra obra que tem selo).
2. Pra cada slug:
   a. `cfg = RenderConfig.from_project(...)` — daí saem `text.text_path`,
      `text.mode`, `text.separator`, `text.regions`.
   b. Se `cfg.text.regions` não for vazio → **erro claro** citando a limitação
      da seção 3, e pula a obra.
   c. `linhas = text_source.read_lines(cfg.text.text_path)`.
   d. `volta`, `nao_espacos`, `voltas` pela fórmula da seção 3, usando
      `works.json[slug].glyphs`.
   e. Tokenizar `volta.split()`, normalizar (minúscula, sem acento via
      `unicodedata` NFD, tirar pontuação das pontas) e contar.
   f. `ranking` = 10 mais frequentes, desempate alfabético (determinismo).
      `palavra` do frontmatter vira o número-herói; se não estiver no texto,
      **erro claro**.
   g. Converter o corpo do `certificado.md` em HTML: parágrafos por linha em
      branco, `*itálico*` → `<em>`. **Escapar HTML antes.** Não instalar
      dependência de Markdown pra isso.
3. Escrever `certificates.json` (`indent=2`, `ensure_ascii=False`, chaves
   ordenadas).

**Aceite — teste objetivo em `tests/test_certificates.py`:**

```python
def test_contagem_bate_com_o_email_do_emicida():
    """O e-mail de entrega é gabarito: 357x levanta, 102x sonho, 77x somos."""
    c = contagem_de("emicida")
    assert c["frases"] == 62
    assert round(c["voltas"], 1) == 25.5
    assert c["letras"] == 40413
    for palavra, esperado in [("levanta", 357), ("anda", 357), ("vai", 357),
                              ("sonho", 102), ("quem", 102), ("sei", 102),
                              ("onde", 102), ("somos", 77), ("seguir", 77),
                              ("nossa", 77)]:
        assert vezes(c, palavra) == esperado
```

Mais: obra com `regions` levanta erro; obra sem `certificado.md` é pulada com
aviso; rodar duas vezes dá byte-a-byte o mesmo arquivo (determinismo).

### Etapa 4 — as cartas

Criar `projects/<slug>/certificado.md` pras obras que forem ganhar certificado.
O Gustavo avisa quais. **Rascunhe a partir do `blurb` do `works.json` e do campo
`notes` do `project.yaml`** (ele costuma ter o raciocínio conceitual inteiro) e
submeta pra revisão — ele aprova um "definitivo" e segue refinando.

Tom, tirado do e-mail: segunda pessoa, frases curtas, uma virada de chave no
fim ("De longe é o Emicida. De perto é a música inteira."). Nada de jargão do
motor.

### Etapa 5 — o template da página

**Criar `site/certificado/index.html`.** Espelha `site/admin/index.html`: página
de verdade numa pasta, entrando em `rollupOptions.input` do `vite.config.js`
como terceira entrada (`certificado`).

Estrutura (reusando os tokens de `src/styles/base.css` — não invente cor nem
fonte):

```
cabeçalho     marca (4 quadradinhos, um terracota) + "Certificado"
título        rótulo "Espécime único" · TÍTULO · subtítulo (artista · obra)
carta         Georgia serif, o texto de certificado.md
contagem      número-herói terracota + palavra + tabela do ranking
              rodapé: "N palavras · N letras desenhadas uma a uma"
imagem        art-full + art-detail (o zoom nas letras), lado a lado no desktop
autenticidade código do selo em mono, data de emissão, edição se houver
rodapé        marca invertida, igual ao e-mail
```

Marcadores pro plugin preencher, no espírito do `data-i18n`:

- `data-cert="chave"` — troca o conteúdo do elemento
- `<!--cert:head-->` — `<title>`, `og:*`, `noindex`, canonical

**`noindex` é obrigatório:** `<meta name="robots" content="noindex, nofollow" />`.

Mobile-first, como o resto do site.

### Etapa 6 — `site/build/certificates.js` (plugin Vite)

**Copie a estrutura de `site/build/i18n.js`** — ele já resolve exatamente este
problema (gerar N páginas estáticas a partir de um template no `writeBundle`).

```js
export default function certificatePages({ siteUrl = "" } = {}) {
  return {
    name: "omp:certificate-pages",
    enforce: "post",
    configureServer(server) { /* middleware: /certificado/<CODE>/ em dev */ },
    writeBundle(options) {
      // 1. ler dist/certificado/index.html (o template já processado pelo Vite)
      // 2. pra cada selo em seals.json:
      //      - achar a obra em certificates.json
      //      - preencher data-cert=* e <!--cert:head-->
      //      - escrever dist/certificado/<CODE>/index.html
      // 3. console.log(`[cert] N selos`)
    },
  };
}
```

**Dados vão INLINE no HTML**, não por `fetch`. Motivos: carrega instantâneo,
funciona sem JS, e a prévia do WhatsApp precisa das `og:` tags já no HTML — que
é metade da graça de mandar o link. Mesma filosofia do `i18n.js`
("o texto já no HTML").

**Falhe alto na build**, como o `i18n.js` faz com chave faltando: selo cujo slug
não está em `certificates.json` deve **quebrar a build**, não gerar página vazia.
Certificado publicado pela metade é pior que build vermelha.

Registrar em `vite.config.js` depois do `i18nPages`.

**Aceite:** `npm run build` gera `dist/certificado/<CODE>/index.html` pra cada
selo; abrir a URL da Vercel depois do deploy mostra a página; escanear o selo
impresso abre ela.

### Etapa 7 — documentação

- `CLAUDE.md`: seção do selo + certificado, no tom das outras (o porquê, não só
  o quê). Registrar a fórmula da contagem e o `core_ratio` medido.
- `site/README.md`: a pasta `certificado/` na árvore, o passo novo no fluxo de
  publicação, e que `seals.json` **é acrescentado por script mas versionado** —
  ao contrário de `works.json`, que é regerado inteiro.

---

## 6. Fluxo final

```bash
.venv/Scripts/python.exe scripts/render.py <obra>
.venv/Scripts/python.exe scripts/build_site_assets.py      # works.json + webp
# escrever projects/<obra>/certificado.md  (uma vez por obra)
.venv/Scripts/python.exe scripts/make_seal.py <obra> --edition 3/5
.venv/Scripts/python.exe scripts/build_certificates.py
git add -A && git commit -m "selo <CODE> — <obra>" && git push   # deploy Vercel
```

Cada selo emitido vira um commit. **O histórico do git é o livro de registro** —
com data, ordem e autoria, sem construir nada pra isso.

---

## 7. Armadilhas

- **Não toque no motor.** Rode `TYPO_PARITY=1 pytest -q` antes de dar qualquer
  etapa como pronta. A contagem é calculada FORA do render, a partir de
  `works.json`; não adicione contador em `typography.py`.
- **`payload` é imutável.** Uma vez em `seals.json`, nunca recalcule — está
  impresso em papel colado numa obra vendida.
- **`glyphs` vem do `works.json`**, que é gerado por `build_site_assets.py` a
  partir do export de 150 dpi. Se a obra for re-renderizada com parâmetros
  diferentes, `glyphs` muda e a contagem muda junto. É o comportamento certo,
  mas o certificado de um selo já impresso passa a mostrar número diferente do
  que mostrava. Se isso incomodar, congele a contagem dentro do `seals.json` no
  momento da emissão — decisão do Gustavo, não assuma.
- **Modo do texto.** A fórmula assume `text.mode: "phrases"` (o default). Em
  `words` ou `chars` o separador muda e `volta` tem que ser montada com
  `text_source.build_stream` em vez de `"   ".join`. Trate os três.
- **`.vercel.app` não é domínio próprio.** Se um dia houver domínio de verdade,
  os selos antigos apontam pro antigo. O Gustavo assumiu esse risco
  explicitamente e reemite se precisar.
- **Não instale dependência nova sem necessidade.** O Markdown da carta é
  parágrafo + itálico; `re.sub` resolve. O site é vanilla JS de propósito.
