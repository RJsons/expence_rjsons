# Implementation Plan: Expense Tracker Enhancements

## Overview

Extend the existing single-file FastAPI application (`main.py`) with five feature areas: Custom Categories, Budget Limits & Alerts, Recurring Expenses (APScheduler), Reports & Analytics, and CSV/PDF Export. All new code is added to `main.py` following the existing patterns (SQLAlchemy ORM, Pydantic schemas, JWT auth via `Depends(get_current_user)`). Two new dependencies (`apscheduler`, `reportlab`) are added to `requirements.txt`.

---

## Tasks

- [x] 1. Add new dependencies and extend database schema
  - [x] 1.1 Update `requirements.txt` with new dependencies
    - Add `apscheduler==3.10.4` and `reportlab==4.2.2` to `requirements.txt`
    - _Requirements: 3.3 (APScheduler job), 5.4 (PDF export)_

  - [x] 1.2 Add `CategoryDB`, `BudgetLimitDB`, and `RecurringTemplateDB` SQLAlchemy models
    - Define `CategoryDB` with columns: `id`, `name`, `color`, `icon`, `is_default`, `user_id` (FK → users)
    - Define `BudgetLimitDB` with columns: `id`, `user_id`, `category`, `limit_amount`, `month`, `year`, `alert_threshold`
    - Define `RecurringTemplateDB` with columns: `id`, `user_id`, `title`, `amount`, `category`, `is_income`, `notes`, `frequency`, `start_date`, `next_due_date`, `is_active`
    - Add `back_populates` relationships on `UserDB` for all three new models
    - Call `Base.metadata.create_all(bind=engine)` (already present — ensure new tables are picked up)
    - _Requirements: 1.3, 2.4, 3.5_

- [x] 2. Implement Custom Categories feature
  - [x] 2.1 Add Category Pydantic schemas and `DEFAULT_CATEGORIES` constant
    - Add `CategoryCreate` (name min_length=1, max_length=50; optional color, icon) and `CategoryResponse` schemas
    - Define `DEFAULT_CATEGORIES` list of 8 dicts (name, color, icon) as a module-level constant
    - _Requirements: 1.3, 1.4_

  - [x] 2.2 Implement `GET /api/categories` endpoint with default seeding
    - Query `CategoryDB` filtered by `current_user.id`
    - If result is empty, bulk-insert the 8 `DEFAULT_CATEGORIES` with `is_default=True` and `user_id=current_user.id`, then return them
    - Return `List[CategoryResponse]` with HTTP 200
    - _Requirements: 1.1, 1.2_

  - [x] 2.3 Implement `POST /api/categories` endpoint
    - Accept `CategoryCreate` body; persist with `user_id=current_user.id`, `is_default=False`
    - Return `CategoryResponse` with HTTP 201
    - Pydantic validation on `name` (min 1, max 50) handles requirement 1.4 automatically
    - _Requirements: 1.3, 1.4_

  - [x] 2.4 Implement `PUT /api/categories/{id}` and `DELETE /api/categories/{id}` endpoints
    - For PUT: query by `id` AND `user_id==current_user.id`; raise HTTP 404 with `{"detail": "Category not found or access denied"}` if not found; update `name`, `color`, `icon`; return updated `CategoryResponse`
    - For DELETE: same ownership check; delete record; return HTTP 200 `{"detail": "Category deleted successfully"}`; do NOT touch any `ExpenseDB` records
    - _Requirements: 1.5, 1.6, 1.7_

  - [ ]* 2.5 Write property test for category ownership isolation
    - **Property 4: Category Ownership Isolation**
    - **Validates: Requirements 1.2**
    - Use `hypothesis` to generate two distinct user IDs and a list of categories; assert that querying categories for user A never returns categories seeded for user B

  - [ ]* 2.6 Write unit tests for category endpoints
    - Test default seeding on first GET (8 categories returned)
    - Test second GET returns same 8 without re-seeding
    - Test POST creates category with correct `user_id`
    - Test PUT/DELETE return 404 for wrong user or missing id
    - Test DELETE leaves `ExpenseDB` records untouched (Property 9)
    - _Requirements: 1.1–1.8_

- [ ] 3. Implement Budget Limits & Alerts feature
  - [x] 3.1 Add Budget Pydantic schemas
    - Add `BudgetLimitCreate`, `BudgetLimitResponse`, and `BudgetStatusResponse` schemas as specified in the design
    - _Requirements: 2.4, 2.6_

  - [x] 3.2 Implement `determine_alert_level` helper and `calculate_budget_status` service function
    - `determine_alert_level(usage_pct, alert_threshold) -> str`: returns `"exceeded"` if `usage_pct >= 1.0`, `"warning"` if `usage_pct >= alert_threshold`, else `"ok"`
    - `calculate_budget_status(db, user_id, category, month, year) -> Optional[BudgetStatusResponse]`: fetch budget limit, aggregate `SUM(amount)` for non-income expenses in the given category/month/year, compute `usage_percentage`, `remaining_amount`, call `determine_alert_level`
    - _Requirements: 2.1, 2.5_

  - [ ]* 3.3 Write property test for budget alert level consistency
    - **Property 1: Budget Alert Level Consistency**
    - **Validates: Requirements 2.1**
    - Use `hypothesis` with `st.floats` for `spent`, `limit`, `threshold`; call `determine_alert_level(spent/limit, threshold)`; assert the three mutually exclusive conditions

  - [x] 3.4 Implement `GET /api/budgets` and `POST /api/budgets` endpoints
    - GET: return all `BudgetLimitDB` records for `current_user.id` as `List[BudgetLimitResponse]`
    - POST: check for duplicate (same `category`, `month`, `year`, `user_id`) → HTTP 409; otherwise persist and return `BudgetLimitResponse` HTTP 201
    - _Requirements: 2.2, 2.3, 2.4, 2.6_

  - [-] 3.5 Implement `PUT /api/budgets/{id}`, `DELETE /api/budgets/{id}`, and `GET /api/budgets/status` endpoints
    - PUT/DELETE: ownership check (filter by `id` AND `user_id`); 404 if not found; update or delete; return appropriate response
    - GET status: iterate all budget limits for the user in the given month/year; call `calculate_budget_status` for each; return `List[BudgetStatusResponse]`
    - _Requirements: 2.1, 2.2, 2.5, 2.7, 2.8, 2.9_

  - [ ]* 3.6 Write property test for budget uniqueness constraint
    - **Property 10: Budget Uniqueness Per Category/Month/Year**
    - **Validates: Requirements 2.3**
    - Use `hypothesis` to generate duplicate budget create requests; assert the second POST returns HTTP 409

  - [ ]* 3.7 Write unit tests for budget endpoints
    - Test POST creates budget with correct fields
    - Test duplicate POST returns 409
    - Test GET status returns correct `alert_level` for all three states
    - Test PUT/DELETE return 404 for wrong user
    - Test `calculate_budget_status` returns `None` when no budget limit exists
    - _Requirements: 2.1–2.10_

- [~] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Recurring Expenses feature
  - [x] 5.1 Add Recurring Pydantic schemas
    - Add `RecurringTemplateCreate` (with `frequency` pattern `^(daily|weekly|monthly)$`, `amount > 0`) and `RecurringTemplateResponse` schemas
    - _Requirements: 3.5, 3.6, 3.7_

  - [x] 5.2 Implement `compute_next_due_date` function
    - `"daily"`: return `current_due_date + timedelta(days=1)`
    - `"weekly"`: return `current_due_date + timedelta(weeks=1)`
    - `"monthly"`: increment month (wrap Dec→Jan, increment year), clamp day to `calendar.monthrange` last day
    - _Requirements: 3.1_

  - [ ]* 5.3 Write property test for recurring date monotonicity
    - **Property 2: Recurring Date Monotonicity**
    - **Validates: Requirements 3.1**
    - Use `hypothesis` with `st.sampled_from(["daily","weekly","monthly"])` and `st.dates`; assert `compute_next_due_date(freq, d) > d` for all inputs

  - [x] 5.4 Implement `generate_due_recurring_expenses` scheduler function
    - Query all `RecurringTemplateDB` where `is_active=True` and `next_due_date <= today`
    - For each: insert `ExpenseDB` (notes appended with `" [auto-generated]"`), advance `next_due_date` via `compute_next_due_date`, commit; wrap each template in try/except to log errors and continue
    - Return `{"generated": N, "errors": M}`
    - _Requirements: 3.2, 3.3, 3.4_

  - [ ]* 5.5 Write property test for recurring generation idempotency
    - **Property 3: Recurring Generation Idempotency Per Day**
    - **Validates: Requirements 3.2**
    - Use `hypothesis` to generate a set of due templates; run `generate_due_recurring_expenses` twice with the same DB state; assert the second run produces 0 new expenses for the same templates (because `next_due_date` was advanced)

  - [-] 5.6 Wire APScheduler background job into FastAPI app startup
    - Import `BackgroundScheduler` from `apscheduler.schedulers.background`
    - Create scheduler instance; add job calling `generate_due_recurring_expenses` with `trigger="cron"`, `hour=0`, `minute=5`
    - Start scheduler in `@app.on_event("startup")` and shut it down in `@app.on_event("shutdown")`
    - _Requirements: 3.3_

  - [~] 5.7 Implement `GET`, `POST`, `PUT`, `DELETE /api/recurring` and pause/resume endpoints
    - GET: return `List[RecurringTemplateResponse]` for `current_user.id`
    - POST: persist with `next_due_date=start_date`, `is_active=True`, `user_id=current_user.id`; return HTTP 201
    - PUT/DELETE: ownership check; 404 if not found
    - POST `/{id}/pause`: set `is_active=False`; POST `/{id}/resume`: set `is_active=True`
    - _Requirements: 3.5–3.12_

  - [ ]* 5.8 Write unit tests for recurring endpoints and scheduler function
    - Test `compute_next_due_date` edge cases: Jan 31 → Feb 28, Dec 31 → Jan 1 (year rollover), leap year Feb 29
    - Test `generate_due_recurring_expenses` creates expense with `" [auto-generated]"` suffix and advances `next_due_date`
    - Test error in one template does not block others (returns correct `errors` count)
    - Test pause/resume toggle `is_active` correctly
    - _Requirements: 3.1–3.12_

- [~] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement Reports & Analytics feature
  - [x] 7.1 Add Report Pydantic schemas
    - Add `MonthlySummaryResponse`, `CategoryBreakdownResponse`, `MonthlyTrendResponse`, and `ChartDataResponse` schemas
    - _Requirements: 4.1–4.5_

  - [x] 7.2 Implement `compute_monthly_summary` service function
    - Aggregate `SUM(amount)` for income and non-income expenses separately for the given `user_id`, `month`, `year`
    - Compute `net_balance = total_income - total_expenses`
    - Determine `top_expense_category` via a grouped query ordered by total descending, limit 1
    - Return `MonthlySummaryResponse` (all zeros and `top_expense_category=None` if no records)
    - _Requirements: 4.1, 4.2_

  - [x] 7.3 Implement `compute_category_breakdown` service function
    - Group non-income expenses by `category` for the given month/year/user; compute `percentage_of_total = (total / grand_total) * 100`
    - Sort result by `total_amount` descending
    - Return `List[CategoryBreakdownResponse]`
    - _Requirements: 4.3_

  - [ ]* 7.4 Write property test for report totals consistency
    - **Property 6: Report Totals Consistency**
    - **Validates: Requirements 4.1**
    - Use `hypothesis` to generate lists of income and expense records; assert `net_balance == total_income - total_expenses` and `sum(breakdown.total_amount) == total_expenses` (within floating-point tolerance)

  - [ ] 7.5 Implement `GET /api/reports/monthly-summary` and `GET /api/reports/category-breakdown` endpoints
    - Both accept `month: int` and `year: int` query params; validate via Pydantic `Query(ge=1, le=12)` / `Query(ge=2000)`
    - Call respective service functions; return responses
    - _Requirements: 4.1–4.3, 4.6_

  - [~] 7.6 Implement `GET /api/reports/income-vs-expense` and `GET /api/reports/chart-data` endpoints
    - Income-vs-expense: group expenses by month for the given year; return `List[MonthlyTrendResponse]` (one entry per month with data)
    - Chart-data: accept `type` param (`"pie"`, `"bar"`, `"line"`); build `ChartDataResponse` with `labels`, `datasets` from category breakdown or trend data depending on type
    - _Requirements: 4.4, 4.5_

  - [ ]* 7.7 Write unit tests for report endpoints
    - Test monthly summary returns all-zero response for empty month
    - Test `net_balance` arithmetic correctness
    - Test category breakdown percentages sum to 100.0
    - Test income-vs-expense returns only months with data
    - Test HTTP 422 for invalid month/year params
    - _Requirements: 4.1–4.7_

- [ ] 8. Implement Export to CSV/PDF feature
  - [x] 8.1 Implement `generate_csv_export` service function
    - Build filtered `ExpenseDB` query (user_id, date range, optional category, optional is_income)
    - Write CSV to `io.StringIO` with header `id,title,amount,date,category,is_income,notes`; order by `date` ascending
    - Return `StringIO` buffer (header-only if no records)
    - _Requirements: 5.1, 5.3, 5.7, 5.8_

  - [ ]* 8.2 Write property test for CSV completeness
    - **Property 7: CSV Completeness**
    - **Validates: Requirements 5.1**
    - Use `hypothesis` to generate lists of expense dicts; call `generate_csv_export` equivalent; assert `len(csv.DictReader(buffer).rows) == len(expenses)`

  - [~] 8.3 Implement `GET /api/export/csv` endpoint
    - Accept `start_date`, `end_date`, optional `category`, optional `is_income` query params
    - Validate `start_date <= end_date` → HTTP 422 if violated (Property 8)
    - Call `generate_csv_export`; return `StreamingResponse` with `media_type="text/csv"` and `Content-Disposition: attachment; filename="expenses_{start_date}_{end_date}.csv"`
    - _Requirements: 5.1, 5.2, 5.3, 5.7, 5.8, 5.9_

  - [ ]* 8.4 Write property test for export date range validity
    - **Property 8: Export Date Range Validity**
    - **Validates: Requirements 5.2**
    - Use `hypothesis` with `st.dates`; generate pairs where `start > end`; assert endpoint returns HTTP 422

  - [~] 8.5 Implement `generate_pdf_export` service function
    - Import `reportlab` inside the function; wrap in try/except `ImportError` → raise HTTP 500 with `{"detail": "PDF export is not available. Install reportlab."}`
    - Build filtered expense query (same filters as CSV)
    - Use `reportlab.platypus` (SimpleDocTemplate, Table, Paragraph) to build PDF with: title (user name + date range), summary totals (income, expenses, net balance), expense table or "No records found" message
    - Return `io.BytesIO` buffer
    - _Requirements: 5.4, 5.5, 5.6_

  - [~] 8.6 Implement `GET /api/export/pdf` endpoint
    - Same query param validation as CSV (`start_date <= end_date` → HTTP 422)
    - Call `generate_pdf_export`; return `StreamingResponse` with `media_type="application/pdf"` and `Content-Disposition: attachment; filename="expenses_{start_date}_{end_date}.pdf"`
    - _Requirements: 5.2, 5.4, 5.5, 5.6, 5.9_

  - [ ]* 8.7 Write unit tests for export endpoints
    - Test CSV header row present when no records match filters
    - Test CSV row count matches filtered expense count
    - Test `Content-Type` and `Content-Disposition` headers for both CSV and PDF
    - Test HTTP 422 when `start_date > end_date`
    - Test PDF returns HTTP 500 message when reportlab unavailable (mock import)
    - _Requirements: 5.1–5.9_

- [~] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- The design uses Python throughout; all code targets the existing `main.py` single-file structure
- Property tests use the `hypothesis` library; add `hypothesis` to `requirements.txt` for the test environment
- Each task references specific requirements for traceability
- Checkpoints at tasks 4, 6, and 9 ensure incremental validation after each major feature area
- The `weekly` frequency in `compute_next_due_date` adds 7 days (`timedelta(weeks=1)`) per the design spec

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "3.1", "5.1", "7.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "3.2", "5.2", "7.2", "7.3", "8.1"] },
    { "id": 3, "tasks": ["2.5", "2.6", "3.3", "3.4", "5.3", "5.4", "7.4", "8.2"] },
    { "id": 4, "tasks": ["3.5", "3.6", "3.7", "5.5", "5.6", "7.5", "8.3", "8.4"] },
    { "id": 5, "tasks": ["5.7", "5.8", "7.6", "8.5"] },
    { "id": 6, "tasks": ["7.7", "8.6"] },
    { "id": 7, "tasks": ["8.7"] }
  ]
}
```
