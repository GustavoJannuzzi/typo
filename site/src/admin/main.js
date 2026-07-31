import { isAuthed, signIn, signOut } from "./auth.js";
import {
  list,
  save,
  saveMany,
  remove,
  blankTask,
  STATUSES,
  TYPES,
  PRIORITIES,
  ASSIGNEES,
} from "./store.js";
import { createBoard } from "./board.js";
import { renderMarkdown } from "./markdown.js";

const gate = document.querySelector("[data-gate]");
const app = document.querySelector("[data-app]");
const modal = document.querySelector("[data-modal]");
const form = modal.querySelector("[data-form]");
const mdInput = modal.querySelector("[data-md-input]");
const mdPreview = modal.querySelector("[data-md-preview]");
const deleteBtn = modal.querySelector("[data-delete]");
const media = modal.querySelector("[data-media]");
const mediaGrid = modal.querySelector("[data-media-grid]");

let tasks = [];
let editing = null;
let board = null;

// --- portão ---------------------------------------------------------------
const gateForm = document.querySelector("[data-gate-form]");
const gateError = document.querySelector("[data-gate-error]");

gateForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = new FormData(gateForm);
  const submit = gateForm.querySelector("button[type=submit]");
  submit.disabled = true;
  const result = await signIn(String(data.get("email")), String(data.get("password")));
  submit.disabled = false;
  if (!result.ok) {
    gateError.textContent = result.message;
    gateError.hidden = false;
    gateForm.elements.password.select();
    return;
  }
  gateError.hidden = true;
  enter();
});

document.querySelector("[data-signout]").addEventListener("click", async () => {
  await signOut();
  location.reload();
});

function failed(err) {
  console.error(err);
  alert("Não deu para falar com o servidor. Tente de novo.");
}

async function enter() {
  gate.hidden = true;
  app.hidden = false;
  fillSelect("type", TYPES);
  fillSelect("status", STATUSES);
  fillSelect("priority", PRIORITIES);
  fillSelect("assignee", ASSIGNEES);
  board = createBoard(document.querySelector("[data-board]"), {
    onOpen: openSheet,
    onAdd: (status) => openSheet({ ...blankTask(), status }, true),
    onMove: (changed) => saveMany(changed).catch(failed),
  });
  try {
    tasks = await list();
  } catch (err) {
    return failed(err);
  }
  refresh();
}

function fillSelect(name, options) {
  const select = form.querySelector(`[data-options="${name}"]`);
  select.innerHTML = options.map((o) => `<option value="${o.id}">${o.label}</option>`).join("");
}

function refresh() {
  board.setTasks(tasks);
  document.querySelector("[data-total]").textContent = `${tasks.length} tarefas`;
}

// --- mídia ----------------------------------------------------------------

/**
 * So' caminho interno e http(s), como no `safeUrl` do markdown.js.
 *
 * O anexo so' entra no banco por quem ja' esta' autenticado, entao isto nao e'
 * a barreira principal — mas `href`/`src` sao exatamente onde um
 * `javascript:` vira XSS, e o custo de barrar aqui e' uma funcao de tres
 * linhas.
 */
function safeMediaUrl(raw) {
  const url = String(raw || "").trim();
  if (/^https?:\/\//i.test(url)) return url;
  if (url.startsWith("/")) return url;
  return "";
}

/** o link que a Geovana cola em outro lugar precisa ser absoluto */
function absolute(url) {
  try {
    return new URL(url, location.origin).href;
  } catch {
    return url;
  }
}

function copy(text, botao) {
  navigator.clipboard.writeText(text).then(
    () => {
      const antes = botao.textContent;
      botao.textContent = "copiado ✓";
      botao.classList.add("is-done");
      setTimeout(() => {
        botao.textContent = antes;
        botao.classList.remove("is-done");
      }, 1400);
    },
    () => alert("O navegador bloqueou a cópia. Use o link com o botão direito.")
  );
}

function mediaItem(anexo, index) {
  const url = safeMediaUrl(anexo.url);
  const el = document.createElement("figure");
  el.className = "media-item";
  if (!url) {
    el.classList.add("media-item--broken");
    el.textContent = `${anexo.name} (link inválido)`;
    return el;
  }

  const link = document.createElement("a");
  link.className = "media-item__thumb";
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  const img = document.createElement("img");
  img.src = safeMediaUrl(anexo.thumb) || url;
  img.alt = anexo.name;
  img.loading = "lazy";
  link.appendChild(img);

  const cap = document.createElement("figcaption");
  cap.className = "media-item__cap";
  const nome = document.createElement("span");
  nome.className = "media-item__name";
  nome.textContent = anexo.name;
  cap.appendChild(nome);

  const acoes = document.createElement("div");
  acoes.className = "media-item__actions";

  const copiar = document.createElement("button");
  copiar.type = "button";
  copiar.className = "label media-item__btn";
  copiar.textContent = "copiar link";
  copiar.addEventListener("click", () => copy(absolute(url), copiar));

  // `download` so' baixa em vez de navegar quando a origem e' a mesma — e e',
  // porque a midia e' servida pelo proprio site em /midia/
  const baixar = document.createElement("a");
  baixar.className = "label media-item__btn";
  baixar.href = url;
  baixar.download = anexo.name;
  baixar.textContent = "baixar";

  const tirar = document.createElement("button");
  tirar.type = "button";
  tirar.className = "label media-item__btn media-item__btn--danger";
  tirar.textContent = "remover";
  tirar.addEventListener("click", () => {
    editing.attachments = editing.attachments.filter((_, i) => i !== index);
    renderMedia(editing.attachments);
  });

  acoes.append(copiar, baixar, tirar);
  el.append(link, cap, acoes);
  return el;
}

function renderMedia(anexos) {
  mediaGrid.textContent = "";
  media.hidden = !anexos.length;
  if (!anexos.length) return;

  // agrupado pelo campo `group` (o formato: "feed 4:5", "story 9:16", …), na
  // ordem em que os grupos aparecem — quem gera a lista ja' ordenou
  const grupos = new Map();
  anexos.forEach((anexo, i) => {
    const chave = anexo.group || "arquivos";
    if (!grupos.has(chave)) grupos.set(chave, []);
    grupos.get(chave).push([anexo, i]);
  });

  grupos.forEach((itens, nome) => {
    const titulo = document.createElement("p");
    titulo.className = "readout media__group";
    titulo.textContent = `${nome} · ${itens.length}`;
    mediaGrid.appendChild(titulo);
    const linha = document.createElement("div");
    linha.className = "media__row";
    itens.forEach(([anexo, i]) => linha.appendChild(mediaItem(anexo, i)));
    mediaGrid.appendChild(linha);
  });
}

modal.querySelector("[data-copy-all]").addEventListener("click", (e) => {
  const links = (editing?.attachments || [])
    .map((a) => safeMediaUrl(a.url))
    .filter(Boolean)
    .map(absolute);
  if (links.length) copy(links.join("\n"), e.currentTarget);
});

// --- ficha ----------------------------------------------------------------
function openSheet(task, isNew = false) {
  editing = task;
  form.elements.title.value = task.title;
  form.elements.type.value = task.type;
  form.elements.status.value = task.status;
  form.elements.priority.value = task.priority;
  form.elements.assignee.value = task.assignee || "";
  mdInput.value = task.description;
  renderMedia(task.attachments || []);
  showTab("write");
  deleteBtn.hidden = isNew;
  modal.hidden = false;
  document.documentElement.classList.add("is-locked");
  form.elements.title.focus();
}

function closeSheet() {
  modal.hidden = true;
  editing = null;
  document.documentElement.classList.remove("is-locked");
}

function showTab(tab) {
  const write = tab === "write";
  mdInput.hidden = !write;
  mdPreview.hidden = write;
  if (!write) mdPreview.innerHTML = renderMarkdown(mdInput.value) || "<p class='readout'>sem descrição</p>";
  modal.querySelectorAll("[data-tab]").forEach((b) => b.classList.toggle("is-active", b.dataset.tab === tab));
}

modal.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
modal.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", closeSheet));

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modal.hidden) closeSheet();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const next = {
    ...editing,
    title: form.elements.title.value.trim(),
    type: form.elements.type.value,
    status: form.elements.status.value,
    priority: form.elements.priority.value,
    assignee: form.elements.assignee.value,
    description: mdInput.value,
  };
  let saved;
  try {
    saved = await save(next);
  } catch (err) {
    return failed(err);
  }
  const i = tasks.findIndex((t) => t.id === saved.id);
  if (i === -1) tasks.push(saved);
  else tasks[i] = saved;
  closeSheet();
  refresh();
});

deleteBtn.addEventListener("click", async () => {
  if (!confirm(`Apagar “${editing.title || "sem título"}”?`)) return;
  const id = editing.id;
  try {
    await remove(id);
  } catch (err) {
    return failed(err);
  }
  tasks = tasks.filter((t) => t.id !== id);
  closeSheet();
  refresh();
});

// o Supabase devolve a sessao de forma assincrona, entao mostrar o quadro so'
// pode ser decidido depois dessa volta — nao da' pra checar no corpo do modulo.
isAuthed().then((yes) => yes && enter());
