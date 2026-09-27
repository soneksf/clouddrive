/* CloudDrive — веб-клієнт (етап 3): логіка кабінету користувача.
 * Відповідає класу FileListController десктоп-версії.
 */
(() => {
  "use strict";

  if (!Api.getToken()) {
    window.location.replace("login.html");
    return;
  }

  /* Опис стовпців таблиці. Стовпець «Назва» приховати не можна (вимога завдання). */
  const COLUMNS = [
    { key: "name", title: "Назва", sort: "name", hideable: false },
    { key: "extension", title: "Тип", sort: "extension", hideable: true },
    { key: "size", title: "Розмір", sort: null, hideable: true },
    { key: "created_at", title: "Створено", sort: "created_at", hideable: true },
    { key: "modified_at", title: "Змінено", sort: "modified_at", hideable: true },
    { key: "uploaded_by", title: "Хто завантажив", sort: "uploaded_by", hideable: true },
    { key: "modified_by", title: "Хто редагував", sort: "modified_by", hideable: true }
  ];

  const VARIANT_EXTENSIONS = [".xml", ".png"];

  /* Стан подання: поле й напрям сортування, фільтр, приховані стовпці.
   * За замовчуванням — операція варіанта 1: дата створення, спадання. */
  const state = {
    files: [],
    sortField: "created_at",
    sortOrder: "desc",
    filter: "all",
    hidden: new Set(JSON.parse(localStorage.getItem("clouddrive.hidden") || "[]")),
    selectedId: null
  };

  const el = (id) => document.getElementById(id);
  const statusBar = el("status");

  function setStatus(text) { statusBar.textContent = text; }

  function humanSize(bytes) {
    const units = ["Б", "КБ", "МБ", "ГБ"];
    let size = bytes;
    for (let i = 0; i < units.length; i += 1) {
      if (size < 1024 || i === units.length - 1) {
        return (i === 0 ? size.toFixed(0) : size.toFixed(1)) + " " + units[i];
      }
      size /= 1024;
    }
    return bytes + " Б";
  }

  function formatDate(iso) {
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return pad(d.getDate()) + "." + pad(d.getMonth() + 1) + "." + d.getFullYear() +
           " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
  }

  function cellValue(file, key) {
    if (key === "size") return humanSize(file.size);
    if (key === "created_at" || key === "modified_at") return formatDate(file[key]);
    return file[key];
  }

  /* ------------------------------------------------------------- таблиця */
  function renderHead() {
    const row = el("head-row");
    row.innerHTML = "";
    COLUMNS.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col.title;
      th.dataset.key = col.key;
      if (col.sort) {
        if (state.sortField === col.sort) {
          th.textContent = col.title + (state.sortOrder === "asc" ? " ▲" : " ▼");
        }
        th.addEventListener("click", () => toggleSort(col.sort));
      } else {
        th.classList.add("no-sort");
      }
      th.hidden = state.hidden.has(col.key);
      row.appendChild(th);
    });
  }

  function renderBody() {
    const body = el("files-body");
    body.innerHTML = "";
    if (state.files.length === 0) {
      body.innerHTML = '<tr><td class="empty" colspan="7">Файлів немає — ' +
                       'завантажте перший або перетягніть його сюди</td></tr>';
      return;
    }
    state.files.forEach((file) => {
      const tr = document.createElement("tr");
      tr.dataset.id = file.id;
      if (file.id === state.selectedId) tr.classList.add("selected");
      COLUMNS.forEach((col) => {
        const td = document.createElement("td");
        td.textContent = cellValue(file, col.key);
        td.hidden = state.hidden.has(col.key);
        tr.appendChild(td);
      });
      tr.addEventListener("click", () => selectFile(file));
      body.appendChild(tr);
    });
  }

  function renderSortState() {
    const column = COLUMNS.find((c) => c.sort === state.sortField);
    const arrow = state.sortOrder === "asc" ? "▲" : "▼";
    el("sort-state").textContent =
      "Сортування: " + (column ? column.title : "—") + " " + arrow +
      "  |  файлів: " + state.files.length;
  }

  function render() {
    renderHead();
    renderBody();
    renderSortState();
    const hasSelection = state.selectedId !== null;
    el("btn-download").disabled = !hasSelection;
    el("btn-delete").disabled = !hasSelection;
  }

  /* ------------------------------------------------- операція варіанта 1 */
  function toggleSort(field) {
    if (state.sortField === field) {
      state.sortOrder = state.sortOrder === "asc" ? "desc" : "asc";
    } else {
      state.sortField = field;
      state.sortOrder = "asc";
    }
    reload();
  }

  async function reload() {
    try {
      state.files = await Api.getFiles(state.sortField, state.sortOrder, state.filter);
      if (!state.files.some((f) => f.id === state.selectedId)) {
        state.selectedId = null;
        clearPreview();
      }
      render();
      setStatus("Список оновлено");
    } catch (err) {
      setStatus("Помилка: " + err.message);
    }
  }

  /* ------------------------------------------------------------ перегляд */
  function clearPreview() {
    el("preview-title").textContent = "Перегляд вмісту";
    el("preview-body").className = "placeholder";
    el("preview-body").textContent =
      "Клікніть по файлу .xml або .png, щоб побачити вміст";
  }

  async function selectFile(file) {
    state.selectedId = file.id;
    render();

    const ext = (file.extension || "").toLowerCase();
    el("preview-title").textContent = "Перегляд: " + file.name;
    const bodyBox = el("preview-body");

    if (VARIANT_EXTENSIONS.indexOf(ext) === -1) {
      bodyBox.className = "placeholder";
      bodyBox.textContent = "Формат " + (ext || "—") + " не передбачено варіантом 1. " +
        "Переглядати можна лише .xml (як текст) і .png (як зображення).";
      return;
    }

    bodyBox.className = "";
    bodyBox.textContent = "Завантаження вмісту…";
    try {
      const blob = await Api.content(file.id);
      bodyBox.innerHTML = "";
      if (ext === ".xml") {
        // .xml показується саме як текст, а не як відрендерена розмітка
        const pre = document.createElement("pre");
        pre.textContent = await blob.text();
        bodyBox.appendChild(pre);
      } else {
        const img = document.createElement("img");
        img.src = URL.createObjectURL(blob);
        img.alt = file.name;
        bodyBox.appendChild(img);
      }
    } catch (err) {
      bodyBox.className = "placeholder";
      bodyBox.textContent = "Не вдалося отримати вміст: " + err.message;
      if (err.message.indexOf("404") === 0) reload();
    }
  }

  /* --------------------------------------------------------------- дії */
  async function uploadFiles(fileList) {
    const files = Array.from(fileList || []);
    if (files.length === 0) return;
    let sent = 0;
    const errors = [];
    for (const file of files) {
      setStatus("Завантаження: " + file.name + "…");
      try {
        await Api.upload(file);
        sent += 1;
      } catch (err) {
        errors.push(file.name + ": " + err.message);
      }
    }
    await reload();
    setStatus(errors.length
      ? "Завантажено: " + sent + ". Помилки: " + errors.join("; ")
      : "Завантажено файлів: " + sent);
  }

  async function downloadSelected() {
    const file = state.files.find((f) => f.id === state.selectedId);
    if (!file) return;
    try {
      const blob = await Api.content(file.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = file.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setStatus("Файл «" + file.name + "» збережено у теку завантажень браузера");
    } catch (err) {
      setStatus("Помилка вивантаження: " + err.message);
    }
  }

  async function deleteSelected() {
    const file = state.files.find((f) => f.id === state.selectedId);
    if (!file) return;
    if (!window.confirm("Видалити файл «" + file.name + "»?")) return;
    try {
      await Api.remove(file.id);
      state.selectedId = null;
      clearPreview();
      await reload();
      setStatus("Файл «" + file.name + "» видалено");
    } catch (err) {
      setStatus("Помилка видалення: " + err.message);
    }
  }

  /* ------------------------------------------------ керування стовпцями */
  function buildColumnsMenu() {
    const box = el("columns-items");
    box.innerHTML = "";
    COLUMNS.forEach((col) => {
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = !state.hidden.has(col.key);
      checkbox.disabled = !col.hideable;   // «Назву» приховати не можна
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) state.hidden.delete(col.key);
        else state.hidden.add(col.key);
        localStorage.setItem("clouddrive.hidden", JSON.stringify(Array.from(state.hidden)));
        render();
      });
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(col.title));
      box.appendChild(label);
    });
  }

  /* --------------------------------------------------------- підключення */
  function bindEvents() {
    el("btn-upload").addEventListener("click", () => el("file-input").click());
    el("file-input").addEventListener("change", (event) => {
      uploadFiles(event.target.files);
      event.target.value = "";
    });
    el("btn-download").addEventListener("click", downloadSelected);
    el("btn-delete").addEventListener("click", deleteSelected);
    el("btn-refresh").addEventListener("click", reload);

    el("filter").addEventListener("change", (event) => {
      state.filter = event.target.value;
      reload();
    });

    const menu = el("columns-menu");
    el("btn-columns").addEventListener("click", (event) => {
      event.stopPropagation();
      menu.classList.toggle("open");
    });
    document.addEventListener("click", (event) => {
      if (!menu.contains(event.target)) menu.classList.remove("open");
    });

    el("btn-logout").addEventListener("click", () => {
      Api.logout();
      window.location.href = "login.html";
    });

    /* drag-and-drop завантаження (бонусна вимога) */
    const dropZone = el("table-wrap");
    ["dragenter", "dragover"].forEach((name) => {
      dropZone.addEventListener(name, (event) => {
        event.preventDefault();
        dropZone.classList.add("dragover");
      });
    });
    ["dragleave", "drop"].forEach((name) => {
      dropZone.addEventListener(name, (event) => {
        event.preventDefault();
        dropZone.classList.remove("dragover");
      });
    });
    dropZone.addEventListener("drop", (event) => {
      uploadFiles(event.dataTransfer.files);
    });
    // браузер не має відкривати файл, якщо його кинули повз таблицю
    window.addEventListener("dragover", (event) => event.preventDefault());
    window.addEventListener("drop", (event) => event.preventDefault());
  }

  function init() {
    const user = Api.getUser();
    el("user-name").textContent = user ? user.full_name || user.login : "";
    buildColumnsMenu();
    bindEvents();
    reload();
  }

  init();
})();
