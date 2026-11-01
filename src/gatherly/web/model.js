/** Convert display amounts into exact integer minor units without floating arithmetic. */
export function parseMoney(value, currency) {
  const digits = currency === "JPY" ? 0 : 2;
  const pattern = digits ? /^(\d+)(?:\.(\d{1,2}))?$/ : /^(\d+)$/;
  const match = String(value).trim().match(pattern);
  if (!match)
    throw new Error(
      digits
        ? "Enter an amount with at most two decimal places."
        : "Enter a whole yen amount.",
    );
  const amount =
    BigInt(match[1]) * (digits ? 100n : 1n) +
    BigInt((match[2] || "").padEnd(digits, "0") || "0");
  if (amount < 1n || amount >= 1000000000n)
    throw new Error("Enter a positive budget below 1,000,000,000 minor units.");
  return Number(amount);
}

/** Format integer minor units without losing a cent. */
export function money(amount, currency) {
  const divisor = currency === "JPY" ? 1 : 100;
  const whole = Math.floor(amount / divisor).toLocaleString("en");
  return `${currency} ${whole}${divisor === 1 ? "" : "." + String(amount % 100).padStart(2, "0")}`;
}

/** Return an editable decimal string, independent of locale grouping. */
export function decimal(amount, currency) {
  return currency === "JPY"
    ? String(amount)
    : `${Math.floor(amount / 100)}.${String(amount % 100).padStart(2, "0")}`;
}

/** Render a calendar date in UTC so local zones cannot shift the day. */
export function dateLabel(date) {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${date}T12:00:00Z`));
}

/** Reconcile a deterministic what-if response with client-held vendor progress. */
export function withBudget(plan, budget) {
  const amounts = new Map(
    budget.lines.map((line) => [line.category, line.amount]),
  );
  return {
    ...plan,
    request: { ...plan.request, budget: budget.total },
    budget,
    vendors: plan.vendors.map((vendor) => ({
      ...vendor,
      allocated_amount: amounts.get(vendor.linked_category),
    })),
  };
}
