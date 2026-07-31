/**
 * Trava do /admin.
 *
 * Antes isto era um portao com hash no cliente — nao protegia nada, porque o
 * dado tambem morava no navegador. Agora quem autentica e' o Supabase: a
 * sessao vira um JWT que o PostgREST le, e a RLS de `public.tasks` decide o
 * que aquele token pode ver. O modulo virou a casca fina que o comentario
 * antigo prometia.
 */
import { supabase } from "./supabase.js";

export async function isAuthed() {
  const { data } = await supabase.auth.getSession();
  return Boolean(data.session);
}

export async function signIn(email, password) {
  const { error } = await supabase.auth.signInWithPassword({
    email: email.trim(),
    password,
  });
  if (!error) return { ok: true };
  const offline = error.message.toLowerCase().includes("fetch");
  return {
    ok: false,
    message: offline ? "Sem conexão com o servidor." : "E-mail ou senha não conferem.",
  };
}

export async function signOut() {
  await supabase.auth.signOut();
}
