---
description: Cria a estrutura de um projeto novo em projects/<nome>
argument-hint: <nome>
---

Crie um projeto novo chamado `$ARGUMENTS`.

1. Rode o scaffold:

```bash
.venv/Scripts/python.exe scripts/new_project.py $ARGUMENTS
```

(no macOS/Linux: `.venv/bin/python scripts/new_project.py $ARGUMENTS`)

2. Mostre ao usuário o que falta preencher:
   - a imagem de referência em `projects/$ARGUMENTS/refs/`
   - a letra/trecho em `projects/$ARGUMENTS/text/$ARGUMENTS.txt`
     (uma frase por linha, `#` é comentário)
   - `source.image` e `source.crop` em `projects/$ARGUMENTS/project.yaml`

3. Se o usuário já indicou qual imagem e qual texto usar, preencha o
   `project.yaml` por ele e siga o guia de afinação em
   `skills/typographic-poster/SKILL.md` para escolher crop, `lum_threshold` e
   a faixa da paisagem. Use `Ver crop` / `Ver máscara` (ou os helpers
   `app.ui.crop_overlay` / `app.ui.mask_overlay`) para conferir antes de
   renderizar em alta.

Não invente valores de `style_overrides` sem antes olhar a máscara.
