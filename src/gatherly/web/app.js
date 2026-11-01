import { parseMoney, money, decimal, withBudget } from "./model.js";
import { node, overview, sectionView } from "./render.js";

const get = (id) => document.getElementById(id);
let plan = null;
let activeSection = "budget";
let busy = false;
let ideasStale = false;
const SECTIONS = ["budget", "timeline", "vendors", "ideas"];
const MAX_IMPORT_BYTES = 262144;

function announce(message) {
  get("status").textContent = message;
}
function feedback(message) {
  get("feedback").textContent = message;
  get("feedback").hidden = false;
  get("feedback").focus();
}

async function request(path, body, download = false) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 16000);
  try {
    const response = await fetch(`/api/v1/plans${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) {
      let message =
        response.status === 429
          ? `Too many requests. Try again in ${response.headers.get("Retry-After") || 60} seconds.`
          : "The request could not be completed. Your current plan is unchanged. Try again.";
      const data = await response.json().catch(() => null);
      if (data?.code === "validation_error")
        message =
          "Some event or plan details are invalid. Check the fields, future date and JSON file, then try again.";
      throw new Error(message);
    }
    return download ? await response.blob() : await response.json();
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error(
        "The request took too long. Your details are still here. Please try again.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "Could not reach Gatherly. Check your connection and try again.",
      );
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function operation(message, action) {
  if (busy) return;
  busy = true;
  get("feedback").hidden = true;
  announce(message);
  document.body.classList.add("is-busy");
  get("results").setAttribute("aria-busy", "true");
  get("event-form").setAttribute("aria-busy", "true");
  const controls = [
    ...document.querySelectorAll("button, input, select, textarea"),
  ];
  controls.forEach((control) => (control.disabled = true));
  try {
    await action();
  } catch (error) {
    announce("");
    feedback(error.message || "Please try again.");
  } finally {
    busy = false;
    controls.forEach((control) => (control.disabled = false));
    document.body.classList.remove("is-busy");
    get("results").setAttribute("aria-busy", "false");
    get("event-form").setAttribute("aria-busy", "false");
  }
}

function showValidation(errors) {
  document.querySelectorAll("[aria-invalid]").forEach((field) => {
    field.removeAttribute("aria-invalid");
    if (field.dataset.hint)
      field.setAttribute("aria-describedby", field.dataset.hint);
    else field.removeAttribute("aria-describedby");
  });
  document.querySelectorAll(".field-error").forEach((field) => field.remove());
  get("error-list").replaceChildren();
  for (const [id, message] of errors) {
    const field = get(id);
    const item = node("li");
    const link = node("a", message);
    link.href = `#${id}`;
    link.addEventListener("click", (event) => {
      event.preventDefault();
      field.focus();
    });
    item.append(link);
    get("error-list").append(item);
    field.setAttribute("aria-invalid", "true");
    const hint = node("small", message, "field-error");
    hint.id = `${id}-error`;
    field.closest("label").after(hint);
    field.setAttribute(
      "aria-describedby",
      [field.dataset.hint || "", hint.id].join(" ").trim(),
    );
  }
  get("errors").hidden = !errors.length;
  if (errors.length) get("errors").focus();
}

function readEvent() {
  const form = get("event-form");
  const data = Object.fromEntries(new FormData(form));
  const errors = [];
  if (!data.type)
    errors.push([
      "occasion-wedding",
      "Choose an occasion: wedding, birthday or community.",
    ]);
  if (!String(data.name).trim())
    errors.push(["name", "Enter a name for your event."]);
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  if (!data.date || data.date <= today)
    errors.push(["date", "Choose an event date after today."]);
  const guests = Number(data.guests);
  if (
    !/^\d+$/.test(data.guests) ||
    !Number.isInteger(guests) ||
    guests < 1 ||
    guests > 5000
  )
    errors.push(["guests", "Enter a whole guest count from 1 to 5,000."]);
  let budget = 0;
  try {
    budget = parseMoney(data.budget, data.currency);
  } catch (error) {
    errors.push(["budget", error.message]);
  }
  showValidation(errors);
  if (errors.length) return null;
  return { ...data, guests, budget };
}

function taskChanged(id, completed) {
  plan.timeline = plan.timeline.map((task) =>
    task.id === id ? { ...task, completed } : task,
  );
  const task = plan.timeline.find((item) => item.id === id);
  for (const prefix of ["next", "task"]) {
    const checkbox = get(`${prefix}-${id}`);
    if (!checkbox) continue;
    checkbox.checked = completed;
    checkbox.closest(".task").querySelector("small").textContent =
      `${task.phase} · ${completed ? "Done" : task.status.replaceAll("_", " ")} · Priority ${task.priority}`;
  }
  get("completion").textContent =
    `${plan.timeline.filter((item) => item.completed).length} of ${plan.timeline.length} tasks complete`;
  announce(completed ? "Task marked complete." : "Task reopened.");
}

function render() {
  overview(plan, taskChanged);
  sectionView(activeSection, plan, taskChanged, (index, status) => {
    plan.vendors[index].status = status;
    announce(`Vendor status updated to ${status.replaceAll("_", " ")}.`);
  });
  get("ai-notice").textContent = ideasStale
    ? "Budget updated. Your existing ideas may reflect the previous budget. Refresh ideas when you are ready."
    : plan.ai_status === "unavailable"
      ? "Your full plan is ready. AI ideas are unavailable, so these are template suggestions you can use now."
      : "Your full plan is ready, with creative ideas from Gemini. Review suggestions for your event and dietary needs.";
}

function showPlan() {
  get("intake").hidden = true;
  get("results").hidden = false;
  render();
  get("plan-title").focus();
}

function selectTab(section, focus = false) {
  activeSection = section;
  for (const key of SECTIONS) {
    const selected = key === section;
    get(`tab-${key}`).setAttribute("aria-selected", String(selected));
    get(`tab-${key}`).tabIndex = selected ? 0 : -1;
    get(`panel-${key}`).hidden = !selected;
  }
  if (plan) render();
  if (focus) get(`tab-${section}`).focus();
}

get("event-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const data = readEvent();
  if (!data) return;
  operation("Creating your plan. This can take up to 15 seconds.", async () => {
    const result = await request("", data);
    plan = result;
    ideasStale = false;
    selectTab("budget");
    showPlan();
    announce("Your plan is ready.");
  });
});
for (const section of SECTIONS) {
  get(`tab-${section}`).addEventListener("click", () => selectTab(section));
  get(`tab-${section}`).addEventListener("keydown", (event) => {
    const index = SECTIONS.indexOf(section);
    const next = {
      ArrowRight: (index + 1) % 4,
      ArrowLeft: (index + 3) % 4,
      Home: 0,
      End: 3,
    }[event.key];
    if (next !== undefined) {
      event.preventDefault();
      selectTab(SECTIONS[next], true);
    }
  });
}
get("edit").addEventListener("click", () => {
  for (const [name, value] of Object.entries(plan.request)) {
    if (name === "type") {
      document.querySelector(`input[name="type"][value="${value}"]`).checked =
        true;
    } else {
      const field = get("event-form").elements.namedItem(name);
      if (field)
        field.value =
          name === "budget" ? decimal(value, plan.request.currency) : value;
    }
  }
  get("intake").hidden = false;
  get("results").hidden = true;
  get("cancel-edit").hidden = false;
  get("name").focus();
  announce(
    "Editing event details creates a new plan. Return to keep your current plan.",
  );
});
get("cancel-edit").addEventListener("click", () => {
  showValidation([]);
  showPlan();
  announce("Current plan kept.");
});
get("budget-slider").addEventListener("input", (event) => {
  const amount = Number(event.target.value);
  get("what-if").value = decimal(amount, plan.request.currency);
  event.target.setAttribute(
    "aria-valuetext",
    money(amount, plan.request.currency),
  );
});
get("budget-form").addEventListener("submit", (event) => {
  event.preventDefault();
  let amount;
  try {
    amount = parseMoney(get("what-if").value, plan.request.currency);
  } catch (error) {
    feedback(error.message);
    return;
  }
  operation("Updating your budget.", async () => {
    const result = await request("/budget", {
      ...plan.request,
      budget: amount,
    });
    plan = withBudget(plan, result);
    ideasStale = true;
    render();
    get("budget-lines").classList.remove("updated");
    requestAnimationFrame(() => get("budget-lines").classList.add("updated"));
    announce(
      `Budget updated to ${money(amount, plan.request.currency)}. Vendor progress kept.`,
    );
  });
});
get("refresh").addEventListener("click", () =>
  operation("Refreshing creative ideas.", async () => {
    const result = await request("/ideas", plan.request);
    plan = { ...plan, ...result };
    ideasStale = false;
    render();
    announce("Ideas refreshed.");
  }),
);
get("refine-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const instruction = get("instruction").value.trim();
  if (!instruction) {
    feedback("Describe the change you would like to make.");
    return;
  }
  const section = get("refine-section").value;
  const change = { instruction };
  if (section !== "all") change.sections = [section];
  operation("Refining your ideas.", async () => {
    const result = await request("/refine", { plan, change });
    plan = result;
    ideasStale = false;
    render();
    announce(
      "Ideas refined. Your checklist and vendor progress have been kept.",
    );
  });
});
document.querySelectorAll("[data-export]").forEach((button) =>
  button.addEventListener("click", () =>
    operation("Preparing your export.", async () => {
      const format = button.dataset.export;
      const blob = await request(`/export?format=${format}`, plan, true);
      const url = URL.createObjectURL(blob);
      const link = node("a");
      link.href = url;
      link.download = `gatherly-plan.${format}`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      announce("Export ready. Keep a JSON copy to reopen your plan.");
    }),
  ),
);
get("import").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) return;
  operation("Checking your saved plan.", async () => {
    if (file.size > MAX_IMPORT_BYTES)
      throw new Error("Choose a Gatherly JSON export smaller than 256 KiB.");
    let candidate;
    try {
      candidate = JSON.parse(await file.text());
    } catch {
      throw new Error(
        "This file is not valid JSON. Choose a Gatherly JSON export.",
      );
    }
    const checked = await request("/export?format=json", candidate);
    plan = checked;
    ideasStale = false;
    selectTab("budget");
    showPlan();
    announce("Saved plan opened, including checklist and vendor progress.");
  });
  event.target.value = "";
});
get("print").addEventListener("click", () => {
  for (const section of SECTIONS)
    sectionView(
      section,
      plan,
      taskChanged,
      (index, status) => (plan.vendors[index].status = status),
    );
  document
    .querySelectorAll("#results details")
    .forEach((details) => (details.open = true));
  window.print();
});
for (const id of ["date", "budget"]) get(id).dataset.hint = `${id}-hint`;
const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
get("date").min =
  `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, "0")}-${String(tomorrow.getDate()).padStart(2, "0")}`;
