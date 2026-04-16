# AGENTS.md

## 1. Purpose

This repository is for building a **Windows local-first asset management workbench**.

The product is **not** a full Explorer replacement. The current phase focuses on a narrow MVP that proves the following core chain:

> source onboarding → file indexing → search → details → tags / color tags → media browsing → recent imports organization → open file / open containing folder

All implementation work must protect this chain.

---

## 2. Project Definition

### 2.1 What this product is
This project is:
- a Windows local-first asset management workbench
- a metadata and library layer built on top of the real file system
- a product centered on search, tagging, media browsing, and organization

### 2.2 What this product is not
This project is **not** currently:
- a full Windows Explorer replacement
- a cloud sync platform
- a multi-user DAM system
- an AI auto-tagging platform
- a full Steam-like game launcher
- a full Calibre-like ebook manager
- a complex automation / rule engine

Do **not** expand the product scope beyond the current MVP unless the task explicitly requests it.

---

## 3. Current Phase Boundary

### 3.1 P0 scope only
Until explicitly changed, work must remain inside the current P0 MVP scope:
- source management
- file indexing
- search
- file details
- normal tags
- color tags
- media library (image/video)
- recent imports
- basic file browser
- open file / open containing folder
- modern desktop UI baseline

### 3.2 Explicitly out of scope for now
Do **not** implement or partially introduce:
- cloud sync
- user accounts / auth / permissions
- AI auto-tagging
- OCR / semantic indexing / embeddings
- complex batch file operations
- deep shell integration / Explorer replacement
- full game / book / app vertical systems
- plugin architecture
- message queue / microservices / distributed architecture

If a task appears to drift into these areas, stop and report the scope conflict instead of improvising.

---

## 4. Core Architecture Rules

### 4.1 Truth layers
Always preserve the following layering:
- **File system** = fact layer
- **Database** = organization layer
- **Derived / AI / semantic data** = derived layer (future only)

Do not let derived logic overwrite fact-layer truth.

### 4.2 Unified core object
Treat `FileItem` as the central object of the system.

Do not split the system into isolated mini-products for:
- search
- media browsing
- tags
- recent imports
- file browser

These must remain parts of one unified workbench.

---

## 5. Backend Rules

### 5.1 Layering
Backend code must keep these boundaries:
- `route` / `router`: request parsing, dependency injection, calling services, returning schemas
- `service`: business logic, orchestration, transaction boundaries, cross-repository coordination
- `repository`: data access only, no business rules
- `worker`: task execution only, no business semantics

### 5.2 Router rules
Routers must **not**:
- implement business rules
- manage transactions directly
- embed SQL logic
- coordinate multiple domain operations inline

### 5.3 Repository rules
Repositories must stay minimal and focused.
Repositories may:
- query
- add
- update
- flush
- provide reusable filtering helpers

Repositories must **not**:
- own business workflows
- decide task semantics
- perform product-level state transitions
- act like services

### 5.4 Worker rules
Workers must execute background operations such as:
- scanning
- metadata extraction
- thumbnail generation

Workers must **not** decide product-level behavior.
They are execution units called by services / task runtime.

### 5.5 Current backend priority
Backend changes should prioritize this order:
1. source management
2. scanning and indexing
3. search and file details
4. tagging / color tags
5. media metadata / thumbnails
6. recent imports and media library queries

---

## 6. Frontend Rules

### 6.1 Layering
Frontend must keep these boundaries:
- `app/`: app shell, providers, router, global layout
- `pages/`: page entry and layout composition
- `features/`: business capability UI and local state
- `entities/`: stable front-end object definitions
- `shared/`: reusable UI and utilities
- `services/`: API calls, mappers, query helpers

### 6.2 App shell rules
The frontend must behave like one unified desktop workbench.
Keep:
- shared app shell
- shared sidebar
- shared top bar
- shared right details panel container

Do not let each page reinvent its own shell.

### 6.3 Details panel rule
`DetailsPanelFeature` is a cross-page core feature.
Do not fork it into page-specific implementations unless explicitly required.

The details panel is not just an info box. It is a high-frequency organization center.

### 6.4 Global state rule
Use global state sparingly.
Global state is only for genuinely cross-page UI concerns, such as:
- selected item id
- details panel open / close
- global theme
- global toast messages

Do **not** move page-local state into global storage unless there is a clear cross-page need.
Page-local examples:
- search query
- filters
- sorting
- pagination
- page-specific view mode
- selection mode

### 6.5 UI interaction rules
Maintain these UI rules unless explicitly changed:
- single click = select + show details
- double click = open file
- filters apply immediately
- tag and color-tag interactions should be lightweight
- empty / loading / no-results states must be handled intentionally

---

## 7. Data and API Rules

### 7.1 Schema rules
Do not turn the core `files` table into a giant wide table.
Use extension tables for:
- metadata
- user metadata
- library mapping
- thumbnails
- tasks

### 7.2 API rules
Keep API style consistent:
- stable route naming
- stable response structure
- stable pagination / sorting / filtering parameter names
- stable error format

Do not create page-specific one-off API shapes unless truly necessary.

### 7.3 View model rule
Frontend should consume stable view models, not raw DB-shaped responses.
Backend services should assemble response models intentionally.

---

## 8. Task Execution Rules for Codex

### 8.1 Always plan first for non-trivial work
If the task is non-trivial, do **not** jump directly into code.
First produce:
1. scope understanding
2. files to change
3. files not to change
4. dependencies
5. validation plan

Then implement only after the plan is coherent.

### 8.2 Keep diffs scoped
Do not opportunistically refactor unrelated code.
Do not “clean up” broad areas unless the task explicitly asks for it.

Every task should aim for the smallest clean diff that completes the requested work.

### 8.3 Respect task boundaries
If asked to implement one task package, implement only that package.
Do not silently add P1/P2 work.
Do not silently redesign architecture.
Do not silently rename broad structures without need.

### 8.4 Report conflicts instead of inventing solutions
If documentation conflicts, or the codebase contradicts current rules:
- stop
- explain the conflict
- propose minimal options
- do not improvise a hidden product decision

---

## 9. Documentation Sync Rules

When implementation changes meaningfully affect product, API, schema, architecture, or task flow, update the relevant docs.

At minimum, changes may require updates to one or more of:
- README v1
- PRD v1
- technical architecture draft
- schema + API draft
- task breakdown doc
- frontend scaffold doc
- backend scaffold doc

Do not leave core docs stale when the implementation has clearly changed.

---

## 10. Validation Rules

Every meaningful task completion should include a validation section.

Where relevant, provide:
- how to run the updated code
- what endpoint / page / flow to test
- what result is expected
- which limitations still remain

If tests exist, run them.
If tests do not yet exist, provide the manual verification path.

---

## 11. Preferred Task Output Format

For each implementation task, end with:

1. **What changed**
2. **Files changed**
3. **Why this scope is sufficient**
4. **Validation steps**
5. **Docs updated**
6. **What remains intentionally not done**

This helps keep progress reviewable and prevents false completeness.

---

## 12. Current Highest Priority Principle

If there is ever ambiguity, optimize for this:

> Make the local asset workflow of “find → inspect → tag → refind → browse” more solid, not broader.

Do not sacrifice the clarity of the MVP for speculative future features.

---

## 13. Anti-Drift Rules

Avoid these common failure modes:

### 13.1 Product drift
Do not turn the project into:
- a replacement Explorer
- a game launcher platform
- an ebook ecosystem
- an AI lab product
- a generic automation framework

### 13.2 Architecture drift
Do not introduce:
- microservices
- message brokers
- plugin systems
- heavy task orchestration platforms
- large event-driven infrastructure

### 13.3 Frontend drift
Do not create:
- page-specific duplicated search logic
- page-specific duplicated details panel logic
- large global stores containing everything
- inconsistent tag / filter interaction patterns

### 13.4 Backend drift
Do not create:
- business-heavy routers
- repositories acting like services
- workers deciding domain rules
- schema/API sprawl with inconsistent conventions

---

## 14. When in Doubt

If unclear, prefer the more conservative option that:
- preserves current architecture boundaries
- preserves the MVP scope
- preserves the main user flow
- minimizes irreversible design decisions

When uncertainty is high, ask for clarification through a concise implementation note instead of making silent product decisions.

---

## 15. Immediate Working Priority

Until explicitly changed, the next implementation priorities are:
1. PoC validation of scanning / query / thumbnail / rendering risk
2. frontend shell + core page scaffolds
3. backend shell + source / scan / search / detail scaffolds
4. end-to-end MVP core chain

Everything else is secondary to that.
