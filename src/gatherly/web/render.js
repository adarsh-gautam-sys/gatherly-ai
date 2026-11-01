import { money, decimal, dateLabel } from "./model.js";

/** Build text-only DOM nodes; untrusted event/model text never becomes markup. */
export function node(tag, text = "", className = "") {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

const get = (id) => document.getElementById(id);

function taskRow(task, change, prefix) {
  const row = node("div", "", "task");
  const checkbox = node("input");
  checkbox.type = "checkbox";
  checkbox.id = `${prefix}-${task.id}`;
  checkbox.checked = Boolean(task.completed);
  checkbox.addEventListener("change", () => change(task.id, checkbox.checked));
  const label = node("label");
  label.htmlFor = checkbox.id;
  label.append(
    node("span", task.title),
    node(
      "small",
      `${task.phase} · ${task.completed ? "Done" : task.status.replaceAll("_", " ")} · Priority ${task.priority}`,
    ),
  );
  row.append(
    checkbox,
    label,
    node("span", dateLabel(task.due_date), "task-date"),
  );
  return row;
}

/** Render overview and budget figures from the current deterministic plan. */
export function overview(plan, change) {
  get("plan-title").textContent = plan.request.name;
  get("plan-meta").textContent =
    `${plan.request.type[0].toUpperCase() + plan.request.type.slice(1)} · ${dateLabel(plan.request.date)} · ${plan.request.guests.toLocaleString()} guests${plan.request.region ? " · " + plan.request.region : ""}`;
  get("total").textContent = money(plan.budget.total, plan.request.currency);
  get("per-guest").textContent =
    `${money(plan.budget.per_guest, plan.request.currency)} per guest`;
  const tasks = [...plan.timeline]
    .filter((task) => !task.completed)
    .sort(
      (a, b) => a.due_date.localeCompare(b.due_date) || a.priority - b.priority,
    )
    .slice(0, 3);
  get("next-tasks").replaceChildren(
    ...tasks.map((task) => taskRow(task, change, "next")),
  );
  if (!tasks.length)
    get("next-tasks").append(
      node(
        "p",
        "Everything on your checklist is complete. Enjoy your celebration.",
      ),
    );
  get("completion").textContent =
    `${plan.timeline.filter((task) => task.completed).length} of ${plan.timeline.length} tasks complete`;
}

/** Render category allocations and controls without recalculating money. */
export function budgetView(plan) {
  const currency = plan.request.currency;
  get("what-if").value = decimal(plan.budget.total, currency);
  const slider = get("budget-slider");
  slider.max = Math.min(999999999, plan.budget.total * 2);
  slider.value = plan.budget.total;
  slider.setAttribute("aria-valuetext", money(plan.budget.total, currency));
  get("budget-lines").replaceChildren(
    ...plan.budget.lines.map((line) => {
      const row = node("tr");
      const category = node("th", line.category);
      category.scope = "row";
      category.append(node("small", line.rationale));
      row.append(
        category,
        node("td", `${line.percent}%`),
        node("td", money(line.amount, currency)),
      );
      return row;
    }),
  );
  get("budget-sum").textContent = money(plan.budget.total, currency);
  get("budget-warnings").replaceChildren(
    ...plan.budget.warnings.map((text) => node("p", text, "notice")),
  );
}

/** Lazily render the selected plan section. */
export function sectionView(section, plan, changeTask, changeVendor) {
  if (section === "budget") return budgetView(plan);
  if (section === "timeline") {
    const contents = [];
    const phases = new Set(plan.timeline.map((task) => task.phase));
    for (const phase of phases) {
      contents.push(node("h3", phase));
      contents.push(
        ...plan.timeline
          .filter((task) => task.phase === phase)
          .map((task) => taskRow(task, changeTask, "task")),
      );
    }
    get("timeline").replaceChildren(...contents);
  }
  if (section === "vendors")
    get("vendors").replaceChildren(
      ...plan.vendors.map((vendor, index) => {
        const block = node("section", "", "vendor");
        const head = node("div", "", "vendor-head");
        const text = node("div");
        text.append(
          node("h3", vendor.category),
          node(
            "p",
            `${money(vendor.allocated_amount, plan.request.currency)} allocated · Priority ${vendor.priority}`,
          ),
        );
        const label = node("label", `${vendor.category} status`);
        const select = node("select");
        select.id = `vendor-${index}`;
        for (const [value, title] of Object.entries({
          todo: "To do",
          contacted: "Contacted",
          booked: "Booked",
          not_needed: "Not needed",
        })) {
          const option = node("option", title);
          option.value = value;
          select.append(option);
        }
        select.value = vendor.status;
        select.addEventListener("change", () =>
          changeVendor(index, select.value),
        );
        label.append(select);
        head.append(text, label);
        const details = node("details");
        details.append(node("summary", "Questions and documents"));
        for (const [title, items] of [
          ["Questions to ask", vendor.questions],
          ["Documents to request", vendor.documents],
        ]) {
          details.append(node("h4", title));
          const list = node("ul");
          list.append(...items.map((item) => node("li", item)));
          details.append(list);
        }
        block.append(
          head,
          node("p", vendor.why),
          node(
            "p",
            `Typical booking lead: ${vendor.lead_time_days} days`,
            "muted",
          ),
          details,
        );
        return block;
      }),
    );
  if (section === "ideas") {
    get("concept").textContent = plan.ideas.concept_summary;
    const content = [];
    for (const theme of plan.ideas.themes) {
      const block = node("section", "", "theme");
      block.append(
        node("h3", theme.name),
        node("p", theme.mood),
        node("p", `Palette: ${theme.colour_palette.join(" · ")}`, "palette"),
        node("p", theme.decor_notes),
      );
      content.push(block);
    }
    for (const [key, title] of [
      ["menu", "Menu suggestions"],
      ["activities", "Activities"],
      ["personal_touches", "Personal touches"],
      ["saving_tips", "Ways to save"],
    ]) {
      content.push(node("h3", title));
      const list = node("ul");
      list.append(
        ...plan.ideas[key].map((item) =>
          node(
            "li",
            typeof item === "string"
              ? item
              : `${item.category}: ${item.suggestion}`,
          ),
        ),
      );
      content.push(list);
    }
    get("ideas").replaceChildren(...content);
  }
}
