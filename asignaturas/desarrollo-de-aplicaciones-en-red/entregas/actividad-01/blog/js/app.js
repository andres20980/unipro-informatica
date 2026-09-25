/* ---------- Utilidades ---------- */
const PAGE_SIZE = 4;
const KEYS = {
  posts: "blog.userPosts",
  comments: "blog.comments",
  likes: "blog.likes",
  theme: "blog.theme",
};

const store = {
  read(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  },
  write(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },
};

/* Crea elementos sin usar innerHTML: el texto de usuario nunca se interpreta como HTML. */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== false && v !== null && v !== undefined)
      node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

const $ = (sel) => document.querySelector(sel);
const fmtDate = (iso) =>
  new Date(iso + (iso.length === 10 ? "T12:00:00" : "")).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
const readingMinutes = (post) =>
  Math.max(1, Math.round(post.content.join(" ").split(/\s+/).length / 200));
const normalize = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

/* ---------- Estado ---------- */
const state = {
  userPosts: store.read(KEYS.posts, []),
  comments: store.read(KEYS.comments, {}),
  likes: store.read(KEYS.likes, {}),
  category: "Todas",
  query: "",
  visible: PAGE_SIZE,
};

const allPosts = () =>
  [...state.userPosts, ...SEED_POSTS].sort((a, b) =>
    a.date < b.date ? 1 : a.date > b.date ? -1 : 0,
  );

function filteredPosts() {
  const q = normalize(state.query.trim());
  return allPosts().filter((p) => {
    if (state.category !== "Todas" && p.category !== state.category) return false;
    if (!q) return true;
    return normalize([p.title, p.content.join(" "), p.tags.join(" ")].join(" ")).includes(q);
  });
}

function toast(message) {
  const t = $("#toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), 2600);
}

/* ---------- Portada ---------- */
// Los botones se crean una sola vez y luego solo cambia su estado,
// para que el foco del teclado no se pierda al pulsar un filtro.
function renderFilters() {
  const box = $("#filters");
  if (!box.children.length) {
    box.append(
      ...["Todas", ...CATEGORIES].map((cat) =>
        el(
          "button",
          {
            type: "button",
            class: "chip",
            "data-cat": cat,
            onclick: () => {
              state.category = cat;
              state.visible = PAGE_SIZE;
              renderList();
            },
          },
          cat,
        ),
      ),
    );
  }
  for (const btn of box.children) {
    const active = btn.dataset.cat === state.category;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", String(active));
  }
}

function postCard(post) {
  const likes = state.likes[post.id] || 0;
  const commentCount = (state.comments[post.id] || []).length;
  return el(
    "article",
    { class: "card" },
    el(
      "p",
      { class: "meta" },
      el("span", { class: "badge" }, post.category),
      " ",
      fmtDate(post.date),
    ),
    el("h2", {}, el("a", { href: `#/post/${encodeURIComponent(post.id)}` }, post.title)),
    el(
      "p",
      { class: "excerpt" },
      post.content[0].length > 150 ? `${post.content[0].slice(0, 147)}…` : post.content[0],
    ),
    el(
      "ul",
      { class: "tags", "aria-label": "Etiquetas" },
      post.tags.map((t) => el("li", {}, `#${t}`)),
    ),
    el(
      "p",
      { class: "card-foot" },
      `${readingMinutes(post)} min de lectura · ♥ ${likes} · 💬 ${commentCount}`,
    ),
  );
}

function renderList() {
  renderFilters();
  const found = filteredPosts();
  const shown = found.slice(0, state.visible);
  const box = $("#posts");

  if (found.length === 0) {
    box.replaceChildren(
      el("p", { class: "empty" }, "No hay entradas que coincidan con tu búsqueda."),
    );
  } else {
    box.replaceChildren(...shown.map(postCard));
  }
  $("#results-info").textContent =
    found.length === 0
      ? ""
      : `Mostrando ${shown.length} de ${found.length} ${found.length === 1 ? "entrada" : "entradas"}.`;
  $("#btn-more").hidden = shown.length >= found.length;
}

/* ---------- Detalle de entrada ---------- */
function renderPost(id) {
  const post = allPosts().find((p) => p.id === id);
  const view = $("#view-post");
  if (!post) {
    view.replaceChildren(
      el("p", { class: "empty" }, "Esta entrada no existe."),
      el("a", { class: "btn", href: "#/" }, "← Volver al blog"),
    );
    return;
  }
  const isMine = state.userPosts.some((p) => p.id === id);
  const likes = state.likes[id] || 0;

  const likeBtn = el(
    "button",
    { type: "button", class: "btn", id: "btn-like" },
    `♥ Me gusta (${likes})`,
  );
  likeBtn.addEventListener("click", () => {
    state.likes[id] = (state.likes[id] || 0) + 1;
    store.write(KEYS.likes, state.likes);
    likeBtn.textContent = `♥ Me gusta (${state.likes[id]})`;
  });

  const actions = [likeBtn];
  if (isMine) {
    actions.push(
      el(
        "button",
        {
          type: "button",
          class: "btn btn-danger",
          onclick: () => {
            if (!confirm("¿Seguro que quieres borrar esta entrada?")) return;
            state.userPosts = state.userPosts.filter((p) => p.id !== id);
            delete state.comments[id];
            delete state.likes[id];
            store.write(KEYS.posts, state.userPosts);
            store.write(KEYS.comments, state.comments);
            store.write(KEYS.likes, state.likes);
            location.hash = "#/";
            toast("Entrada eliminada");
          },
        },
        "Borrar entrada",
      ),
    );
  }

  view.replaceChildren(
    el("a", { class: "back", href: "#/" }, "← Volver al blog"),
    el(
      "article",
      { class: "post" },
      el(
        "p",
        { class: "meta" },
        el("span", { class: "badge" }, post.category),
        " ",
        fmtDate(post.date),
        ` · ${readingMinutes(post)} min de lectura`,
      ),
      el("h1", {}, post.title),
      post.content.map((par) => el("p", {}, par)),
      el(
        "ul",
        { class: "tags" },
        post.tags.map((t) => el("li", {}, `#${t}`)),
      ),
      el("div", { class: "post-actions" }, actions),
    ),
    commentsSection(id),
  );
  document.title = `${post.title} · Bitácora de Andrés`;
  view.querySelector("h1").setAttribute("tabindex", "-1");
  view.querySelector("h1").focus();
}

function commentsSection(id) {
  const list = state.comments[id] || [];
  const listBox = el("ul", { class: "comments" });
  const paint = () => {
    const items = state.comments[id] || [];
    listBox.replaceChildren(
      ...(items.length
        ? items.map((c) =>
            el(
              "li",
              {},
              el("p", { class: "meta" }, el("strong", {}, c.name), " · ", fmtDate(c.date)),
              el("p", {}, c.text),
            ),
          )
        : [el("li", { class: "empty" }, "Todavía no hay comentarios. ¡Sé el primero!")]),
    );
    heading.textContent = `Comentarios (${items.length})`;
  };
  const heading = el("h2", {}, `Comentarios (${list.length})`);

  const name = el("input", { id: "c-name", type: "text", maxlength: "40", required: true });
  const text = el("textarea", { id: "c-text", rows: "3", maxlength: "500", required: true });
  const errName = el("p", { class: "error" });
  const errText = el("p", { class: "error" });
  const form = el(
    "form",
    { novalidate: true, class: "comment-form" },
    el("div", { class: "field" }, el("label", { for: "c-name" }, "Nombre"), name, errName),
    el("div", { class: "field" }, el("label", { for: "c-text" }, "Comentario"), text, errText),
    el("button", { type: "submit", class: "btn btn-primary" }, "Comentar"),
  );
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    errName.textContent =
      name.value.trim().length < 2 ? "Escribe tu nombre (mínimo 2 caracteres)." : "";
    errText.textContent =
      text.value.trim().length < 5 ? "El comentario debe tener al menos 5 caracteres." : "";
    if (errName.textContent || errText.textContent) return;
    state.comments[id] ||= [];
    state.comments[id].push({
      name: name.value.trim(),
      text: text.value.trim(),
      date: new Date().toISOString(),
    });
    store.write(KEYS.comments, state.comments);
    form.reset();
    paint();
    toast("Comentario publicado");
  });

  paint();
  return el(
    "section",
    { class: "comments-section", "aria-label": "Comentarios" },
    heading,
    listBox,
    form,
  );
}

/* ---------- Enrutado por hash ---------- */
function route() {
  const match = location.hash.match(/^#\/post\/(.+)$/);
  const list = $("#view-list");
  const view = $("#view-post");
  if (match) {
    list.hidden = true;
    view.hidden = false;
    renderPost(decodeURIComponent(match[1]));
    window.scrollTo(0, 0);
  } else {
    view.hidden = true;
    list.hidden = false;
    document.title = "Bitácora de Andrés · Blog de Informática";
    renderList();
  }
}

/* ---------- Nueva entrada ---------- */
function setupNewPost() {
  const dlg = $("#dlg-new");
  const form = $("#form-new");
  const select = $("#f-category");
  select.append(...CATEGORIES.map((c) => el("option", { value: c }, c)));

  const setError = (field, msg) => {
    form.querySelector(`.error[data-for="${field}"]`).textContent = msg;
  };

  $("#btn-new").addEventListener("click", () => {
    form.reset();
    for (const f of ["title", "category", "content"]) setError(f, "");
    dlg.showModal();
    $("#f-title").focus();
  });
  $("#btn-cancel").addEventListener("click", () => dlg.close());

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const title = form.elements.title.value.trim();
    const category = form.elements.category.value;
    const content = form.elements.content.value.trim();
    setError("title", title.length < 5 ? "El título debe tener al menos 5 caracteres." : "");
    setError("category", category ? "" : "Elige una categoría.");
    setError(
      "content",
      content.length < 30 ? "El contenido debe tener al menos 30 caracteres." : "",
    );
    if (title.length < 5 || !category || content.length < 30) return;

    const tags = [
      ...new Set(
        form.elements.tags.value
          .split(",")
          .map((t) => t.trim().toLowerCase().replace(/\s+/g, "-"))
          .filter(Boolean),
      ),
    ].slice(0, 6);
    const post = {
      id: `user-${Date.now().toString(36)}`,
      title,
      category,
      tags,
      date: new Date().toISOString().slice(0, 10),
      content: content
        .split(/\n\s*\n/)
        .map((p) => p.trim())
        .filter(Boolean),
    };
    state.userPosts.unshift(post);
    const saved = store.write(KEYS.posts, state.userPosts);
    dlg.close();
    state.category = "Todas";
    state.query = "";
    $("#search").value = "";
    location.hash = `#/post/${encodeURIComponent(post.id)}`;
    toast(
      saved
        ? "Entrada publicada"
        : "No se pudo guardar en este navegador; la entrada se perderá al recargar.",
    );
  });
}

/* ---------- Tema claro/oscuro ---------- */
function setupTheme() {
  const saved = store.read(KEYS.theme, null);
  const prefersDark = window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches;
  const apply = (dark) => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    $("#btn-theme").setAttribute("aria-pressed", String(dark));
    $("#theme-icon").textContent = dark ? "☀️" : "🌙";
  };
  apply(saved ? saved === "dark" : prefersDark);
  $("#btn-theme").addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme !== "dark";
    apply(dark);
    store.write(KEYS.theme, dark ? "dark" : "light");
  });
}

/* ---------- Arranque ---------- */
document.addEventListener("DOMContentLoaded", () => {
  $("#year").textContent = new Date().getFullYear();
  setupTheme();
  setupNewPost();

  let debounce;
  $("#search").addEventListener("input", (e) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      state.query = e.target.value;
      state.visible = PAGE_SIZE;
      renderList();
    }, 150);
  });
  $("#btn-more").addEventListener("click", () => {
    state.visible += PAGE_SIZE;
    renderList();
  });

  window.addEventListener("hashchange", route);
  route();
});
