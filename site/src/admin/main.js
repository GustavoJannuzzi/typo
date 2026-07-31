import { isAuthed, signIn, signOut } from "./auth.js";
import { list, save, saveMany, remove, blankTask, STATUSES, TYPES, PRIORITIES } from "./store.js";
import { createBoard } from "./board.js";
import { renderMarkdown } from "./markdown.js";

const gate = document.querySelector("[data-gate]");
const app = document.querySelector("[data-app]");
const modal = document.querySelector("[data-modal]");
const form = modal.querySelector("[data-form]");
const mdInput = modal.querySelector("[data-md-input]");
const mdPreview = modal.querySelector("[data-md-preview]");
const deleteBtn = modal.querySelector("[data-delete]");

let tasks = [];
let editing = null;
let board = null;

// --- portão ---------------------------------------------------------------
const gateForm = document.querySelector("[data-gate-form]");
const gateError = document.querySelector("[data-gate-error]");

gateForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const value = new FormData(gateForm).get("passphrase");
  const result = await signIn(String(value));
  if (!result.ok) {
    gateError.textContent = result.message;
    gateError.hidden = false;
    gateForm.querySelector("input").select();
    return;
  }
  enter();
});

document.querySelector("[data-signout]").addEventListener("click", () => {
  signOut();
  location.reload();
});

async function enter() {
  gate.hidden = true;
  app.hidden = false;
  fillSelect("type", TYPES);
  fillSelect("status", STATUSES);
  fillSelect("priority", PRIORITIES);
  board = createBoard(document.querySelector("[data-board]"), {
    onOpen: openSheet,
    onAdd: (status) => openSheet({ ...blankTask(), status }, true),
    onMove: (changed) => saveMany(changed),
  });
  tasks = await list();
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

// --- ficha ----------------------------------------------------------------
function openSheet(task, isNew = false) {
  editing = task;
  form.elements.title.value = task.title;
  form.elements.type.value = task.type;
  form.elements.status.value = task.status;
  form.elements.priority.value = task.priority;
  mdInput.value = task.description;
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
    description: mdInput.value,
  };
  const saved = await save(next);
  const i = tasks.findIndex((t) => t.id === saved.id);
  if (i === -1) tasks.push(saved);
  else tasks[i] = saved;
  closeSheet();
  refresh();
});

deleteBtn.addEventListener("click", async () => {
  if (!confirm(`Apagar “${editing.title || "sem título"}”?`)) return;
  await remove(editing.id);
  tasks = tasks.filter((t) => t.id !== editing.id);
  closeSheet();
  refresh();
});

if (isAuthed()) enter();
