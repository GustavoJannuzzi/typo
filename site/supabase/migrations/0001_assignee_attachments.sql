-- Responsável e anexos nas tarefas do /admin.
--
-- Rode isto uma vez no SQL Editor do Supabase (você já está autenticado lá como
-- dono do projeto). É puramente aditivo: nenhuma linha existente muda, e o
-- /admin antigo continuaria funcionando com estas colunas presentes.
--
--   assignee     texto livre com o id do responsável ("geovana", "gustavo").
--                Fica nulo/vazio em tarefa sem dono. Não é FK pra auth.users
--                de propósito: quem toca no quadro é uma equipe de duas pessoas
--                e nem toda responsável precisa ter conta pra aparecer no
--                cartão. Se um dia virar controle de acesso, aí sim vira FK.
--
--   attachments  jsonb, sempre um ARRAY de objetos:
--                  [{"name": "03-macro.png",
--                    "url": "/midia/ouro-marrom/feed/03-macro.png",
--                    "group": "feed 4:5"}]
--                O default é '[]' e o check garante que continue array — o
--                /admin faz `.map()` em cima disso sem checar, então um objeto
--                solto ali quebraria a ficha inteira.

alter table public.tasks
  add column if not exists assignee text,
  add column if not exists attachments jsonb not null default '[]'::jsonb;

alter table public.tasks
  drop constraint if exists tasks_attachments_is_array;

alter table public.tasks
  add constraint tasks_attachments_is_array
  check (jsonb_typeof(attachments) = 'array');

comment on column public.tasks.assignee is
  'id do responsável (ver ASSIGNEES em site/src/admin/store.js)';
comment on column public.tasks.attachments is
  'array de {name, url, group} — mídia da tarefa servida por site/public/midia/';

-- Filtrar "o que é da Geovana" é a consulta mais comum do quadro daqui pra
-- frente; o índice parcial ignora as linhas sem dono, que são a maioria.
create index if not exists tasks_assignee_idx
  on public.tasks (assignee)
  where assignee is not null;
