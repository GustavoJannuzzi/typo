/**
 * Trava do /admin.
 *
 * Isto e' um portao, nao seguranca: o site e' estatico, o bundle e' publico e
 * qualquer pessoa consegue ler este arquivo. O hash so evita que a frase
 * apareca em texto puro pra quem abrir o DevTools de curioso — nao protege
 * dado nenhum, porque o dado tambem esta no navegador. Quando o Supabase
 * entrar, quem autentica de verdade e' ele (sessao + RLS na tabela) e este
 * modulo vira uma casca em volta do `signInWithPassword`.
 */

const PASS_HASH = "167c5ca03c5768fb2a0cd9d998439d69c51d2c2eb951c8711002c96780621cf3";
const SESSION_KEY = "omp.admin.session";

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function isAuthed() {
  return localStorage.getItem(SESSION_KEY) === "1";
}

export async function signIn(passphrase) {
  // `crypto.subtle` so existe em contexto seguro: https ou localhost. Abrir
  // pelo IP da rede local em http cai aqui.
  if (!crypto.subtle) {
    return { ok: false, message: "Abra por https ou localhost — o navegador bloqueia a checagem aqui." };
  }
  const hash = await sha256Hex(passphrase.trim().toLowerCase());
  if (hash !== PASS_HASH) return { ok: false, message: "Frase não confere." };
  localStorage.setItem(SESSION_KEY, "1");
  return { ok: true };
}

export function signOut() {
  localStorage.removeItem(SESSION_KEY);
}
