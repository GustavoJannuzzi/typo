/**
 * Fonte de dados do quadro — tabela `public.tasks` no Supabase.
 *
 * As quatro funcoes (`list`, `save`, `saveMany`, `remove`) sao as mesmas de
 * quando isto morava no localStorage: `board.js` nunca soube da diferenca.
 * `saveMany` existe porque um arrasto mexe na ordem de varios cartoes de uma
 * vez — aqui isso e' um `upsert` unico em vez de N requisicoes.
 *
 * No banco a coluna e' `position`, nao `order`: `order` e' palavra reservada
 * em SQL. A traducao pro nome que a UI usa acontece nas duas funcoes de
 * mapeamento abaixo, e em nenhum outro lugar.
 */
import { supabase } from "./supabase.js";

export const STATUSES = [
  { id: "todo", label: "A fazer" },
  { id: "doing", label: "Em curso" },
  { id: "review", label: "Revisão" },
  { id: "done", label: "Feito" },
];

export const TYPES = [
  { id: "pedido", label: "Pedido" },
  { id: "arte", label: "Arte autoral" },
  { id: "tech", label: "Tecnologia" },
  { id: "social", label: "Social" },
];

export const PRIORITIES = [
  { id: "baixa", label: "Baixa" },
  { id: "media", label: "Média" },
  { id: "alta", label: "Alta" },
];

function toTask(row) {
  return {
    id: row.id,
    title: row.title,
    type: row.type,
    status: row.status,
    priority: row.priority,
    description: row.description,
    order: row.position,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function toRow(task) {
  return {
    id: task.id,
    title: task.title,
    type: task.type,
    status: task.status,
    priority: task.priority,
    description: task.description,
    position: task.order,
    updated_at: new Date().toISOString(),
  };
}

export function blankTask() {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: "",
    type: "pedido",
    status: "todo",
    priority: "media",
    description: "",
    order: Date.now(),
    createdAt: now,
    updatedAt: now,
  };
}

export async function list() {
  const { data, error } = await supabase.from("tasks").select("*").order("position");
  if (error) throw error;
  return data.map(toTask);
}

export async function save(task) {
  const { data, error } = await supabase
    .from("tasks")
    .upsert(toRow(task))
    .select()
    .single();
  if (error) throw error;
  return toTask(data);
}

export async function saveMany(changed) {
  const { error } = await supabase.from("tasks").upsert(changed.map(toRow));
  if (error) throw error;
}

export async function remove(id) {
  const { error } = await supabase.from("tasks").delete().eq("id", id);
  if (error) throw error;
}
