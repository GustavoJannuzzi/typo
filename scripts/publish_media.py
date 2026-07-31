#!/usr/bin/env python3
"""Publica a mídia social no site e gera as tarefas do /admin.

    python scripts/publish_media.py
    python scripts/publish_media.py --responsavel geovana --sem-quantizar

Faz duas coisas:

1. Copia `social/` para `site/public/midia/`, que é servido pelo próprio deploy
   do site. Assim cada arquivo vira uma URL simples
   (`https://<dominio>/midia/ouro-marrom/feed/03-macro.png`) que qualquer pessoa
   abre, copia e baixa — sem login, sem bucket, sem infraestrutura nova.
2. Escreve `site/supabase/seed-tarefas.sql`: uma tarefa por obra, mais uma da
   identidade do perfil, cada uma com a lista de anexos e o responsável.

**Este script não escreve no banco.** A RLS de `public.tasks` só aceita sessão
autenticada, e a chave publicável do bundle não lê nem escreve nada. O caminho
é colar o `.sql` no SQL Editor do Supabase, onde o Gustavo já entra como dono
do projeto — nenhuma credencial passa por aqui.

## Peso

As cartas somam ~27 MB em PNG de 24 bits. Elas usam poucas cores de tinta
(papel, tinta, terracota e o antialias entre elas), então a paleta de 256 cores
é medida, não chutada: no macro do `ouro-marrom` o erro é **zero** — a imagem
já cabia em 256 cores. Nas cartas com o accent em degradê o erro médio fica em
0,1 de 255, em 0,1% dos pixels. O peso cai ~65%, o que importa porque isto vai
pro git e pro deploy. `--sem-quantizar` desliga, se algum dia a arte passar a
usar cor contínua de verdade.

As miniaturas de 320 px existem porque a ficha da tarefa abre com até oito
imagens: sem elas o painel puxaria megabytes só pra desenhar oito quadradinhos.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import social_kit as kit  # noqa: E402

ROOT = kit.ROOT
SOCIAL = ROOT / "social"
DESTINO = ROOT / "site" / "public" / "midia"
SEED = ROOT / "site" / "supabase" / "seed-tarefas.sql"

#: prefixo da URL pública. O padrão é relativo, que é o que funciona depois do
#: deploy (o Vite serve `site/public/` na raiz). Enquanto o site não está no ar,
#: `--base-url` aponta pro raw do GitHub e os links passam a funcionar hoje:
#:
#:   --base-url https://raw.githubusercontent.com/USUARIO/REPO/main/site/public/midia
URL_BASE = "/midia"

#: o que cada arquivo é, em uma linha. A chave é o nome do arquivo; para as
#: cartas do carrossel, o nome se repete entre feed/ e story/, e é o mesmo
#: conteúdo em corte diferente — então uma entrada serve pros dois.
DESCRICOES = {
    # carrossel
    "01-arte.png": "A peça inteira, com o título. É a carta que para o dedo.",
    "02-malha.png": "2,6× mais perto. A malha começa a virar letra.",
    "03-macro.png": "1:1 com o arquivo de impressão — aqui se lê a palavra. "
                    "É a carta que segura o post.",
    "04-ficha.png": "Ficha técnica: medida, glifos, fonte e o trecho do texto.",
    # avatares
    "avatar-marca.png": "RECOMENDADO pra foto de perfil. Os quatro quadradinhos "
                        "do rodapé do pôster, na grade 2×2.",
    "avatar-marca-invertido.png": "A mesma marca em campo de tinta. Segura "
                                  "melhor contra fundo claro na lista de stories.",
    "avatar-marca-tipografada.png": "Os três quadrados de tinta preenchidos com "
                                    "macro de obra real. Degrada bem: com 110 px "
                                    "os três viram cinza juntos.",
    "avatar-letra.png": "Um O em corpo de selo, com o quadradinho de destaque "
                        "no vazio.",
    "avatar-letra-invertido.png": "A mesma, em campo de tinta. Vira um alvo — "
                                  "a que mais chama atenção numa lista.",
    "avatar-letra-tipografada.png": "USO GRANDE (capa, camiseta). Como foto de "
                                    "perfil não serve: com 110 px a textura de "
                                    "texto vira cinza chapado.",
    # destaques
    "destaque-colecao.png": "Capa do destaque “Coleção”.",
    "destaque-processo.png": "Capa do destaque “Processo”.",
    "destaque-encomenda.png": "Capa do destaque “Encomenda”.",
    "destaque-sobre.png": "Capa do destaque “Sobre”.",
    "destaque-precos.png": "Capa do destaque “Preços”.",
    # assinaturas
    "lockup-horizontal.png": "Assinatura deitada — faixa, banner, rodapé de e-mail.",
    "lockup-horizontal-invertido.png": "A deitada, para fundo escuro.",
    "lockup-empilhado.png": "Assinatura quadrada, para espaço sem largura.",
    "lockup-empilhado-invertido.png": "A quadrada, para fundo escuro.",
    # referência
    "chapa-avatares.png": "REFERÊNCIA (não postar): cada avatar em 110 px "
                          "circular, que é o tamanho real no feed.",
    "chapa-lockups.png": "REFERÊNCIA (não postar): as quatro assinaturas lado a lado.",
    "chapa-destaques.png": "REFERÊNCIA (não postar): as cinco capas em fileira.",
    "chapa-paleta.png": "REFERÊNCIA (não postar): paleta e escala tipográfica.",
}

THUMB_PX = 320
CORES = 256

#: namespace fixo pros ids das tarefas. Rodar o script de novo **atualiza** a
#: mesma tarefa em vez de criar uma cópia — é o que o `on conflict` embaixo
#: precisa pra ser idempotente.
NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://ondemoramaspalavras/admin/tasks")

GRUPOS = {"feed": "feed 4:5 · carrossel", "story": "story 9:16"}

#: subpastas de `social/marca/`, na ordem em que fazem sentido na ficha
GRUPOS_MARCA = [
    ("avatar-", "avatar · foto de perfil"),
    ("destaque-", "capas de destaque"),
    ("lockup-", "assinaturas"),
    ("chapa-", "provas de contato · referência"),
]


@dataclass
class Anexo:
    name: str
    url: str
    thumb: str
    group: str

    def json(self) -> dict:
        return {"name": self.name, "url": self.url, "thumb": self.thumb, "group": self.group}


@dataclass
class Tarefa:
    slug: str
    title: str
    description: str
    anexos: list[Anexo] = field(default_factory=list)
    priority: str = "media"

    @property
    def id(self) -> str:
        return str(uuid.uuid5(NS, self.slug))


# --------------------------------------------------------------------------
# publicação dos arquivos
# --------------------------------------------------------------------------

def publicar(src: Path, rel: Path, quantizar: bool, base: str) -> tuple[str, str]:
    """Copia um PNG pra `site/public/midia/<rel>` e gera a miniatura.

    Devolve `(url, url_da_miniatura)`.
    """
    dst = DESTINO / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        img = im.convert("RGB")
        if quantizar:
            img.quantize(colors=CORES, method=Image.MEDIANCUT, dither=Image.NONE).save(
                dst, optimize=True
            )
        else:
            shutil.copyfile(src, dst)
        thumb_rel = rel.with_name(f"{rel.stem}-thumb.webp")
        escala = THUMB_PX / max(img.size)
        thumb = (img.resize((max(1, round(img.width * escala)),
                             max(1, round(img.height * escala))), Image.LANCZOS)
                 if escala < 1 else img)
        thumb.save(DESTINO / thumb_rel, quality=80, method=6)
    return (f"{base}/{rel.as_posix()}", f"{base}/{thumb_rel.as_posix()}")


def anexos_da_obra(slug: str, quantizar: bool, base: str) -> list[Anexo]:
    out = []
    for pasta, rotulo in GRUPOS.items():
        origem = SOCIAL / slug / pasta
        if not origem.is_dir():
            continue
        for png in sorted(origem.glob("*.png")):
            rel = Path(slug) / pasta / png.name
            url, thumb = publicar(png, rel, quantizar, base)
            out.append(Anexo(png.name, url, thumb, rotulo))
    return out


def ordem_editorial(nome: str) -> int:
    """Posição do arquivo na ordem em que faz sentido lê-lo.

    É a ordem de `DESCRICOES`, não a alfabética: dentro dos avatares o
    recomendado é o `avatar-marca.png`, e em ordem alfabética ele cai por
    último, depois de duas variantes que a ficha desaconselha. Arquivo sem
    descrição vai pro fim.
    """
    chaves = list(DESCRICOES)
    return chaves.index(nome) if nome in chaves else len(chaves)


def anexos_da_marca(quantizar: bool, base: str) -> list[Anexo]:
    origem = SOCIAL / "marca"
    if not origem.is_dir():
        return []
    todos = sorted(origem.glob("*.png"), key=lambda p: (ordem_editorial(p.name), p.name))
    out, vistos = [], set()
    for prefixo, rotulo in GRUPOS_MARCA:
        for png in todos:
            if not png.name.startswith(prefixo) or png.name in vistos:
                continue
            vistos.add(png.name)
            rel = Path("marca") / png.name
            url, thumb = publicar(png, rel, quantizar, base)
            out.append(Anexo(png.name, url, thumb, rotulo))
    return out


def lista_de_arquivos(anexos: list[Anexo]) -> str:
    """A lista de arquivos em markdown: nome, link e o que cada um é.

    Existe porque a ficha da tarefa é lida antes dos anexos serem clicados —
    e porque link cru numa lista não diz qual arquivo é o que segura o post.
    Sem descrição, "03-macro.png" e "02-malha.png" são a mesma coisa pra quem
    não montou o carrossel.
    """
    linhas = ["## Arquivos"]
    grupo_atual = None
    for a in anexos:
        if a.group != grupo_atual:
            grupo_atual = a.group
            linhas.append(f"\n**{a.group}**\n")
        texto = DESCRICOES.get(a.name, "")
        linhas.append(f"- [{a.name}]({a.url}) — {texto}" if texto
                      else f"- [{a.name}]({a.url})")
    return "\n".join(linhas)


# --------------------------------------------------------------------------
# conteúdo das tarefas
# --------------------------------------------------------------------------

def descricao_obra(slug: str) -> str:
    meta = {}
    caminho = ROOT / "site" / "src" / "data" / "works.json"
    if caminho.exists():
        for entry in json.loads(caminho.read_text(encoding="utf-8")):
            if entry.get("slug") == slug:
                meta = entry
                break
    titulo = meta.get("title", slug.replace("-", " ").upper())
    sub = meta.get("subtitle", "")
    glifos = f"{meta['glyphs']:,}".replace(",", ".") if meta.get("glyphs") else "—"
    dim = (f"{meta['widthCm']:.0f} × {meta['heightCm']:.0f} cm"
           if meta.get("widthCm") else "—")

    return f"""## {titulo}

{sub}

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

**Ficha:** {dim} · {glifos} glifos · impressão em 150 dpi.

> A carta 3 é a que segura o post. Se for cortar alguma, corte a 2.
"""


DESCRICAO_MARCA = """## Identidade do perfil

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
"""


# --------------------------------------------------------------------------
# SQL
# --------------------------------------------------------------------------

def sql_txt(valor: str) -> str:
    """Literal de texto do Postgres. Aspa simples dentro vira aspa dobrada."""
    return "'" + valor.replace("'", "''") + "'"


def gerar_sql(tarefas: list[Tarefa], responsavel: str) -> str:
    agora = datetime.now(timezone.utc)
    base = int(agora.timestamp() * 1000)
    linhas = []
    for i, t in enumerate(tarefas):
        anexos = json.dumps([a.json() for a in t.anexos], ensure_ascii=False)
        linhas.append(
            "  (" + ", ".join([
                sql_txt(t.id) + "::uuid",
                sql_txt(t.title),
                sql_txt("social"),
                sql_txt("todo"),
                sql_txt(t.priority),
                sql_txt(t.description),
                sql_txt(responsavel),
                sql_txt(anexos) + "::jsonb",
                str(base + i),
            ]) + ")"
        )

    total = sum(len(t.anexos) for t in tarefas)
    corpo = ",\n".join(linhas)  # f-string do 3.11 não aceita barra invertida dentro
    return f"""-- Tarefas de mídia social — GERADO por scripts/publish_media.py
-- {agora.isoformat(timespec='seconds')} · {len(tarefas)} tarefas · {total} anexos
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
{corpo}
on conflict (id) do update set
  title       = excluded.title,
  description = excluded.description,
  assignee    = excluded.assignee,
  attachments = excluded.attachments,
  updated_at  = now();
"""


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("slugs", nargs="*",
                    help="obras a publicar (padrão: todas as que têm mídia em social/)")
    ap.add_argument("--responsavel", default="geovana",
                    help="id do responsável (ver ASSIGNEES em site/src/admin/store.js)")
    ap.add_argument("--base-url", default=URL_BASE,
                    help="prefixo das URLs. O padrão (/midia) só funciona depois "
                         "do deploy do site; use o raw do GitHub pra ter link "
                         "que funciona hoje")
    ap.add_argument("--sem-quantizar", action="store_true",
                    help="mantém PNG de 24 bits (arquivos ~3× maiores)")
    args = ap.parse_args()

    if not SOCIAL.is_dir():
        raise SystemExit("não há nada em social/. Rode scripts/build_instagram.py antes.")

    quantizar = not args.sem_quantizar
    base = args.base_url.rstrip("/")
    slugs = args.slugs or sorted(
        p.name for p in SOCIAL.iterdir() if p.is_dir() and p.name != "marca"
    )

    tarefas: list[Tarefa] = []
    marca = anexos_da_marca(quantizar, base)
    if marca:
        tarefas.append(Tarefa(
            slug="marca",
            title="Perfil no Instagram — avatar, destaques e assinaturas",
            description=DESCRICAO_MARCA + "\n" + lista_de_arquivos(marca),
            anexos=marca,
            priority="alta",
        ))
        print(f"  ok marca                {len(marca)} arquivos")

    for slug in slugs:
        anexos = anexos_da_obra(slug, quantizar, base)
        if not anexos:
            print(f"  ! {slug}: sem feed/ nem story/ em social/{slug}, pulando")
            continue
        titulo = slug.replace("-", " ").upper()
        tarefas.append(Tarefa(
            slug=f"carrossel:{slug}",
            title=f"Carrossel — {titulo}",
            description=descricao_obra(slug) + "\n" + lista_de_arquivos(anexos),
            anexos=anexos,
        ))
        print(f"  ok {slug:<20} {len(anexos)} arquivos")

    if not tarefas:
        raise SystemExit("nenhuma mídia encontrada — nada a publicar.")

    SEED.parent.mkdir(parents=True, exist_ok=True)
    SEED.write_text(gerar_sql(tarefas, args.responsavel), encoding="utf-8")

    peso = sum(f.stat().st_size for f in DESTINO.rglob("*") if f.is_file())
    print(f"\nmídia  -> {DESTINO.relative_to(ROOT)}  ({peso / 1024 / 1024:.1f} MB)")
    print(f"tarefas -> {SEED.relative_to(ROOT)}  ({len(tarefas)} tarefas, "
          f"responsável: {args.responsavel})")
    print("\nfalta você fazer, nesta ordem:")
    print("  1. SQL Editor do Supabase: rodar site/supabase/migrations/"
          "0001_assignee_attachments.sql (uma vez só)")
    print(f"  2. SQL Editor do Supabase: rodar {SEED.relative_to(ROOT).as_posix()}")
    print("  3. criar o login da Geovana em Authentication > Users, no painel "
          "do Supabase")
    print("  4. publicar o site (as URLs de /midia só existem depois do deploy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
