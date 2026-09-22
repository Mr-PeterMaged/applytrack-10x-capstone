const $ = (selector) => document.querySelector(selector);
const state = {
  page: "overview",
  register: false,
  applications: [],
  offset: 0,
  searchVersion: 0,
  polling: null,
};
const labels = {
  saved: "Saved",
  applied: "Applied",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};
const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const prettyDate = (value) =>
  value
    ? new Date(`${value}T12:00:00`).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      })
    : "—";
let toastTimer;
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    $("#toast").hidden = true;
  }, 4500);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
    credentials: "same-origin",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (
      response.status === 401 &&
      !path.includes("/auth/login") &&
      !path.includes("/auth/register")
    )
      showAuth();
    const detail = Array.isArray(body.detail)
      ? body.detail.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join("; ")
      : body.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

function showAuth() {
  clearTimeout(state.polling);
  $("#workspace").hidden = true;
  $("#auth-view").hidden = false;
  if ($("#application-dialog").open) $("#application-dialog").close();
  $("#password").value = "";
}

async function enterWorkspace(user) {
  $("#user-email").textContent = user.email;
  $(".avatar").textContent = user.email[0].toUpperCase();
  $("#auth-view").hidden = true;
  $("#workspace").hidden = false;
  $("#password").value = "";
  await navigate("overview");
}

$("#auth-toggle").addEventListener("click", () => {
  state.register = !state.register;
  $("#auth-title").textContent = state.register
    ? "Your next chapter."
    : "Welcome back.";
  $("#auth-description").textContent = state.register
    ? "Create your own space to keep moving forward."
    : "Sign in and pick up where you left off.";
  $("#auth-submit").textContent = state.register
    ? "Create account ↗"
    : "Sign in ↗";
  $("#switch-copy").textContent = state.register
    ? "Already have an account?"
    : "New here?";
  $("#auth-toggle").textContent = state.register
    ? "Sign in"
    : "Create an account";
  $("#password").autocomplete = state.register
    ? "new-password"
    : "current-password";
  $("#auth-error").textContent = "";
});

$("#auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#auth-submit").disabled = true;
  $("#auth-error").textContent = "";
  try {
    const user = await api(
      `/api/auth/${state.register ? "register" : "login"}`,
      {
        method: "POST",
        body: JSON.stringify({
          email: $("#email").value,
          password: $("#password").value,
        }),
      },
    );
    await enterWorkspace(user);
  } catch (error) {
    $("#auth-error").textContent = error.message;
  } finally {
    $("#auth-submit").disabled = false;
  }
});

async function signOut() {
  try {
    await api("/api/auth/logout", { method: "POST" });
    showAuth();
  } catch (error) {
    toast(error.message);
  }
}
$("#logout").addEventListener("click", signOut);

async function seedDemo() {
  try {
    const result = await api("/api/demo/seed", { method: "POST" });
    toast(
      result.inserted
        ? "Eight fictional applications added. Take a look around."
        : "Demo data loads into an empty workspace. Your current applications were kept.",
    );
    await refresh();
  } catch (error) {
    toast(error.message);
  }
}
$("#seed-button").addEventListener("click", seedDemo);

const pages = {
  overview: [
    "LET'S KEEP THINGS MOVING",
    "Your next move.",
    "A little clarity for your application journey.",
  ],
  applications: [
    "EVERY OPPORTUNITY, IN ONE PLACE",
    "Your applications.",
    "Keep track of where you are and what comes next.",
  ],
  reports: [
    "LOOK BACK. MOVE FORWARD.",
    "Your progress, captured.",
    "A simple snapshot to reflect on, save, or share.",
  ],
};
async function navigate(page) {
  state.page = page;
  clearTimeout(state.polling);
  for (const name of Object.keys(pages))
    $(`#${name}-page`).hidden = name !== page;
  document.querySelectorAll("[data-page]").forEach((button) => {
    button.classList.toggle("active", button.dataset.page === page);
    button.setAttribute(
      "aria-current",
      button.dataset.page === page ? "page" : "false",
    );
  });
  $("#page-label").textContent = page[0].toUpperCase() + page.slice(1);
  [
    $("#page-eyebrow").textContent,
    $("#page-title").textContent,
    $("#page-description").textContent,
  ] = pages[page];
  $("#add-button").hidden = page === "reports";
  try {
    await refresh();
  } catch (error) {
    toast(error.message);
  }
}
document
  .querySelectorAll("[data-page]")
  .forEach((button) =>
    button.addEventListener("click", () => navigate(button.dataset.page)),
  );
$("#view-all").addEventListener("click", () => navigate("applications"));

function table(items, editable) {
  if (!items.length)
    return '<div class="empty"><strong>A little space for your next opportunity.</strong>Add an application to get started, or <button class="text-button" data-seed>load fictional demo data</button>.</div>';
  return `<table><thead><tr><th>COMPANY & ROLE</th><th>STATUS</th><th>APPLIED</th><th>FOLLOW-UP</th>${editable ? "<th>ACTIONS</th>" : ""}</tr></thead><tbody>${items.map((item) => `<tr><td><div class="table-company"><span class="company-icon">${escapeHTML(item.company[0].toUpperCase())}</span><div class="company-details"><strong>${escapeHTML(item.company)}</strong><small>${escapeHTML(item.role)}</small></div></div></td><td><span class="badge ${item.status}">${labels[item.status]}</span></td><td>${prettyDate(item.applied_on)}</td><td>${prettyDate(item.follow_up_on)}</td>${editable ? `<td><div class="row-actions"><button class="text-button" data-edit="${item.id}" aria-label="Edit ${escapeHTML(item.company)}">Edit</button><button class="text-button delete" data-delete="${item.id}" aria-label="Delete ${escapeHTML(item.company)}">Delete</button></div></td>` : ""}</tr>`).join("")}</tbody></table>`;
}

async function refresh() {
  const summary = await api("/api/summary");
  $("#nav-count").textContent = summary.total;
  if (state.page === "overview") {
    $("#stat-total").textContent = summary.total;
    $("#stat-interview").textContent = summary.by_status.interview;
    $("#stat-offer").textContent = summary.by_status.offer;
    $("#stat-overdue").textContent = summary.overdue;
    $("#response-rate").textContent = `${summary.response_rate}%`;
    $("#pipeline").innerHTML = Object.entries(labels)
      .map(
        ([key, label]) =>
          `<div class="pipeline-row" data-status="${key}"><span>${label}</span><div class="bar-track"><div class="bar-fill"></div></div><strong>${summary.by_status[key]}</strong></div>`,
      )
      .join("");
    document.querySelectorAll(".pipeline-row").forEach((row) => {
      row.querySelector(".bar-fill").style.width =
        `${summary.total ? Math.max(3, (summary.by_status[row.dataset.status] / summary.total) * 100) : 0}%`;
    });
    $("#followups").innerHTML = summary.follow_ups.length
      ? summary.follow_ups
          .map(
            (item) =>
              `<div class="followup-item"><span class="company-icon">${escapeHTML(item.company[0].toUpperCase())}</span><div class="company-details"><strong>${escapeHTML(item.company)}</strong><small>${escapeHTML(item.role)}</small></div><span class="date-pill ${item.follow_up_on < summary.as_of ? "overdue" : ""}">${item.follow_up_on < summary.as_of ? "Overdue · " : item.follow_up_on === summary.as_of ? "Today · " : ""}${prettyDate(item.follow_up_on)}</span></div>`,
          )
          .join("")
      : '<div class="empty"><strong>A clear horizon.</strong>No follow-ups due in the next seven days.</div>';
    const applications = await api("/api/applications?limit=5");
    $("#recent-table").innerHTML = table(applications.items, false);
  } else if (state.page === "applications") await loadApplications();
  else await loadReports();
}

async function loadApplications() {
  const version = ++state.searchVersion;
  const params = new URLSearchParams({
    q: $("#search").value,
    limit: "10",
    offset: String(state.offset),
  });
  if ($("#status-filter").value)
    params.set("status", $("#status-filter").value);
  const result = await api(`/api/applications?${params}`);
  if (version !== state.searchVersion) return;
  if (!result.items.length && state.offset > 0) {
    state.offset = Math.max(0, state.offset - 10);
    return loadApplications();
  }
  state.applications = result.items;
  $("#applications-table").innerHTML = result.total
    ? table(result.items, true)
    : '<div class="empty"><strong>No applications found.</strong>Add an application or try a different search.</div>';
  $("#results-count").textContent = result.total
    ? `${state.offset + 1}–${state.offset + result.items.length} of ${result.total} applications`
    : "0 applications";
  $("#previous").disabled = state.offset === 0;
  $("#next").disabled = state.offset + 10 >= result.total;
}
let searchTimer;
$("#search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.offset = 0;
    loadApplications().catch((e) => toast(e.message));
  }, 200);
});
$("#status-filter").addEventListener("change", () => {
  state.offset = 0;
  loadApplications().catch((e) => toast(e.message));
});
$("#previous").addEventListener("click", () => {
  state.offset = Math.max(0, state.offset - 10);
  loadApplications().catch((e) => toast(e.message));
});
$("#next").addEventListener("click", () => {
  state.offset += 10;
  loadApplications().catch((e) => toast(e.message));
});

function openApplication(item = null) {
  $("#application-form").reset();
  $("#application-error").textContent = "";
  $("#dialog-title").textContent = item
    ? "Edit application"
    : "New application";
  $("#application-id").value = item?.id ?? "";
  $("#company").value = item?.company ?? "";
  $("#role").value = item?.role ?? "";
  $("#application-status").value = item?.status ?? "saved";
  $("#applied-on").value = item?.applied_on ?? today();
  $("#follow-up-on").value = item?.follow_up_on ?? "";
  $("#notes").value = item?.notes ?? "";
  $("#application-dialog").showModal();
  $("#company").focus();
}
$("#add-button").addEventListener("click", () => openApplication());
for (const id of ["#close-dialog", "#cancel-dialog"])
  $(id).addEventListener("click", () => $("#application-dialog").close());
$("#application-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#save-application").disabled = true;
  $("#application-error").textContent = "";
  const body = Object.fromEntries(new FormData(event.target));
  body.follow_up_on ||= null;
  const id = $("#application-id").value;
  try {
    await api(`/api/applications${id ? `/${id}` : ""}`, {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(body),
    });
    $("#application-dialog").close();
    toast(id ? "Application updated." : "A new possibility, saved.");
    await refresh();
  } catch (error) {
    $("#application-error").textContent = error.message;
  } finally {
    $("#save-application").disabled = false;
  }
});
document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  if (button.hasAttribute("data-seed")) return seedDemo();
  if (button.dataset.edit)
    return openApplication(
      state.applications.find(
        (item) => item.id === Number(button.dataset.edit),
      ),
    );
  if (button.dataset.delete) {
    const item = state.applications.find(
      (row) => row.id === Number(button.dataset.delete),
    );
    if (
      !confirm(
        `Delete the application at ${item.company}? This cannot be undone.`,
      )
    )
      return;
    try {
      await api(`/api/applications/${item.id}`, { method: "DELETE" });
      toast("Application deleted.");
      await refresh();
    } catch (error) {
      toast(error.message);
    }
  }
});

async function loadReports() {
  clearTimeout(state.polling);
  const result = await api("/api/reports");
  $("#reports-list").innerHTML = result.items.length
    ? result.items
        .map(
          (job) =>
            `<div class="report-row"><div><strong>Application progress report</strong><small>${escapeHTML(new Date(job.created_at.replace(" ", "T") + "Z").toLocaleString())}</small>${job.error ? `<small>${escapeHTML(job.error)}</small>` : ""}</div><div><span class="badge ${job.status}">${job.status[0].toUpperCase() + job.status.slice(1)}</span>${job.status === "completed" ? `<a class="text-button" href="/api/reports/${job.id}/download">Download PDF ↧</a>` : ""}</div></div>`,
        )
        .join("")
    : '<div class="empty"><strong>Your story is still taking shape.</strong>Create a report to capture your progress.</div>';
  if (
    state.page === "reports" &&
    result.items.some((job) => ["queued", "running"].includes(job.status))
  )
    state.polling = setTimeout(
      () => loadReports().catch((e) => toast(e.message)),
      1200,
    );
}
$("#generate-report").addEventListener("click", async () => {
  $("#generate-report").disabled = true;
  try {
    await api("/api/reports", { method: "POST" });
    toast("Your report is being prepared.");
    await loadReports();
  } catch (error) {
    toast(error.message);
  } finally {
    $("#generate-report").disabled = false;
  }
});

// Compact controls stay available when the mobile layout hides the sidebar footer.
const mobileControls = document.createElement("div");
mobileControls.className = "mobile-controls";
const mobileDemo = document.createElement("button");
mobileDemo.className = "text-button";
mobileDemo.textContent = "Demo";
mobileDemo.addEventListener("click", seedDemo);
const mobileLogout = document.createElement("button");
mobileLogout.className = "text-button";
mobileLogout.textContent = "Sign out";
mobileLogout.addEventListener("click", signOut);
mobileControls.append(mobileDemo, mobileLogout);
$(".topbar").append(mobileControls);
api("/api/auth/me")
  .then(enterWorkspace)
  .catch(() => showAuth());
