/* CloudDrive — веб-клієнт (етап 3).
 * Api — аналог класу RestApiClient десктоп-версії: єдине місце,
 * яке знає про HTTP, адреси ендпоінтів і токен сеансу.
 */
const Api = (() => {
  const TOKEN_KEY = "clouddrive.token";
  const USER_KEY = "clouddrive.user";

  const getToken = () => localStorage.getItem(TOKEN_KEY);
  const getUser = () => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch (err) {
      return null;
    }
  };

  function authHeaders() {
    const token = getToken();
    return token ? { Authorization: "Bearer " + token } : {};
  }

  async function handle(response) {
    if (response.status === 401) {
      logout();
      window.location.href = "login.html";
      throw new Error("Сеанс завершено, увійдіть повторно");
    }
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const data = await response.json();
        detail = data.detail || detail;
      } catch (err) { /* тіло не JSON — лишаємо статус */ }
      throw new Error(response.status + ": " + detail);
    }
    return response;
  }

  async function login(login, password) {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login, password })
    });
    if (response.status === 401) {
      throw new Error("Невірний логін або пароль");
    }
    await handle(response);
    const data = await response.json();
    localStorage.setItem(TOKEN_KEY, data.token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    return data.user;
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  /* Список файлів. Сортування й фільтрація виконуються на сервері тим самим
   * класом SortFilterService, що й для десктоп-клієнта. */
  async function getFiles(sort, order, type) {
    const params = new URLSearchParams({ sort, order, type });
    const response = await fetch("/api/files?" + params.toString(), { headers: authHeaders() });
    await handle(response);
    return response.json();
  }

  async function upload(file) {
    const form = new FormData();
    form.append("file", file, file.name);
    const response = await fetch("/api/files", {
      method: "POST",
      headers: authHeaders(),
      body: form
    });
    await handle(response);
    return response.json();
  }

  async function content(fileId) {
    const response = await fetch("/api/files/" + fileId + "/content", { headers: authHeaders() });
    await handle(response);
    return response.blob();
  }

  async function remove(fileId) {
    const response = await fetch("/api/files/" + fileId, {
      method: "DELETE",
      headers: authHeaders()
    });
    await handle(response);
    return response.json();
  }

  return { getToken, getUser, login, logout, getFiles, upload, content, remove };
})();
