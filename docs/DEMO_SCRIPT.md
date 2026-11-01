# Gatherly AI: Demonstration Walkthrough Script

This script provides an interactive 3–5 minute demonstration of **Gatherly AI** for reviewers and challenge evaluators.

---

## Pre-Demo Quick Start

1. Start the application locally:
   ```sh
   make run
   ```
2. Open your browser to **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**.
3. (Optional) If you have a Gemini API key, start with `GEMINI_API_KEY=your_key make run`. If no key is set, Gatherly AI runs automatically in **deterministic fallback mode** with identical schema guarantees.

---

## Act 1: The Problem & The Intake (0:00 – 1:00)

**Narrator / Presenter:**
> *"Planning celebrations—weddings, milestone birthdays, and community festivals—is traditionally messy. Planners juggle chaotic spreadsheets, forgotten vendor questions, and unrealistic schedules. Generic LLMs hallucinate impossible budgets and dates. Gatherly AI solves this by separating deterministic math from generative creativity."*

**Action:**
1. Navigate to the intake form.
2. Select **Wedding**.
3. Fill in the scenario:
   - **Guest Count:** `120`
   - **Event Date:** Select a date **8 months** in the future.
   - **Location:** `London, UK`
   - **Currency:** `GBP (£)`
   - **Total Budget:** `25000` (£25,000)
4. Expand **Optional preferences**:
   - **Theme & Vibe:** `Rustic botanical, candlelit warmth`
   - **Dietary Requirements:** `Vegan and gluten-free options`
5. Click **"Generate celebration plan"**.

---

## Act 2: Pure Deterministic Control (1:00 – 2:00)

**Narrator / Presenter:**
> *"Notice the speed. In a fraction of a second, Gatherly generates a complete plan. Notice how money and dates are treated: zero hallucinations."*

**Action:**
1. **Overview Tab:**
   - Point out the summary cards: Total Budget (£25,000.00), Planned Spending (£25,000.00), Remaining (£0.00).
   - Point out the Contingency Reserve (£2,500.00, exactly 10%).
2. **Budget Tab:**
   - Inspect the budget breakdown table: Venue (40%), Catering & Bar (30%), Photo & Video (10%), etc.
   - Emphasize: *Every single penny is conserved using the Largest Remainder Method. There are no floating-point rounding errors.*
3. **Timeline Tab:**
   - Review chronological milestones calculated backwards from the wedding date.
   - Click the checkbox for **"Establish wedding budget and priority list"** and **"Book ceremony and reception venue"**.
   - Note how the completion state persists dynamically in the UI.
4. **Vendors Tab:**
   - Inspect the **Catering** vendor checklist.
   - Point out the pre-populated vendor interview questions (e.g., *"Are tasting sessions included?"*, *"What is your staffing ratio per guest?"*) and required contracts/permits.

---

## Act 3: Deterministic "What-If" Budget Recalculation (2:00 – 2:45)

**Narrator / Presenter:**
> *"Now the couple discovers their venue costs less than expected, or they want to trim their budget down to £20,000. What happens in a traditional tool? You start over or manually edit every spreadsheet cell. In Gatherly AI, we test this deterministically with zero AI latency and zero hallucination."*

**Action:**
1. Switch to the **Budget** tab.
2. In the "What-if budget recalculation" panel, change the budget input to `20000`.
3. Click **"Update budget"**.
4. Observe the result:
   - Every category instantly scales to the new £20,000.00 total down to the exact penny.
   - Switch to the **Timeline** and **Vendors** tabs: **Checked tasks and vendor statuses remain intact!**
   - The creative ideas are clearly labeled as based on the prior budget until explicitly refreshed.

---

## Act 4: Schema-Constrained Gemini Creativity (2:45 – 3:30)

**Narrator / Presenter:**
> *"Now let's examine where Gemini shines: creative inspiration that respects our exact parameters."*

**Action:**
1. Switch to the **Creative Ideas** tab.
2. Review the structured ideas:
   - **3 Cohesive Themes:** e.g., *"English Meadow & Botanical Glasshouse"*, complete with color palettes and styling notes.
   - **Curated Menu Concepts:** Tailored to the 120 guests with vegan/gluten-free pairings.
   - **Memorable Activities:** Interactive guestbook, botanical cocktail workshop.
   - **Cost-Saving Tips:** Direct actionable savings tied to actual budget categories.
3. Test **Idea Refinement**:
   - In the "Refine creative ideas" box, select section: `Catering & Menu`.
   - Enter instruction: `Emphasize seasonal farm-to-table British produce and artisanal mocktails`.
   - Click **"Refine creative ideas"**.
   - Show how the menu ideas update specifically while retaining all budget figures and timeline milestones.

---

## Act 5: Exports, Accessibility & Portability (3:30 – 4:15)

**Narrator / Presenter:**
> *"Finally, Gatherly AI respects user privacy and data ownership. There are no user accounts, no tracking cookies, and no database lock-in."*

**Action:**
1. Click **"Download Markdown"**: Open or inspect the generated markdown file showing completed tasks marked as `- [x]`.
2. Click **"Download Calendar (.ics)"**: Inspect the standard RFC 5545 calendar entries.
3. Click **"Export JSON"**: Save `gatherly-plan.json`.
4. **The Portability Test:**
   - Reload the browser page (`F5`).
   - The page returns to the clean intake form (demonstrating zero lingering server-side state).
   - In the intake section, click **"Reopen JSON plan"** and select `gatherly-plan.json`.
   - **Result:** The entire plan—including adjusted budget, custom instructions, and checked milestone tasks—is completely restored.
5. Press `Ctrl + P` / `Cmd + P`: Show the dedicated **print preview**, formatted as an executive celebration brief.

---

## Act 6: Quality, Security & Standards Wrap-Up (4:15 – 4:45)

**Narrator / Presenter:**
> *"Under the hood, Gatherly AI meets the highest engineering standards:
> - **100% pure domain logic** with zero I/O.
> - **98.94% overall automated test coverage**, with 100.00% domain coverage.
> - **WCAG 2.2 AA compliant** with 0 axe-core violations and Lighthouse Accessibility 100.
> - **Production containerized** as a read-only, non-root microservice ready for Google Cloud Run."*

