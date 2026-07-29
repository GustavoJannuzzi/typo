---
description: Render headless de um projeto (PNG + PDF em tamanho de impressão)
argument-hint: <projeto>
---

Renderize o projeto `$ARGUMENTS` em alta resolução:

```bash
.venv/Scripts/python.exe scripts/render.py projects/$ARGUMENTS/project.yaml
```

(no macOS/Linux: `.venv/bin/python scripts/render.py projects/$ARGUMENTS/project.yaml`)

O comando imprime o resumo do render, o caminho do PNG e o do PDF **com o
mediabox em cm** — confira que o tamanho físico bate com o esperado antes de
mandar imprimir.

Dicas:
- Para iterar rápido, use `--dpi 60` (ou `--preview`, que só gera PNG pequeno).
- Os arquivos vão para `projects/$ARGUMENTS/output/`.
- Export a 150 dpi de uma página 113 × 111 cm leva ~15 s e gera uma imagem de
  44 MP. Não rode isso em loop.

Se o projeto não existir, liste os disponíveis com
`.venv/Scripts/python.exe -c "from typo.project import list_projects; print(list_projects())"`.
