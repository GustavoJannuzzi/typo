-- Tarefas de mídia social — GERADO por scripts/publish_media.py
-- 2026-07-31T19:21:06+00:00 · 4 tarefas · 43 anexos
--
-- Antes de rodar isto, rode a migration 0001_assignee_attachments.sql uma vez.
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
- [chapa-paleta.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-paleta.png) — REFERÊNCIA (não postar): paleta e escala tipográfica.', 'geovana', '[{"name": "avatar-marca.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-marca-invertido.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-invertido.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-invertido-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-marca-tipografada.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-tipografada.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-marca-tipografada-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-letra.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-letra-invertido.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-invertido.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-invertido-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "avatar-letra-tipografada.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-tipografada.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/avatar-letra-tipografada-thumb.webp", "group": "avatar · foto de perfil"}, {"name": "destaque-colecao.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-colecao.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-colecao-thumb.webp", "group": "capas de destaque"}, {"name": "destaque-processo.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-processo.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-processo-thumb.webp", "group": "capas de destaque"}, {"name": "destaque-encomenda.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-encomenda.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-encomenda-thumb.webp", "group": "capas de destaque"}, {"name": "destaque-sobre.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-sobre.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-sobre-thumb.webp", "group": "capas de destaque"}, {"name": "destaque-precos.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-precos.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/destaque-precos-thumb.webp", "group": "capas de destaque"}, {"name": "lockup-horizontal.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal-thumb.webp", "group": "assinaturas"}, {"name": "lockup-horizontal-invertido.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal-invertido.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-horizontal-invertido-thumb.webp", "group": "assinaturas"}, {"name": "lockup-empilhado.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado-thumb.webp", "group": "assinaturas"}, {"name": "lockup-empilhado-invertido.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado-invertido.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/lockup-empilhado-invertido-thumb.webp", "group": "assinaturas"}, {"name": "chapa-avatares.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-avatares.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-avatares-thumb.webp", "group": "provas de contato · referência"}, {"name": "chapa-lockups.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-lockups.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-lockups-thumb.webp", "group": "provas de contato · referência"}, {"name": "chapa-destaques.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-destaques.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-destaques-thumb.webp", "group": "provas de contato · referência"}, {"name": "chapa-paleta.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-paleta.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/marca/chapa-paleta-thumb.webp", "group": "provas de contato · referência"}]'::jsonb, 1785525666661),
  ('50ffc65e-cdd3-5e0c-8632-e34e0a62063f'::uuid, 'Carrossel — GAROTA DE IPANEMA', 'social', 'todo', 'media', '## GAROTA DE IPANEMA

TOM JOBIM · VINICIUS DE MORAES · 1962

O carrossel vai **de longe pra perto** — é ele que conta que a arte é feita de
texto, coisa que uma foto só nunca mostra no feed. Poste **nesta ordem**, os
arquivos já estão numerados:

1. `01-arte.png` — a peça inteira, com o título
2. `02-malha.png` — 2,6× mais perto, a malha começando a virar letra
3. `03-macro.png` — o macro, onde se lê a palavra
4. `04-ficha.png` — a ficha técnica

- [ ] postar o carrossel no feed (4 imagens, 4:5)
- [ ] subir os quatro no story também (9:16, já cortados)
- [ ] fixar a legenda com o trecho do texto que aparece na ficha

**Ficha:** 101 × 112 cm · 23.447 glifos · impressão em 150 dpi.

> A carta 3 é a que segura o post. Se for cortar alguma, corte a 2.

## Arquivos

**feed 4:5 · carrossel**

- [01-arte.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/01-arte.png) — A peça inteira, com o título. É a carta que para o dedo.
- [02-malha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/02-malha.png) — 2,6× mais perto. A malha começa a virar letra.
- [03-macro.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/03-macro.png) — 1:1 com o arquivo de impressão — aqui se lê a palavra. É a carta que segura o post.
- [04-ficha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/04-ficha.png) — Ficha técnica: medida, glifos, fonte e o trecho do texto.

**story 9:16**

- [01-arte.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/01-arte.png) — A peça inteira, com o título. É a carta que para o dedo.
- [02-malha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/02-malha.png) — 2,6× mais perto. A malha começa a virar letra.
- [03-macro.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/03-macro.png) — 1:1 com o arquivo de impressão — aqui se lê a palavra. É a carta que segura o post.
- [04-ficha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/04-ficha.png) — Ficha técnica: medida, glifos, fonte e o trecho do texto.', 'geovana', '[{"name": "01-arte.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/01-arte.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/01-arte-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "02-malha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/02-malha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/02-malha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "03-macro.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/03-macro.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/03-macro-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "04-ficha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/04-ficha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/feed/04-ficha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "01-arte.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/01-arte.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/01-arte-thumb.webp", "group": "story 9:16"}, {"name": "02-malha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/02-malha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/02-malha-thumb.webp", "group": "story 9:16"}, {"name": "03-macro.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/03-macro.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/03-macro-thumb.webp", "group": "story 9:16"}, {"name": "04-ficha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/04-ficha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/garota-de-ipanema/story/04-ficha-thumb.webp", "group": "story 9:16"}]'::jsonb, 1785525666662),
  ('365d3b08-82ac-5102-a13d-0ff8dc55ea51'::uuid, 'Carrossel — NOSSA SENHORA', 'social', 'todo', 'media', '## NOSSA SENHORA

AVE MARIA · CHEIA DE GRAÇA

O carrossel vai **de longe pra perto** — é ele que conta que a arte é feita de
texto, coisa que uma foto só nunca mostra no feed. Poste **nesta ordem**, os
arquivos já estão numerados:

1. `01-arte.png` — a peça inteira, com o título
2. `02-malha.png` — 2,6× mais perto, a malha começando a virar letra
3. `03-macro.png` — o macro, onde se lê a palavra
4. `04-ficha.png` — a ficha técnica

- [ ] postar o carrossel no feed (4 imagens, 4:5)
- [ ] subir os quatro no story também (9:16, já cortados)
- [ ] fixar a legenda com o trecho do texto que aparece na ficha

**Ficha:** 73 × 112 cm · 26.668 glifos · impressão em 150 dpi.

> A carta 3 é a que segura o post. Se for cortar alguma, corte a 2.

## Arquivos

**feed 4:5 · carrossel**

- [01-arte.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/01-arte.png) — A peça inteira, com o título. É a carta que para o dedo.
- [02-malha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/02-malha.png) — 2,6× mais perto. A malha começa a virar letra.
- [03-macro.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/03-macro.png) — 1:1 com o arquivo de impressão — aqui se lê a palavra. É a carta que segura o post.
- [04-ficha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/04-ficha.png) — Ficha técnica: medida, glifos, fonte e o trecho do texto.

**story 9:16**

- [01-arte.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/01-arte.png) — A peça inteira, com o título. É a carta que para o dedo.
- [02-malha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/02-malha.png) — 2,6× mais perto. A malha começa a virar letra.
- [03-macro.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/03-macro.png) — 1:1 com o arquivo de impressão — aqui se lê a palavra. É a carta que segura o post.
- [04-ficha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/04-ficha.png) — Ficha técnica: medida, glifos, fonte e o trecho do texto.', 'geovana', '[{"name": "01-arte.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/01-arte.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/01-arte-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "02-malha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/02-malha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/02-malha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "03-macro.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/03-macro.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/03-macro-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "04-ficha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/04-ficha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/feed/04-ficha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "01-arte.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/01-arte.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/01-arte-thumb.webp", "group": "story 9:16"}, {"name": "02-malha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/02-malha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/02-malha-thumb.webp", "group": "story 9:16"}, {"name": "03-macro.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/03-macro.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/03-macro-thumb.webp", "group": "story 9:16"}, {"name": "04-ficha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/04-ficha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/nossa-senhora/story/04-ficha-thumb.webp", "group": "story 9:16"}]'::jsonb, 1785525666663),
  ('87aa92a2-30ab-5c07-bca0-af00a4fc425b'::uuid, 'Carrossel — OURO MARROM', 'social', 'todo', 'media', '## OURO MARROM

JOTA.PÊ · SE O MEU PEITO FOSSE O MUNDO

O carrossel vai **de longe pra perto** — é ele que conta que a arte é feita de
texto, coisa que uma foto só nunca mostra no feed. Poste **nesta ordem**, os
arquivos já estão numerados:

1. `01-arte.png` — a peça inteira, com o título
2. `02-malha.png` — 2,6× mais perto, a malha começando a virar letra
3. `03-macro.png` — o macro, onde se lê a palavra
4. `04-ficha.png` — a ficha técnica

- [ ] postar o carrossel no feed (4 imagens, 4:5)
- [ ] subir os quatro no story também (9:16, já cortados)
- [ ] fixar a legenda com o trecho do texto que aparece na ficha

**Ficha:** 96 × 112 cm · 35.880 glifos · impressão em 150 dpi.

> A carta 3 é a que segura o post. Se for cortar alguma, corte a 2.

## Arquivos

**feed 4:5 · carrossel**

- [01-arte.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/01-arte.png) — A peça inteira, com o título. É a carta que para o dedo.
- [02-malha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/02-malha.png) — 2,6× mais perto. A malha começa a virar letra.
- [03-macro.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/03-macro.png) — 1:1 com o arquivo de impressão — aqui se lê a palavra. É a carta que segura o post.
- [04-ficha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/04-ficha.png) — Ficha técnica: medida, glifos, fonte e o trecho do texto.

**story 9:16**

- [01-arte.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/01-arte.png) — A peça inteira, com o título. É a carta que para o dedo.
- [02-malha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/02-malha.png) — 2,6× mais perto. A malha começa a virar letra.
- [03-macro.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/03-macro.png) — 1:1 com o arquivo de impressão — aqui se lê a palavra. É a carta que segura o post.
- [04-ficha.png](https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/04-ficha.png) — Ficha técnica: medida, glifos, fonte e o trecho do texto.', 'geovana', '[{"name": "01-arte.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/01-arte.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/01-arte-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "02-malha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/02-malha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/02-malha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "03-macro.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/03-macro.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/03-macro-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "04-ficha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/04-ficha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/feed/04-ficha-thumb.webp", "group": "feed 4:5 · carrossel"}, {"name": "01-arte.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/01-arte.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/01-arte-thumb.webp", "group": "story 9:16"}, {"name": "02-malha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/02-malha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/02-malha-thumb.webp", "group": "story 9:16"}, {"name": "03-macro.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/03-macro.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/03-macro-thumb.webp", "group": "story 9:16"}, {"name": "04-ficha.png", "url": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/04-ficha.png", "thumb": "https://raw.githubusercontent.com/GustavoJannuzzi/typo/main/site/public/midia/ouro-marrom/story/04-ficha-thumb.webp", "group": "story 9:16"}]'::jsonb, 1785525666664)
on conflict (id) do update set
  title       = excluded.title,
  description = excluded.description,
  assignee    = excluded.assignee,
  attachments = excluded.attachments,
  updated_at  = now();
