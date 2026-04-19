# UI Postmortem And Guardrails

## Date

- 2026-04-19

## Why This Postmortem Exists

- The frontend direction drifted for multiple rounds before converging to the correct admin analysis system.
- This should not have taken that many iterations.
- The problem was not only implementation. It was also product judgment, validation discipline, and acceptance control.

## My Mistakes

### Mistake 1: I optimized for "good-looking UI" before locking the product type

- I treated the task too much like a generic frontend redesign problem.
- I produced interfaces closer to a landing page or a polished workspace, instead of a true management and analysis system.
- This was a product-shape error, not just a styling error.

### Mistake 2: I did not freeze explicit UI acceptance criteria early enough

- I should have converted the user's intent into a hard checklist before iterating:
- Must look like a management system.
- Must have a data-dense dashboard structure.
- Must prioritize tables, KPIs, filters, batch views, report reading, and operational status.
- Must not look like a marketing page, hero page, or portfolio-style workspace.
- Because I did not lock these criteria first, several iterations were "reasonable" visually but still wrong for the product.

### Mistake 3: I validated code structure more than real browser delivery

- I verified HTML generation and component structure, but I did not verify the full browser-facing delivery chain early enough.
- As a result, the UI code could be conceptually correct while the live browser still looked broken.
- This allowed the CSS media-type bug to survive longer than it should have.

### Mistake 4: I relied too much on automated confidence and not enough on visual smoke checks

- Tests passing did not prove the page looked correct.
- The project needed a dedicated frontend smoke checklist:
- Home page loads with styles.
- Icons render.
- Sidebar renders.
- Tables render.
- Upload panel is visible.
- The page does not degrade into raw text or one oversized clickable block.
- I added technical checks later, but I should have used this visual checklist from the first frontend pass.

### Mistake 5: I did not adapt fast enough to the local runtime constraints

- This repository uses a lightweight local FastAPI-compatible layer, not the normal production stack.
- That means browser delivery details like response media type matter even more.
- I should have inspected the actual response behavior of `/static/styles.css` sooner instead of assuming the usual framework behavior.

### Mistake 6: I allowed iteration churn instead of enforcing a tighter review gate

- After the first user rejection, I should have stopped and re-framed the target UI as:
- "enterprise admin console"
- "batch analysis center"
- "operations dashboard"
- "report review system"
- Instead, I still allowed intermediate designs that were too close to generic showcase UI.

## Root Causes

- Template bias: defaulting toward common polished UI patterns instead of the exact product archetype.
- Weak acceptance gating: no locked visual contract before iteration.
- Incomplete verification: validating generated markup without validating browser delivery.
- Environment assumption: treating the local stack like a standard FastAPI + static-files setup.

## What I Should Have Done

1. Freeze the product archetype before touching layout.
2. Translate the user's words into explicit visual constraints.
3. Build the first version directly as an admin dashboard, not as an intermediate concept.
4. Verify CSS route headers and live rendering on the first frontend pass.
5. Add regression checks immediately after the first visual bug.

## Guardrails For Future Frontend Work

### Product-shape gate

Before implementation, explicitly classify the requested UI as one of:

- Landing page
- Marketing site
- Workspace
- Admin system
- Dashboard
- Reader tool
- Operations console

If the request is an admin or analysis system, do not start with hero-first layouts.

### Acceptance gate

Before the first frontend commit, write a checklist in the work log:

- What it must look like
- What it must not look like
- What information must be visible on first screen
- What user actions must be primary

### Delivery gate

Before calling a frontend "done", verify:

- HTML structure
- CSS route media type
- Static asset loading
- Cache behavior during local iteration
- Basic visual smoke behavior in the live page

### Regression gate

When a UI bug appears in the browser, add one of:

- an automated response contract test
- a route-level regression test
- a documented smoke-check item

Do not rely on memory alone.

## Concrete Rules I Must Follow Next Time

- Do not redesign an admin system as a landing page.
- Do not trust "good visual taste" over the user's product description.
- Do not stop at HTML inspection when the bug is visual.
- Do not assume static resources are being served correctly.
- Do not count a frontend round as successful until runtime delivery is verified.

## What Was Fixed This Time

- The visual direction was rebuilt as a real admin analysis dashboard.
- The stylesheet route was corrected to return `text/css; charset=utf-8`.
- A no-store cache header was added for local iteration.
- A regression test was added for stylesheet delivery.

## Follow-up Standard

For future UI rounds in this project, every proposed screen must be judged against this sentence first:

- "Does this look like a management and analysis system that an operator would use all day?"

If the answer is not clearly yes, the design direction is wrong and must be corrected before implementation continues.
