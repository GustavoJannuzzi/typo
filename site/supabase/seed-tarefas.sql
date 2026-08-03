-- Tarefas de mídia social — GERADO por scripts/publish_media.py
-- 2026-08-03T15:22:02+00:00 · 4 tarefas · 52 anexos
--
-- Antes de rodar isto, rode as migrations de site/supabase/migrations/ na
-- ordem, uma vez cada: 0001 (assignee + attachments) e 0002 (position bigint).
-- Sem a 0002 este arquivo falha com `22003: integer out of range`, porque
-- `position` abaixo é um timestamp em ms e não cabe num integer.
--
-- Cole no SQL Editor do Supabase e execute. Os ids são derivados do slug
-- (uuid v5), então rodar de novo ATUALIZA as mesmas tarefas em vez de criar
-- cópias — o `on conflict` embaixo cuida disso. A coluna `position` é a única
-- que fica de fora do update: se alguém já tiver arrastado o cartão pra outro
-- lugar do quadro, regerar a mídia não pode jogar ele de volta pro fim.

insert into public.tasks
  (id, title, type, status, priority, description, assignee, attachments, position)
values
  ('8a9dd7c2-4c7c-5ad5-832a-5cf7af518fe4'::uuid, 'Perfil no Instagram — avatar, destaques e assinaturas', 'social', 'todo', 'alta', '## Identidade do perfil

Tudo aqui sai de `site/src/styles/base.css` — mesma paleta e mesmas fontes do
site, então o perfil e a landing são a mesma marca.

- [ ] subir o avatar (ver qual variante abaixo)
- [ ] criar os cinco destaques e subir as capas
- [ ] preencher a bio

**Avatar.** A recomendação é `avatar-marca.png` — são os quatro quadradinhos do
rodapé do pôster, que quem já tem a peça reconhece. Todas as variantes foram
provadas em **110 px circular**, que é o tamanho real no feed: é o que está na
prova de contato `chapa-avatares.png`.

`avatar-letra-tipografada.png` é a mais bonita de perto e a pior de longe — com
110 px a textura de texto vira cinza chapado. Use em capa e camiseta, não como
foto de perfil.

**Destaques.** Os campos alternam papel, tinta e terracota de propósito: em
fileira, cinco bolinhas iguais somem umas nas outras.

**Assinaturas.** `lockup-horizontal` pra faixa e e-mail, `lockup-empilhado` pra
espaço quadrado. As versões invertidas são pra fundo escuro.

## Arquivos

**avatar · foto de perfil**

- [avatar-marca.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca.png) — RECOMENDADO pra foto de perfil. Os quatro quadradinhos do rodapé do pôster, na grade 2×2.
- [avatar-marca-invertido.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-invertido.png) — A mesma marca em campo de tinta. Segura melhor contra fundo claro na lista de stories.
- [avatar-marca-tipografada.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-tipografada.png) — Os três quadrados de tinta preenchidos com macro de obra real. Degrada bem: com 110 px os três viram cinza juntos.
- [avatar-letra.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra.png) — Um O em corpo de selo, com o quadradinho de destaque no vazio.
- [avatar-letra-invertido.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-invertido.png) — A mesma, em campo de tinta. Vira um alvo — a que mais chama atenção numa lista.
- [avatar-letra-tipografada.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-tipografada.png) — USO GRANDE (capa, camiseta). Como foto de perfil não serve: com 110 px a textura de texto vira cinza chapado.

**capas de destaque**

- [destaque-colecao.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-colecao.png) — Capa do destaque “Coleção”.
- [destaque-processo.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-processo.png) — Capa do destaque “Processo”.
- [destaque-encomenda.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-encomenda.png) — Capa do destaque “Encomenda”.
- [destaque-sobre.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-sobre.png) — Capa do destaque “Sobre”.
- [destaque-precos.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-precos.png) — Capa do destaque “Preços”.

**assinaturas**

- [lockup-horizontal.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal.png) — Assinatura deitada — faixa, banner, rodapé de e-mail.
- [lockup-horizontal-invertido.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal-invertido.png) — A deitada, para fundo escuro.
- [lockup-empilhado.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado.png) — Assinatura quadrada, para espaço sem largura.
- [lockup-empilhado-invertido.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado-invertido.png) — A quadrada, para fundo escuro.

**provas de contato · referência**

- [chapa-avatares.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-avatares.png) — REFERÊNCIA (não postar): cada avatar em 110 px circular, que é o tamanho real no feed.
- [chapa-lockups.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-lockups.png) — REFERÊNCIA (não postar): as quatro assinaturas lado a lado.
- [chapa-destaques.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-destaques.png) — REFERÊNCIA (não postar): as cinco capas em fileira.
- [chapa-paleta.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-paleta.png) — REFERÊNCIA (não postar): paleta e escala tipográfica.', 'geovana', '[{"name": "avatar-marca.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-marca-invertido.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-invertido.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-invertido-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-marca-tipografada.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-tipografada.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-tipografada-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-letra.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-letra-invertido.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-invertido.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-invertido-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-letra-tipografada.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-tipografada.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-tipografada-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "destaque-colecao.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-colecao.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-colecao-thumb.webp", "group": "capas de destaque"}, {"name": "destaque-processo.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-processo.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-processo-thumb.webp", "group": "capas de destaque"}, {"name": "destaque-encomenda.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-encomenda.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-encomenda-thumb.webp", "group": "capas de destaque"}, {"name": "destaque-sobre.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-sobre.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-sobre-thumb.webp", "group": "capas de destaque"}, {"name": "destaque-precos.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-precos.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-precos-thumb.webp", "group": "capas de destaque"}, {"name": "lockup-horizontal.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal-thumb.webp", "group": "assinaturas"}, {"name": "lockup-horizontal-invertido.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal-invertido.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal-invertido-thumb.webp", "group": "assinaturas"}, {"name": "lockup-empilhado.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado-thumb.webp", "group": "assinaturas"}, {"name": "lockup-empilhado-invertido.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado-invertido.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado-invertido-thumb.webp", "group": "assinaturas"}, {"name": "chapa-avatares.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-avatares.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-avatares-thumb.webp", "group": "provas de contato · referência"}, {"name": "chapa-lockups.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-lockups.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-lockups-thumb.webp", "group": "provas de contato · referência"}, {"name": "chapa-destaques.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-destaques.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-destaques-thumb.webp", "group": "provas de contato · referência"}, {"name": "chapa-paleta.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-paleta.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-paleta-thumb.webp", "group": "provas de contato · referência"}]'::jsonb, 1785770522581),
  ('e4f7cbf6-556d-57b0-85c9-2b79f70b0436'::uuid, 'Carrossel — EMICIDA', 'social', 'todo', 'media', '## O GLORIOSO RETORNO

EMICIDA · LEVANTA E ANDA

O carrossel vai **de longe pra perto** — é ele que conta que a arte é feita de
texto, coisa que uma foto só nunca mostra no feed. Poste **nesta ordem**, os
arquivos já estão numerados:

1. `01-arte.png` — a peça inteira, com o título
2. `02-malha.png` — 2,6× mais perto, a malha começando a virar letra
3. `03-macro.png` — o macro, onde se lê a palavra
4. `04-ficha.png` — a ficha técnica

- [ ] postar o carrossel no feed (4 imagens, 4:5)
- [ ] subir `story.png` no story (é **uma** imagem só)
- [ ] subir o vídeo em reels e story
- [ ] fixar a legenda com o trecho do texto que aparece na ficha

**Ficha:** 71 × 112 cm · 40.413 glifos · impressão em 150 dpi.

> A carta 3 é a que segura o post. Se for cortar alguma, corte a 2.

**O vídeo** tem 30 s e é o argumento da peça em movimento: a frase
vira malha, a malha vira retrato, e o retrato volta a virar palavra
contada. Serve pra reels e pra story.

**As avulsas** não são peça fechada — são matéria-prima. O título sai
em PNG com fundo transparente e os `malha-*.png` são recortes 1:1 do
arquivo de impressão, sem placa e sem moldura. É o material pra montar
uma arte à mão sem ter que recortar da carta pronta.

## Arquivos

**feed 4:5 · carrossel**

- [01-arte.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/01-arte.png) — A peça inteira, com o título. É a carta que para o dedo.
- [02-malha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/02-malha.png) — 2,6× mais perto. A malha começa a virar letra.
- [03-macro.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/03-macro.png) — 1:1 com o arquivo de impressão — aqui se lê a palavra. É a carta que segura o post.
- [04-ficha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/04-ficha.png) — Ficha técnica: medida, glifos, fonte e o trecho do texto.

**story 9:16**

- [story.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/story/story.png) — O story inteiro numa imagem: o macro sangrando no fundo e a peça inteira na placa de papel. No story não dá pra passar o dedo pra próxima, então o mergulho cabe numa tela.

**vídeo 9:16**

- [o-glorioso-retorno-30s.mp4](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/video/o-glorioso-retorno-30s.mp4) — Vídeo vertical 9:16 — serve pra reels e pra story.

**avulsas · pra montar à mão**

- [malha-01.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/malha-01.png) — Recorte 1:1 da malha, cru — sem placa e sem moldura.
- [malha-02.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/malha-02.png) — Outro recorte 1:1, de outra região da peça.
- [malha-03.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/malha-03.png) — Outro recorte 1:1, de outra região da peça.
- [peca.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/peca.png) — A peça inteira, crua — sem carta, sem moldura e sem título.
- [titulo.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/titulo.png) — O título isolado, PNG com FUNDO TRANSPARENTE. Pra montar por cima do que você quiser.', 'geovana', '[{"name": "01-arte.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/01-arte.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/01-arte-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "02-malha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/02-malha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/02-malha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "03-macro.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/03-macro.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/03-macro-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "04-ficha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/04-ficha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/feed/04-ficha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "story.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/story/story.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/story/story-thumb.webp", "group": "story 9:16"}, {"name": "o-glorioso-retorno-30s.mp4", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/video/o-glorioso-retorno-30s.mp4", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/video/o-glorioso-retorno-30s-thumb.webp", "group": "vídeo 9:16"}, {"name": "malha-01.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/malha-01.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/malha-01-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "malha-02.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/malha-02.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/malha-02-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "malha-03.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/malha-03.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/malha-03-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "peca.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/peca.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/peca-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "titulo.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/titulo.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/emicida/avulsas/titulo-thumb.webp", "group": "avulsas · pra montar à mão"}]'::jsonb, 1785770522582),
  ('afe68fff-8d08-5c57-bcce-3c369f8659f6'::uuid, 'Carrossel — DEBRET ANTROPOFAGIA', 'social', 'todo', 'media', '## TUPI OR NOT TUPI

OSWALD DE ANDRADE · MANIFESTO ANTROPÓFAGO · 1928

O carrossel vai **de longe pra perto** — é ele que conta que a arte é feita de
texto, coisa que uma foto só nunca mostra no feed. Poste **nesta ordem**, os
arquivos já estão numerados:

1. `01-arte.png` — a peça inteira, com o título
2. `02-malha.png` — 2,6× mais perto, a malha começando a virar letra
3. `03-macro.png` — o macro, onde se lê a palavra
4. `04-ficha.png` — a ficha técnica

- [ ] postar o carrossel no feed (4 imagens, 4:5)
- [ ] subir `story.png` no story (é **uma** imagem só)
- [ ] subir o vídeo em reels e story
- [ ] fixar a legenda com o trecho do texto que aparece na ficha

**Ficha:** 100 × 112 cm · 188.125 glifos · impressão em 150 dpi.

> A carta 3 é a que segura o post. Se for cortar alguma, corte a 2.

**O vídeo** tem 30 s e é o argumento da peça em movimento: a frase
vira malha, a malha vira retrato, e o retrato volta a virar palavra
contada. Serve pra reels e pra story.

**As avulsas** não são peça fechada — são matéria-prima. O título sai
em PNG com fundo transparente e os `malha-*.png` são recortes 1:1 do
arquivo de impressão, sem placa e sem moldura. É o material pra montar
uma arte à mão sem ter que recortar da carta pronta.

## Arquivos

**feed 4:5 · carrossel**

- [01-arte.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/01-arte.png) — A peça inteira, com o título. É a carta que para o dedo.
- [02-malha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/02-malha.png) — 2,6× mais perto. A malha começa a virar letra.
- [03-macro.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/03-macro.png) — 1:1 com o arquivo de impressão — aqui se lê a palavra. É a carta que segura o post.
- [04-ficha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/04-ficha.png) — Ficha técnica: medida, glifos, fonte e o trecho do texto.

**story 9:16**

- [story.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/story/story.png) — O story inteiro numa imagem: o macro sangrando no fundo e a peça inteira na placa de papel. No story não dá pra passar o dedo pra próxima, então o mergulho cabe numa tela.

**vídeo 9:16**

- [tupi-or-not-tupi-20s.mp4](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/video/tupi-or-not-tupi-20s.mp4) — Vídeo vertical 9:16 — serve pra reels e pra story.

**avulsas · pra montar à mão**

- [malha-01.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/malha-01.png) — Recorte 1:1 da malha, cru — sem placa e sem moldura.
- [malha-02.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/malha-02.png) — Outro recorte 1:1, de outra região da peça.
- [malha-03.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/malha-03.png) — Outro recorte 1:1, de outra região da peça.
- [peca.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/peca.png) — A peça inteira, crua — sem carta, sem moldura e sem título.
- [titulo.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/titulo.png) — O título isolado, PNG com FUNDO TRANSPARENTE. Pra montar por cima do que você quiser.', 'geovana', '[{"name": "01-arte.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/01-arte.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/01-arte-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "02-malha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/02-malha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/02-malha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "03-macro.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/03-macro.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/03-macro-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "04-ficha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/04-ficha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/feed/04-ficha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "story.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/story/story.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/story/story-thumb.webp", "group": "story 9:16"}, {"name": "tupi-or-not-tupi-20s.mp4", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/video/tupi-or-not-tupi-20s.mp4", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/video/tupi-or-not-tupi-20s-thumb.webp", "group": "vídeo 9:16"}, {"name": "malha-01.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/malha-01.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/malha-01-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "malha-02.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/malha-02.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/malha-02-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "malha-03.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/malha-03.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/malha-03-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "peca.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/peca.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/peca-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "titulo.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/titulo.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/debret-antropofagia/avulsas/titulo-thumb.webp", "group": "avulsas · pra montar à mão"}]'::jsonb, 1785770522583),
  ('7a70fe58-350e-5c0d-a4d4-ae030cd2dfaa'::uuid, 'Carrossel — MAGALENHA', 'social', 'todo', 'media', '## MAGALENHA



O carrossel vai **de longe pra perto** — é ele que conta que a arte é feita de
texto, coisa que uma foto só nunca mostra no feed. Poste **nesta ordem**, os
arquivos já estão numerados:

1. `01-arte.png` — a peça inteira, com o título
2. `02-malha.png` — 2,6× mais perto, a malha começando a virar letra
3. `03-macro.png` — o macro, onde se lê a palavra
4. `04-ficha.png` — a ficha técnica

- [ ] postar o carrossel no feed (4 imagens, 4:5)
- [ ] subir `story.png` no story (é **uma** imagem só)
- [ ] subir o vídeo em reels e story
- [ ] fixar a legenda com o trecho do texto que aparece na ficha

**Ficha:** — · — glifos · impressão em 150 dpi.

> A carta 3 é a que segura o post. Se for cortar alguma, corte a 2.

**O vídeo** tem 30 s e é o argumento da peça em movimento: a frase
vira malha, a malha vira retrato, e o retrato volta a virar palavra
contada. Serve pra reels e pra story.

**As avulsas** não são peça fechada — são matéria-prima. O título sai
em PNG com fundo transparente e os `malha-*.png` são recortes 1:1 do
arquivo de impressão, sem placa e sem moldura. É o material pra montar
uma arte à mão sem ter que recortar da carta pronta.

## Arquivos

**feed 4:5 · carrossel**

- [01-arte.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/01-arte.png) — A peça inteira, com o título. É a carta que para o dedo.
- [02-malha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/02-malha.png) — 2,6× mais perto. A malha começa a virar letra.
- [03-macro.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/03-macro.png) — 1:1 com o arquivo de impressão — aqui se lê a palavra. É a carta que segura o post.
- [04-ficha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/04-ficha.png) — Ficha técnica: medida, glifos, fonte e o trecho do texto.

**story 9:16**

- [story.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/story/story.png) — O story inteiro numa imagem: o macro sangrando no fundo e a peça inteira na placa de papel. No story não dá pra passar o dedo pra próxima, então o mergulho cabe numa tela.

**vídeo 9:16**

- [magalenha-20s.mp4](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/video/magalenha-20s.mp4) — Vídeo vertical 9:16 — serve pra reels e pra story.

**avulsas · pra montar à mão**

- [malha-01.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/malha-01.png) — Recorte 1:1 da malha, cru — sem placa e sem moldura.
- [malha-02.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/malha-02.png) — Outro recorte 1:1, de outra região da peça.
- [malha-03.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/malha-03.png) — Outro recorte 1:1, de outra região da peça.
- [peca.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/peca.png) — A peça inteira, crua — sem carta, sem moldura e sem título.
- [titulo.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/titulo.png) — O título isolado, PNG com FUNDO TRANSPARENTE. Pra montar por cima do que você quiser.', 'geovana', '[{"name": "01-arte.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/01-arte.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/01-arte-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "02-malha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/02-malha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/02-malha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "03-macro.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/03-macro.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/03-macro-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "04-ficha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/04-ficha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/feed/04-ficha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "story.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/story/story.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/story/story-thumb.webp", "group": "story 9:16"}, {"name": "magalenha-20s.mp4", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/video/magalenha-20s.mp4", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/video/magalenha-20s-thumb.webp", "group": "vídeo 9:16"}, {"name": "malha-01.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/malha-01.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/malha-01-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "malha-02.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/malha-02.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/malha-02-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "malha-03.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/malha-03.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/malha-03-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "peca.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/peca.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/peca-thumb.webp", "group": "avulsas · pra montar à mão"}, {"name": "titulo.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/titulo.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/magalenha/avulsas/titulo-thumb.webp", "group": "avulsas · pra montar à mão"}]'::jsonb, 1785770522584)
on conflict (id) do update set
  title       = excluded.title,
  description = excluded.description,
  assignee    = excluded.assignee,
  attachments = excluded.attachments,
  updated_at  = now();
