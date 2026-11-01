import { test } from "node:test";
import assert from "node:assert/strict";
import {
  parseMoney,
  money,
  decimal,
  withBudget,
  dateLabel,
} from "../../src/gatherly/web/model.js";

test("money conversion preserves every minor unit without accepting exponential notation", () => {
  for (const value of [1, 99, 100, 123456, 999999999])
    assert.equal(parseMoney(decimal(value, "INR"), "INR"), value);
  assert.equal(money(123456, "INR"), "INR 1,234.56");
  assert.equal(parseMoney("123", "JPY"), 123);
  for (const value of [
    "0",
    "-1",
    "1e5",
    "Infinity",
    "1.001",
    "1,000",
    "10000000.00",
  ])
    assert.throws(() => parseMoney(value, "INR"));
  assert.throws(() => parseMoney("1.2", "JPY"));
  assert.equal(dateLabel("2099-06-01"), "Jun 1, 2099");
});
test("what-if merges preserve vendor and checklist state", () => {
  const plan = {
    request: { budget: 100 },
    timeline: [{ completed: true }],
    vendors: [
      { status: "booked", linked_category: "Venue", allocated_amount: 100 },
    ],
  };
  const next = withBudget(plan, {
    total: 200,
    lines: [{ category: "Venue", amount: 200 }],
  });
  assert.equal(next.vendors[0].allocated_amount, 200);
  assert.equal(next.vendors[0].status, "booked");
  assert.equal(next.timeline[0].completed, true);
  assert.equal(plan.request.budget, 100);
});
