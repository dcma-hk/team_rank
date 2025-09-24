## Team Stack Ranking Manager – Product Requirements Document (PRD)

### 1. Overview
A web application for managers to view, compare, and adjust the stack rank of team members based on role‑specific weighted metrics. Data is sourced from a single local Excel workbook with three tabs and changes are written back to the same file.

### 2. Goals
- Provide transparent, role‑aware ranking based on weighted metric scores.
- Highlight mismatches between calculated rank and expected rank.
- Enable guided, safe score adjustments to align outcomes with expectations.
- Visualize organizational distribution by percentile and role.

### 3. Non‑Goals
- Authentication/authorization and multi‑user concurrency.
- Support for data sources other than the specified Excel workbook.
- Complex what‑if simulations beyond the specified “calculate” helper.

### 4. Primary User
- People managers responsible for the listed team members.

### 5. Data Source (Single Excel Workbook)
- Location: Configurable local file path (env var EXCEL_PATH); defaults to a file within the app directory.
- Tabs and Schemas:
  1) Roles (sheet name: "Roles")
     - Columns: alias (string, unique), role (string)
     - Example rows: Tom, Developer; John, Developer; Jane, Project Manager
  2) Scores (sheet name: "Scores")
     - Columns (left→right):
       - metrics (string; unique metric name)
       - One column per role with the weight for that role (float 0..1)
       - Max (float; max team score for this metric)
       - Min (float; min team score for this metric)
       - One column per team member (alias) holding that member’s raw score for the metric (float typically within [Min, Max])
     - Notes:
       - Only metrics with weight > 0 apply to a given role.
       - Max/Min can be recomputed by the app on load or save as the max/min across all member columns for that metric.
  3) ExpectedRanking (sheet name: "ExpectedRanking")
     - Columns: alias (string), role (string), rank (integer ≥1). Duplicate ranks are allowed (ties), and members without an entry are treated as having no expected rank.

- Data Validation & Normalization:
  - Trim whitespace, case‑normalize alias matches across sheets; log and surface mismatches.
  - Validate that all member columns in Scores exist in Roles and vice versa; report extras/missing.
  - Validate role weight columns exist for all roles listed in Roles.

### 6. Core Concepts and Calculations
- Weighted Score (per member): For each metric m
  - Consider only the weight for the member’s role: w = weight(role, m)
  - Contribution = score(member, m) × w
  - Weighted score = Σ over all metrics of Contribution
- Ranking:
  - Ranking is computed within role cohorts (i.e., members of the same role are ranked together).
  - Sorting by weighted score (desc). Ties (exact same weighted score) share the same rank using dense ranking (e.g., 1,2,2,3).
  - If multiple roles are selected in the UI, show groupings per role with independent ranks.

### 7. Functional Requirements

#### 7.1 Page #1 – Stack Rank Table
- Role filter: multi‑select of roles to include.
- Table columns:
  - alias
  - role (if >1 roles selected)
  - rank (computed)
  - expected rank (from ExpectedRanking; blank if none)
  - weighted score (with 2–4 decimal precision)
  - Metric scores: columns labeled with a short numeric label (e.g., M1, M2, …); each has a tooltip with the full metric name.
- Highlight entries where rank ≠ expected rank (e.g., both rank and expected rank cells).
- Interaction:
  - Clicking on a highlighted rank opens Page #2 preloaded for that member.
  - Sorting by any column; default by role then rank asc.
  - Sticky header and horizontal scroll for metrics.
- Performance: Pagination or virtualized table for large column counts.

#### 7.2 Page #2 – Adjust Scores
- Layout: Metrics as rows; team members as columns.
  - Always include the selected member’s column.
  - Include a reference member (same role) depending on direction:
    - If selected member’s current rank is lower (worse) than expected: show the member at one level better rank as reference.
    - If higher (better) than expected: show the member at one level worse rank as reference.
  - Only include metrics applicable to the selected member’s role (weight > 0). Show role weight per metric.
- Controls:
  - Checkbox list to select metrics to adjust manually/automatically.
  - Target delta input: default 5% (user editable) relative to reference weighted score.
  - Buttons:
    - Calculate: compute proposed new scores for the selected metrics so that the selected member’s weighted score becomes S_target = S_ref × (1 ± p). Direction chosen automatically to move toward expected rank. Respect per‑metric Min/Max and zero‑weight metrics. If selected metrics’ total role‑weight is zero, show error.
    - Next: navigate to the next member (by current data) with rank ≠ expected rank; persists unsaved changes prompt if any.
    - Save: write updated scores back to Excel, recompute Max/Min for each metric, recompute ranks, then return to Page #1 with updated view and highlights.
- Auto‑Adjust Algorithm (transparent and explainable):
  - Let S_cur be current weighted score; S_ref the reference; p the target percent (e.g., 0.05). Define S_target = S_ref × (1 + p) if trying to move above reference; else (1 − p) if moving below.
  - Only adjust selected metrics M with role weights w_m > 0.
  - Compute needed delta D = S_target − S_cur.
  - Distribute D proportionally to weights over M: proposed delta per metric d_m = D × (w_m / Σ_w).
  - Convert to raw score adjustments: Δscore_m = d_m / w_m; clip new scores to [Min, Max]. Recompute achieved weighted score; if under‑achieved due to clipping, iterate proportionally over remaining headroom up to 3 passes; report if target not fully achievable.
  - Display a diff table (old, new, delta) before apply.

#### 7.3 Page #3 – Org Ranking Percentiles
- Basis toggle: weighted score or rank (within role).
- Buckets: rows for 10%, 20%, …, 100%.
- Columns: roles.
- For each [role, bucket], list members falling in that percentile band with their weighted score (or rank). Ties spanning boundaries appear in the higher bucket; show a count + expandable list for readability.

### 8. API Design (FastAPI)
- GET /api/roles → { roles: ["Developer", "Project Manager", …], countsByRole: {role: n} }
- GET /api/members → [{ alias, role }]
- GET /api/metrics → [{ id: "M1", name: "Software Engineer principal", weightsByRole: {...}, min, max }]
- GET /api/scores → { metrics: [names], members: [aliases], scores: { alias: { metricName: number } } }
- GET /api/rankings?roles=RoleA,RoleB → [{ alias, role, weightedScore, rank, expectedRank, mismatch: bool }]
- GET /api/mismatches → ordered list of members with rank ≠ expected rank
- POST /api/adjust/preview { alias, selectedMetrics: [names], percent: number } → { proposed: { metricName: newScore }, achievedWeightedScore, hitClamps: [metricNames] }
- POST /api/adjust/apply { alias, changes: { metricName: newScore } } → { ok: true, updatedAt, rankings: [...] }
- GET /api/percentiles?basis=weighted|rank → { buckets: [{ pct: 10, byRole: { role: [{ alias, weightedScore|rank }] } }, ...] }
- Error responses: { error: { code, message, details? } }

### 9. Backend Implementation Notes
- Python, FastAPI, pandas, openpyxl.
- Data loading:
  - Load all sheets into DataFrames. Normalize alias, role names.
  - Validate schema; return explicit errors for missing sheets/columns.
- Computations:
  - Weighted scores computed on demand or cached with invalidation on save.
  - Recompute Max/Min on save as the max/min across member columns for each metric.
  - Ranking per role with dense ranking; deterministic tie‑break by alias for display stability.
- Persistence:
  - All edits affect only member score columns in Scores sheet.
  - Use file lock (advisory) while writing to avoid partial writes.
- Config: EXCEL_PATH, PORT, LOG_LEVEL, CORS origins.

### 10. Frontend Implementation Notes
- React + Material UI.
- Routing: Page #1 (/), Page #2 (/adjust/:alias), Page #3 (/org).
- State/data: React Query (or SWR) to fetch rankings, mismatches, metrics, and scores; optimistic update on save.
- Components:
  - StackRankTable with metric label→tooltip mapping.
  - AdjustScoresPanel with metric selection, percent input, reference panel, and diff table.
  - OrgPercentilesGrid with bucketed grouping and expand/collapse.
- Accessibility: Keyboard navigation, ARIA labels for tooltips and buttons.

### 11. Edge Cases & Validation
- Missing expected rank: display blank; no highlight unless explicitly different from computed (blank ≠ any rank → no highlight).
- Multiple members sharing expected rank: allowed.
- Alias in Roles but missing in Scores (or vice versa): surface warning; exclude from computations until resolved.
- Metrics with zero total role weight across all roles: permitted; they won’t affect any ranking.
- Selected metrics for auto‑adjust all have zero weight: block with clear error.
- Score bounds: Enforce Min/Max; report any clamped adjustments.
- External edits to Excel while app is open: detect on save (mtime change); prompt to reload or overwrite.

### 12. Performance & Scale
- Intended scale: ≤500 members, ≤100 metrics, ≤20 roles.
- Server computes ranks in O(M×N) per role selection; acceptable with caching.

### 13. Security & Privacy
- Local‑only data access; no external data transmission.
- CORS limited to localhost by default.
- Input sanitation for file path and HTTP inputs; no code execution from Excel content.

### 14. Observability
- Structured logs for load, compute, preview, apply, and errors.
- Basic metrics: requests count/latency by endpoint; number of clamp events during auto‑adjust.

### 15. Acceptance Criteria
- Page #1 shows correct role‑grouped ranks with mismatches highlighted and tooltips for metrics.
- Clicking a highlighted rank opens Page #2 with correct reference member and metrics filtered to applicable ones.
- Auto‑adjust brings weighted score to within ±0.5% of target if not clamped; otherwise reports clamped metrics.
- Save writes new scores to Excel, recomputes Max/Min, and updates rankings on return to Page #1.
- Page #3 displays members bucketed by 10% increments per role by chosen basis.
- All endpoints return correct shapes; errors are informative.

### 16. Milestones
- v0.1: Project scaffolding; Excel loader and schema validation; GET /roles, /members, /metrics.
- v0.2: Weighted score + ranking; Page #1 table with filters/highlights.
- v0.3: Adjust page with preview algorithm; POST /adjust/preview; navigation via Next.
- v0.4: Save to Excel; POST /adjust/apply; return to Page #1 with updates.
- v1.0: Org Percentiles view; percentiles API; UI polish, accessibility, logging.

### 17. Out of Scope (for v1)
- Multi‑user locking/sync beyond single‑process file lock.
- Historical tracking/versioning of score changes.
- Authentication/role‑based access control.

