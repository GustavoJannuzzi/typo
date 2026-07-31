-- `position` precisa ser bigint, não integer.
--
-- Rode no SQL Editor do Supabase, depois da 0001. É seguro e não destrutivo:
-- alargar integer -> bigint preserva todo valor existente.
--
-- Por que: a ordem de um cartão novo é `Date.now()` (ver `blankTask()` em
-- site/src/admin/store.js). Hoje isso dá 1.785.522.648.393, e o teto do
-- `integer` do Postgres é 2.147.483.647 — três ordens de grandeza abaixo.
-- Ou seja: **qualquer tarefa criada pelo botão "+ tarefa" já falhava** com
-- `22003: integer out of range`. O quadro nunca tinha esbarrado nisso porque
-- arrastar um cartão renumera a coluna inteira para 0,1,2… (o `commit()` do
-- board.js), e a carga inicial veio do localStorage com números pequenos.
--
-- O timestamp como ordem é intencional e vale manter: é monotônico, não
-- colide entre duas abas e põe o cartão novo no fim sem precisar consultar o
-- resto da tabela. Quem estava errado era o tipo da coluna.

do $$
begin
  if (
    select data_type
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'tasks'
      and column_name = 'position'
  ) is distinct from 'bigint' then
    alter table public.tasks alter column position type bigint;
  end if;
end $$;

comment on column public.tasks.position is
  'ordem dentro da coluna do quadro. Cartão novo entra com Date.now() (ms), '
  'e arrastar renumera a coluna a partir de 0 — daí bigint, não integer.';
