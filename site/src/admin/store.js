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

/**
 * Responsaveis. E' uma lista fixa, nao uma consulta a `auth.users`: quem
 * aparece no cartao nao precisa ter conta (ver o comentario da migration
 * 0001). Para incluir alguem, e' uma linha aqui.
 */
export const ASSIGNEES = [
  { id: "", label: "sem responsável" },
  { id: "gustavo", label: "Gustavo" },
  { id: "geovana", label: "Geovana" },
];

/**
 * `attachments` chega do banco como jsonb. O check da migration garante que e'
 * array, mas linha antiga (anterior a migration, com a coluna recem-criada) e
 * resposta de erro parcial nao garantem nada — entao a normalizacao acontece
 * aqui, uma vez, e o resto do /admin pode fazer `.map()` sem medo.
 */
function toAttachments(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((a) => a && typeof a.url === "string" && a.url)
    .map((a) => ({
      name: String(a.name || a.url.split("/").pop() || "arquivo"),
      url: String(a.url),
      // a ficha pode abrir com oito imagens; sem miniatura ela puxaria
      // megabytes so' pra desenhar oito quadradinhos
      thumb: String(a.thumb || a.url),
      group: String(a.group || ""),
    }));
}

function toTask(row) {
  return {
    id: row.id,
    title: row.title,
    type: row.type,
    status: row.status,
    priority: row.priority,
    description: row.description,
    assignee: row.assignee || "",
    attachments: toAttachments(row.attachments),
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
    assignee: task.assignee || null,
    attachments: toAttachments(task.attachments),
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
    assignee: "",
    attachments: [],
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
