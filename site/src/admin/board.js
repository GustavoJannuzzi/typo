import { STATUSES, TYPES, PRIORITIES } from "./store.js";

/**
 * Quadro kanban.
 *
 * O arrasto e' Pointer Events puro (mouse e toque no mesmo caminho), sem
 * biblioteca e sem a API nativa de drag-and-drop, que no toque simplesmente
 * nao existe.
 *
 * Duas decisoes que nao sao obvias:
 *
 * 1. No toque so o *punho* arrasta. Se o cartao inteiro arrastasse, ele
 *    precisaria de `touch-action: none` e a coluna deixaria de rolar com o
 *    dedo. No mouse nao ha esse conflito, entao ali o cartao inteiro pega.
 * 2. Quem segue o dedo e' um clone; o cartao original fica no fluxo e vai
 *    sendo reinserido na posicao de destino. Ele e' o proprio marcador de
 *    lugar, entao nao existe elemento fantasma pra sincronizar — no `pointerup`
 *    o DOM ja' esta' na configuracao final e so' falta ler a ordem.
 */

const DRAG_THRESHOLD = 6;

const TYPE_LABEL = new Map(TYPES.map((t) => [t.id, t.label]));
const PRIORITY_LABEL = new Map(PRIORITIES.map((p) => [p.id, p.label]));

const dateFmt = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" });

function cardEl(task) {
  const el = document.createElement("article");
  el.className = "task-card";
  el.dataset.card = "";
  el.dataset.id = task.id;
  el.tabIndex = 0;
  el.setAttribute("role", "button");

  el.innerHTML = `
    <div class="task-card__top">
      <span class="task-card__type label" data-type="${task.type}"></span>
      <span class="task-card__grip" data-grip title="Arrastar"><i></i><i></i><i></i><i></i></span>
    </div>
    <h3 class="task-card__title"></h3>
    <p class="task-card__meta readout">
      <span class="task-card__prio" data-prio="${task.priority}"></span>
      <span class="task-card__date"></span>
    </p>`;

  el.querySelector(".task-card__type").textContent = TYPE_LABEL.get(task.type) || task.type;
  el.querySelector(".task-card__title").textContent = task.title || "sem título";
  el.querySelector(".task-card__prio").textContent = PRIORITY_LABEL.get(task.priority) || task.priority;
  el.querySelector(".task-card__date").textContent = dateFmt.format(new Date(task.updatedAt));
  return el;
}

export function createBoard(root, { onOpen, onMove, onAdd }) {
  let tasks = [];
  let drag = null;
  let justDragged = false;

  root.innerHTML = STATUSES.map(
    (s) => `
    <section class="column" data-column data-status="${s.id}">
      <header class="column__head">
        <span class="label column__title">${s.label}</span>
        <span class="readout column__count" data-count>0</span>
      </header>
      <div class="column__list" data-list></div>
      <button type="button" class="column__add label" data-add="${s.id}">+ tarefa</button>
    </section>`
  ).join("");

  const lists = new Map(
    [...root.querySelectorAll("[data-column]")].map((c) => [c.dataset.status, c.querySelector("[data-list]")])
  );

  function render() {
    lists.forEach((list) => (list.textContent = ""));
    [...tasks]
      .sort((a, b) => a.order - b.order)
      .forEach((task) => {
        const list = lists.get(task.status) || lists.get("todo");
        list.appendChild(cardEl(task));
      });
    updateCounts();
  }

  function updateCounts() {
    root.querySelectorAll("[data-column]").forEach((column) => {
      column.querySelector("[data-count]").textContent = String(
        column.querySelectorAll("[data-card]").length
      );
    });
  }

  /** le a configuracao atual do DOM e devolve so' os cartoes que mudaram */
  function commit() {
    const changed = [];
    root.querySelectorAll("[data-column]").forEach((column) => {
      const status = column.dataset.status;
      [...column.querySelectorAll("[data-card]")].forEach((el, i) => {
        const task = tasks.find((t) => t.id === el.dataset.id);
        if (!task) return;
        if (task.status !== status || task.order !== i) {
          task.status = status;
          task.order = i;
          changed.push(task);
        }
      });
    });
    updateCounts();
    if (changed.length) onMove(changed);
  }

  function dropTarget(x, y) {
    const under = document.elementFromPoint(x, y);
    const column = under && under.closest("[data-column]");
    if (!column) return null;
    const list = column.querySelector("[data-list]");
    const before = [...list.querySelectorAll("[data-card]")]
      .filter((c) => c !== drag.card)
      .find((c) => {
        const r = c.getBoundingClientRect();
        return y < r.top + r.height / 2;
      });
    return { list, before: before || null };
  }

  function startDrag(e) {
    const rect = drag.card.getBoundingClientRect();
    drag.active = true;
    drag.offsetX = drag.x0 - rect.left;
    drag.offsetY = drag.y0 - rect.top;

    drag.ghost = drag.card.cloneNode(true);
    drag.ghost.classList.add("task-card--ghost");
    drag.ghost.style.width = `${rect.width}px`;
    document.body.appendChild(drag.ghost);

    drag.card.classList.add("task-card--source");
    root.classList.add("is-dragging");
    drag.card.setPointerCapture(e.pointerId);
  }

  function endDrag() {
    drag.ghost.remove();
    drag.card.classList.remove("task-card--source");
    root.classList.remove("is-dragging");
  }

  root.addEventListener("pointerdown", (e) => {
    const card = e.target.closest("[data-card]");
    if (!card) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    if (e.pointerType !== "mouse" && !e.target.closest("[data-grip]")) return;
    drag = { card, x0: e.clientX, y0: e.clientY, pointerId: e.pointerId, active: false };
  });

  root.addEventListener("pointermove", (e) => {
    if (!drag || e.pointerId !== drag.pointerId) return;
    if (!drag.active) {
      if (Math.hypot(e.clientX - drag.x0, e.clientY - drag.y0) < DRAG_THRESHOLD) return;
      startDrag(e);
    }
    e.preventDefault();
    drag.ghost.style.transform = `translate(${e.clientX - drag.offsetX}px, ${e.clientY - drag.offsetY}px)`;
    const target = dropTarget(e.clientX, e.clientY);
    if (target) target.list.insertBefore(drag.card, target.before);
  });

  root.addEventListener("pointerup", (e) => {
    if (!drag || e.pointerId !== drag.pointerId) return;
    if (drag.active) {
      endDrag();
      // o clique sintetico que o navegador dispara depois do arrasto tem que ser
      // engolido, mas ele nem sempre chega — se o alvo do pointerup nao virar
      // cartao, a flag ficaria armada e comeria o proximo clique de verdade.
      // O timeout roda so' na proxima macrotarefa, depois do clique.
      justDragged = true;
      setTimeout(() => (justDragged = false));
      commit();
    }
    drag = null;
  });

  root.addEventListener("pointercancel", () => {
    if (!drag) return;
    if (drag.active) {
      endDrag();
      render();
    }
    drag = null;
  });

  root.addEventListener("click", (e) => {
    const add = e.target.closest("[data-add]");
    if (add) {
      onAdd(add.dataset.add);
      return;
    }
    const card = e.target.closest("[data-card]");
    if (!card) return;
    if (justDragged) return;
    const task = tasks.find((t) => t.id === card.dataset.id);
    if (task) onOpen(task);
  });

  root.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const card = e.target.closest("[data-card]");
    if (!card) return;
    e.preventDefault();
    const task = tasks.find((t) => t.id === card.dataset.id);
    if (task) onOpen(task);
  });

  return {
    setTasks(next) {
      tasks = next;
      render();
    },
  };
}
