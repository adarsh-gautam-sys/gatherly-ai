# Accessibility verification

## Target and implemented support

Gatherly targets WCAG 2.2 AA. Automated results do not establish full conformance.
The interface has semantic landmarks, one visible page heading, a skip link,
labelled controls, field descriptions and an error summary that receives focus.
Tabs implement roving focus with Left/Right, Home and End keys. Native checkboxes,
radios, selects, dates and expandable details retain browser keyboard behavior.
Status messages announce generation, updates and fallback; busy actions are
disabled while requests run. A failed update preserves the current plan.

Text never relies on colour alone. Light/dark preferences and reduced motion are
supported. The budget change highlight is the only authored animation; reduced
motion disables it. Small-screen layouts stack the form and overview. Tables
retain captions and row/column headers, with a local scroll container if needed.
Controls have 44 px minimum row targets; checklist text labels enlarge the native
checkbox target. Print expands every result section into a single document.

## Automated evidence

Run `make check` after `make install` (Python 3.12, Node 22.19+ and GNU Make).
CI installs Chromium's Linux system dependencies before running the same gate.
Only browser-test tooling uses npm; the shipped frontend has no build step or
runtime JavaScript dependencies.

`tests/browser/planner.spec.mjs` runs axe-core 4.14.0 against intake, validation
errors, light/dark modes and the four result sections. WCAG 2 A/AA, 2.1 A/AA,
2.2 AA and best-practice tags are included. Tested widths are 320, 390, 640 and
1440 px. The 640 px case represents the effective width of a 1280 px viewport
at 200% zoom; actual browser zoom and text-only scaling remain manual checks.
All tested states have zero violations. Lighthouse 13.5.0 reports accessibility
100 and best practices 100 on the initial production page using Chromium.
Lighthouse does not exercise every interactive state; axe and flow tests do.

The keyboard test follows the skip link, event radio, intake fields and optional
preferences, submits with Enter, changes tabs with arrow keys, checks a timeline
task with Space and verifies retained progress. Native date-field segmented tab
stops are traversed explicitly; its value is supplied with Playwright's native
field fill for consistent operating-system date formats.

## Manual verification still required

Use NVDA with Chrome/Firefox on Windows, or VoiceOver with Safari on macOS:

1. Navigate headings and landmarks; activate the skip link and verify the main
   planner receives focus.
2. Submit empty intake and confirm the summary, error links and field descriptions
   are understandable. Correct fields without losing other entries.
3. Complete each event type with realistic preferences. Confirm generation and
   fallback messages are announced once, without reading the entire page again.
4. Navigate tabs with arrows and Tab, toggle tasks, and change vendor status.
   Verify control names, checked/selected state, dates and amounts are announced.
5. Change the budget, refine ideas and simulate a connection failure. Confirm
   status/error announcements and preserved progress.
6. Export JSON, reload and reopen it. Verify completion and vendor status survive.
   Review Markdown/calendar downloads and print/PDF output in the system dialogs.
7. At actual 200% browser zoom and text-only zoom, check reachability, readable
   content, focus visibility and lack of page-level horizontal scrolling.

No assistive-technology user walkthrough or audible screen-reader check has
been claimed. Record the browser, reader/version, date and findings here when
that manual pass is performed.
