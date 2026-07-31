/**
 * Markdown minimo para o campo de descricao das tarefas.
 *
 * Nao entra `marked`/`markdown-it`: sao dezenas de kb pra um subconjunto que
 * cabe aqui, e os dois deixam HTML cru passar no meio do texto. Como a
 * descricao vai virar linha de banco quando o Supabase entrar, HTML cru ali
 * e' XSS armazenado. Aqui o texto e' escapado *antes* de qualquer
 * transformacao: as unicas tags que existem na saida sao as que este arquivo
 * emite, por construcao.
 */

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

/** so http(s), mailto e caminhos internos — barra `javascript:` e afins */
function safeUrl(raw) {
  const url = raw.trim();
  if (/^(https?:\/\/|mailto:)/i.test(url)) return url;
  if (/^[/#]/.test(url)) return url;
  return "#";
}

function emphasis(text) {
  let out = text.replace(
    /\[([^\]]+)\]\(([^)\s]+)\)/g,
    (_, label, url) => `<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`
  );
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/(^|[^*\w])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  return out.replace(/~~([^~]+)~~/g, "<del>$1</del>");
}

/**
 * O corte por crase deixa os pedacos de indice impar (= entre crases) fora do
 * passo de enfase; sem isso um `**` dentro de um trecho de codigo viraria tag.
 */
function inline(raw) {
  return escapeHtml(raw)
    .split("`")
    .map((part, i) => (i % 2 ? `<code>${part}</code>` : emphasis(part)))
    .join("");
}

const RE_FENCE = /^```/;
const RE_HR = /^(-{3,}|\*{3,}|_{3,})$/;
const RE_HEAD = /^(#{1,4})\s+(.*)$/;
const RE_QUOTE = /^\s*>\s?/;
const RE_UL = /^\s*[-*+]\s+/;
const RE_OL = /^\s*\d+[.)]\s+/;
const RE_TASK = /^\[([ xX])\]\s+/;

function isBlockStart(line) {
  return (
    RE_FENCE.test(line) ||
    RE_HR.test(line.trim()) ||
    RE_HEAD.test(line) ||
    RE_QUOTE.test(line) ||
    RE_UL.test(line) ||
    RE_OL.test(line)
  );
}

function item(text) {
  const task = RE_TASK.exec(text);
  if (!task) return `<li>${inline(text)}</li>`;
  const done = task[1] !== " ";
  return `<li class="md-task${done ? " is-done" : ""}">${inline(text.slice(task[0].length))}</li>`;
}

export function renderMarkdown(src) {
  const lines = String(src || "")
    .replace(/\r\n?/g, "\n")
    .split("\n");
  const html = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    if (RE_FENCE.test(line)) {
      const buf = [];
      i++;
      while (i < lines.length && !RE_FENCE.test(lines[i])) buf.push(lines[i++]);
      i++;
      html.push(`<pre><code>${escapeHtml(buf.join("\n"))}</code></pre>`);
      continue;
    }

    if (RE_HR.test(line.trim())) {
      html.push("<hr />");
      i++;
      continue;
    }

    const head = RE_HEAD.exec(line);
    if (head) {
      const level = Math.min(6, head[1].length + 2);
      html.push(`<h${level}>${inline(head[2])}</h${level}>`);
      i++;
      continue;
    }

    if (RE_QUOTE.test(line)) {
      const buf = [];
      while (i < lines.length && RE_QUOTE.test(lines[i])) buf.push(lines[i++].replace(RE_QUOTE, ""));
      html.push(`<blockquote>${inline(buf.join(" "))}</blockquote>`);
      continue;
    }

    if (RE_UL.test(line)) {
      const buf = [];
      while (i < lines.length && RE_UL.test(lines[i])) buf.push(lines[i++].replace(RE_UL, ""));
      html.push(`<ul>${buf.map(item).join("")}</ul>`);
      continue;
    }

    if (RE_OL.test(line)) {
      const buf = [];
      while (i < lines.length && RE_OL.test(lines[i])) buf.push(lines[i++].replace(RE_OL, ""));
      html.push(`<ol>${buf.map((t) => `<li>${inline(t)}</li>`).join("")}</ol>`);
      continue;
    }

    const buf = [];
    while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i])) buf.push(lines[i++]);
    html.push(`<p>${inline(buf.join("\n")).replace(/\n/g, "<br />")}</p>`);
  }

  return html.join("");
}
