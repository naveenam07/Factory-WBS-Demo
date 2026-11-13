(function () {
  "use strict";

  let routes = null;

  function loadRoutes() {
    routes = routes || fetch("/static/api-routes.json").then((response) => response.json());
    return routes;
  }

  async function api(name, params, options) {
    const all = await loadRoutes();
    const path = all[name].replace(/\{(\w+)\}/g, (_, key) => encodeURIComponent(params[key]));
    const response = await fetch(path, options);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const traceId = body.trace_id || response.headers.get("X-Trace-Id") || "unknown";
      const error = new Error(
        `Something went wrong (${response.status}). Reference: ${traceId}. ` +
          "Please contact the help desk."
      );
      error.isApiError = true;
      throw error;
    }
    return body;
  }

  function postJson(payload) {
    return {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    };
  }

  function showBanner(kind, message) {
    const banner = document.getElementById("banner");
    banner.className = `banner banner-${kind}`;
    banner.textContent = message;
    banner.hidden = false;
    banner.scrollIntoView({ block: "center" });
  }

  function showError(error) {
    showBanner("error", error.isApiError ? error.message : "Something went wrong. Please contact the help desk.");
  }

  function money(value) {
    return value == null ? "-" : `$${Number(value).toFixed(2)}`;
  }

  function row(cells) {
    const tr = document.createElement("tr");
    for (const cell of cells) {
      const td = document.createElement("td");
      if (cell instanceof Node) {
        td.appendChild(cell);
      } else {
        td.textContent = cell;
      }
      tr.appendChild(td);
    }
    return tr;
  }

  async function initClients(section) {
    const advisorId = section.dataset.advisorId;
    const tbody = document.getElementById("client-rows");
    try {
      const data = await api("accounts", { advisor_id: advisorId });
      document.getElementById("advisor-name").textContent = `${data.advisor_name} (${data.advisor_id})`;
      tbody.replaceChildren();
      for (const account of data.accounts) {
        const href = `/accounts/${encodeURIComponent(account.account_id)}?advisor_id=${encodeURIComponent(advisorId)}`;
        const link = document.createElement("a");
        link.href = href;
        link.textContent = "Open";
        const tr = row([account.client_name, account.account_type || "-", account.last4, link]);
        tr.className = "clickable";
        tr.addEventListener("click", () => { window.location.href = href; });
        tbody.appendChild(tr);
      }
    } catch (error) {
      tbody.replaceChildren();
      showError(error);
    }
  }

  async function loadAccount(accountId, advisorId) {
    const data = await api("accounts", { advisor_id: advisorId });
    const account = data.accounts.find((a) => a.account_id === accountId);
    if (account) {
      document.getElementById("account-title").textContent = `${account.client_name} (${account.account_id})`;
      const details = document.getElementById("account-details");
      details.replaceChildren();
      for (const [label, value] of [
        ["Account type", account.account_type || "-"],
        ["Last 4", account.last4],
        ["Cash balance", money(account.cash_balance)],
      ]) {
        const dt = document.createElement("dt");
        dt.textContent = label;
        const dd = document.createElement("dd");
        dd.textContent = value;
        details.append(dt, dd);
      }
    }
    const select = document.getElementById("to-account");
    select.replaceChildren();
    for (const other of data.accounts.filter((a) => a.account_id !== accountId)) {
      const option = document.createElement("option");
      option.value = other.account_id;
      option.textContent = `${other.client_name} (...${other.last4})`;
      select.appendChild(option);
    }
  }

  async function loadPositions(accountId) {
    const tbody = document.getElementById("positions-rows");
    const data = await api("positions", { account_id: accountId });
    tbody.replaceChildren();
    for (const p of data.positions) {
      tbody.appendChild(row([p.symbol, String(p.quantity), money(p.cost_basis), money(p.price), money(p.market_value)]));
    }
  }

  function initAccount(section) {
    const accountId = section.dataset.accountId;
    const advisorId = section.dataset.advisorId;

    loadAccount(accountId, advisorId).catch(showError);
    loadPositions(accountId).catch((error) => {
      document.getElementById("positions-rows").replaceChildren();
      showError(error);
    });

    document.getElementById("trade-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.target);
      try {
        const result = await api("orders", {}, postJson({
          advisor_id: advisorId,
          account_id: accountId,
          symbol: form.get("symbol").trim().toUpperCase(),
          side: form.get("side"),
          quantity: Number(form.get("quantity")),
        }));
        showBanner("success", `Trade placed. Confirmation number: ${result.confirmation_number}`);
      } catch (error) {
        showError(error);
      }
    });

    document.getElementById("transfer-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.target);
      try {
        const result = await api("transfers", {}, postJson({
          advisor_id: advisorId,
          from_account_id: accountId,
          to_account_id: form.get("to_account_id"),
          amount: Number(form.get("amount")),
        }));
        showBanner("success", `Money moved. Confirmation number: ${result.confirmation_number}`);
        loadAccount(accountId, advisorId).catch(showError);
      } catch (error) {
        showError(error);
      }
    });
  }

  const page = document.querySelector("[data-page]");
  if (page && page.dataset.page === "clients") {
    initClients(page);
  } else if (page && page.dataset.page === "account") {
    initAccount(page);
  }
})();
