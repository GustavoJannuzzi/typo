/**
 * Fonte de dados do quadro.
 *
 * A API e' assincrona de proposito. Hoje tudo mora no localStorage do
 * navegador, mas o Supabase entra como um adaptador com estas mesmas quatro
 * funcoes (`list`, `save`, `saveMany`, `remove`) — `board.js` nao precisa
 * saber de nada. Por isso `saveMany` existe: um arrasto mexe na ordem de
 * varios cartoes de uma vez, e la' isso vira um `upsert` unico em vez de N
 * requisicoes.
 */

const KEY = "omp.admin.tasks.v1";

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

const SEED = [
  {
    title: "Solicitação de pedido — fluxo de entrada",
    type: "pedido",
    status: "todo",
    priority: "alta",
    description:
      "Receber o brief pelo WhatsApp e catalogar como espécime.\n\n" +
      "- [ ] confirmar foto de referência\n" +
      "- [ ] confirmar o texto (letra, trecho, carta)\n" +
      "- [ ] definir tamanho de impressão\n",
  },
  {
    title: "Arte autoral — próximo espécime da coleção",
    type: "arte",
    status: "doing",
    priority: "media",
    description:
      "Escolher referência e texto para a décima peça.\n\n" +
      "> A coleção hoje tem **nove** espécimes catalogados.\n",
  },
  {
    title: "Supabase: sair do localStorage",
    type: "tech",
    status: "todo",
    priority: "media",
    description:
      "Criar o projeto, rodar as queries e trocar o adaptador em `src/admin/store.js`.\n\n" +
      "A interface já é assíncrona, então é só substituir o corpo das quatro funções.\n",
  },
  {
    title: "Posts pro Instagram",
    type: "social",
    status: "todo",
    priority: "baixa",
    description: "Sequência mostrando o *antes e depois*: foto de referência ↦ malha de letras.\n",
  },
];

function newId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return `t${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // storage corrompido ou bloqueado — recomeca do seed em vez de morrer
  }
  const now = new Date().toISOString();
  const seeded = SEED.map((t, i) => ({
    ...t,
    id: newId(),
    order: i,
    createdAt: now,
    updatedAt: now,
  }));
  write(seeded);
  return seeded;
}

function write(tasks) {
  try {
    localStorage.setItem(KEY, JSON.stringify(tasks));
  } catch {
    // modo privado / cota estourada: o quadro segue vivo em memoria
  }
}

export function blankTask() {
  const now = new Date().toISOString();
  return {
    id: newId(),
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
  return read();
}

export async function save(task) {
  const tasks = read();
  const next = { ...task, updatedAt: new Date().toISOString() };
  const i = tasks.findIndex((t) => t.id === next.id);
  if (i === -1) tasks.push(next);
  else tasks[i] = next;
  write(tasks);
  return next;
}

export async function saveMany(changed) {
  const tasks = read();
  const byId = new Map(changed.map((t) => [t.id, t]));
  write(tasks.map((t) => byId.get(t.id) || t));
}

export async function remove(id) {
  write(read().filter((t) => t.id !== id));
}
