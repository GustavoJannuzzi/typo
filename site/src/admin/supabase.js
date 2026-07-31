/**
 * Cliente unico do Supabase.
 *
 * A URL e a chave publicavel ficam em texto puro aqui de proposito: elas vao
 * pro bundle de qualquer jeito e foram feitas pra isso. Quem protege a tabela
 * e' a RLS — a policy de `public.tasks` so aceita `authenticated`, entao com
 * esta chave sozinha nao se le nem se escreve nada.
 */
import { createClient } from "@supabase/supabase-js";

const URL = "https://qgydjrcobxcijslcyxsd.supabase.co";
const PUBLISHABLE_KEY = "sb_publishable_azKKRUqarW3UQrq6GFH9kQ_muv9bJcm";

export const supabase = createClient(URL, PUBLISHABLE_KEY);
