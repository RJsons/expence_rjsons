# Requirements Document

## Introduction

This document defines the formal requirements for five enhancements to the existing FastAPI Expense Tracker backend. The enhancements extend the current two-table schema (users, expenses) with four new tables and twelve new API endpoints, while preserving full backward compatibility with existing endpoints and the Flutter mobile client.

The five feature areas are:
1. **Custom Expense Categories Management** — user-owned category records with CRUD operations and default seeding
2. **Budget Limits & Alerts** — monthly spending caps per category with real-time alert status
3. **Recurring Expenses** — template-driven auto-generation of expenses via a daily APScheduler background job
4. **Reports & Analytics** — aggregated financial summaries, category breakdowns, trend data, and chart payloads
5. **Export to CSV/PDF** — filtered expense data downloads with date range and category filters

---

## Glossary

- **API**: The FastAPI backend application serving all endpoints
- **Authenticated_User**: A user who has presented a valid JWT Bearer token in the request header
- **Budget_Limit**: A record associating a spending cap (`limit_amount`) with a specific category, month, and year for a user
- **Budget_Status**: A computed response showing real-time spending versus the budget limit for a category in a given month/year
- **Category**: A user-owned record with a name, color, and icon used to classify expense and income transactions
- **CategoryBreakdown**: A per-category aggregation of spending totals and percentages for a given month/year
- **CSV_Export**: A comma-separated values file containing filtered expense records
- **Default_Categories**: Eight system-seeded category records created for a user on their first category list request
- **Expense**: An existing transaction record in the `expenses` table with fields: id, title, amount, date, category, is_income, notes, user_id
- **MonthlySummary**: An aggregated response containing total income, total expenses, net balance, transaction count, and top expense category for a given month/year
- **MonthlyTrend**: A per-month aggregation of income and expense totals for a given year, used for trend charts
- **PDF_Export**: A PDF document containing filtered expense records with summary totals
- **Recurring_Template**: A record defining a repeating expense or income entry with a frequency, start date, and next due date
- **Scheduler**: The APScheduler background job that runs daily to generate expenses from active recurring templates
- **System**: The FastAPI backend application including all routers, service functions, and database interactions

---

## Requirements

### Requirement 1: Custom Expense Categories Management

**User Story:** As an authenticated user, I want to manage my own expense categories with custom names, colors, and icons, so that I can organise my transactions in a way that reflects my personal spending habits.

#### Acceptance Criteria

1. WHEN an Authenticated_User sends `GET /api/categories` and has no existing categories, THE System SHALL seed the eight Default_Categories for that user and return them as a `List[CategoryResponse]` with HTTP 200.
2. WHEN an Authenticated_User sends `GET /api/categories` and already has categories, THE System SHALL return only that user's categories as a `List[CategoryResponse]` with HTTP 200, never including categories belonging to any other user. *(Property 4)*
3. WHEN an Authenticated_User sends `POST /api/categories` with a valid `CategoryCreate` body, THE System SHALL persist the new category record with `user_id` set to the authenticated user's id and return a `CategoryResponse` with HTTP 201.
4. IF an Authenticated_User sends `POST /api/categories` with a `name` that is empty or exceeds 50 characters, THEN THE System SHALL return HTTP 422 with a Pydantic validation error detail.
5. WHEN an Authenticated_User sends `PUT /api/categories/{id}` for a category they own, THE System SHALL update the category's `name`, `color`, and/or `icon` fields and return the updated `CategoryResponse` with HTTP 200.
6. IF an Authenticated_User sends `PUT /api/categories/{id}` or `DELETE /api/categories/{id}` for a category id that does not exist or belongs to another user, THEN THE System SHALL return HTTP 404 with `{"detail": "Category not found or access denied"}`.
7. WHEN an Authenticated_User sends `DELETE /api/categories/{id}` for a category they own, THE System SHALL remove the category record and return HTTP 200 with `{"detail": "Category deleted successfully"}`, while all existing Expense records that referenced that category's name string SHALL remain unmodified. *(Property 9)*
8. THE System SHALL require a valid JWT Bearer token for all `/api/categories` endpoints and return HTTP 401 for unauthenticated requests.

---

### Requirement 2: Budget Limits & Alerts

**User Story:** As an authenticated user, I want to set monthly spending caps per category and receive real-time alert status when I am approaching or exceeding my budget, so that I can stay in control of my finances.

#### Acceptance Criteria

1. WHEN an Authenticated_User sends `GET /api/budgets/status?month=&year=`, THE System SHALL return a `List[BudgetStatusResponse]` where for each entry: `alert_level == "exceeded"` if `usage_percentage >= 1.0`; `alert_level == "warning"` if `usage_percentage >= alert_threshold` and `usage_percentage < 1.0`; and `alert_level == "ok"` otherwise. *(Property 1)*
2. WHEN an Authenticated_User sends `GET /api/budgets` or `GET /api/budgets/status`, THE System SHALL only return Budget_Limit records and compute Budget_Status values using Expense records that belong to the Authenticated_User, never including data from other users. *(Property 5)*
3. IF an Authenticated_User sends `POST /api/budgets` with a `category`, `month`, and `year` combination for which a Budget_Limit already exists for that user, THEN THE System SHALL return HTTP 409 with `{"detail": "Budget limit already exists for this category and period"}`. *(Property 10)*
4. WHEN an Authenticated_User sends `POST /api/budgets` with a valid `BudgetLimitCreate` body, THE System SHALL persist the Budget_Limit record with `user_id` set to the authenticated user's id and return a `BudgetLimitResponse` with HTTP 201.
5. WHEN an Authenticated_User sends `GET /api/budgets/status?month=&year=`, THE System SHALL compute `spent_amount` as the sum of all non-income Expense amounts for the authenticated user in the given category, month, and year; `remaining_amount` as `limit_amount - spent_amount`; and `usage_percentage` as `spent_amount / limit_amount`.
6. IF an Authenticated_User sends `POST /api/budgets` with `limit_amount <= 0`, `month` outside [1, 12], `year < 2000`, or `alert_threshold` outside [0.0, 1.0], THEN THE System SHALL return HTTP 422 with a Pydantic validation error detail.
7. WHEN an Authenticated_User sends `PUT /api/budgets/{id}` for a Budget_Limit they own, THE System SHALL update the record and return the updated `BudgetLimitResponse` with HTTP 200.
8. IF an Authenticated_User sends `PUT /api/budgets/{id}` or `DELETE /api/budgets/{id}` for a Budget_Limit id that does not exist or belongs to another user, THEN THE System SHALL return HTTP 404 with `{"detail": "Budget limit not found or access denied"}`.
9. WHEN an Authenticated_User sends `DELETE /api/budgets/{id}` for a Budget_Limit they own, THE System SHALL remove the record and return HTTP 200 with `{"detail": "Budget limit deleted successfully"}`.
10. THE System SHALL require a valid JWT Bearer token for all `/api/budgets` endpoints and return HTTP 401 for unauthenticated requests.

---

### Requirement 3: Recurring Expenses

**User Story:** As an authenticated user, I want to define recurring expense or income templates that automatically generate transaction entries on a daily, weekly, or monthly schedule, so that I do not have to manually enter predictable transactions.

#### Acceptance Criteria

1. WHEN the Scheduler calls `compute_next_due_date` with any valid `frequency` value (`"daily"`, `"weekly"`, or `"monthly"`) and any valid `current_due_date`, THE System SHALL return a date that is strictly greater than `current_due_date`. *(Property 2)*
2. WHEN the Scheduler runs `generate_due_recurring_expenses` and processes an active Recurring_Template, THE System SHALL advance the template's `next_due_date` before the job completes, so that a second execution of the job on the same day does not generate a duplicate Expense record for that template. *(Property 3)*
3. WHEN the Scheduler runs `generate_due_recurring_expenses`, THE System SHALL insert one new Expense record for each active Recurring_Template where `next_due_date <= today`, appending `" [auto-generated]"` to the template's `notes` field in the generated Expense.
4. WHEN the Scheduler runs `generate_due_recurring_expenses` and an individual template fails to generate, THE System SHALL log the error, skip that template, continue processing remaining templates, and return `{"generated": N, "errors": M}` where `N + M` equals the total number of due templates processed.
5. WHEN an Authenticated_User sends `POST /api/recurring` with a valid `RecurringTemplateCreate` body, THE System SHALL persist the Recurring_Template with `next_due_date` set to `start_date`, `is_active` set to `True`, and `user_id` set to the authenticated user's id, and return a `RecurringTemplateResponse` with HTTP 201.
6. IF an Authenticated_User sends `POST /api/recurring` with a `frequency` value other than `"daily"`, `"weekly"`, or `"monthly"`, THEN THE System SHALL return HTTP 422 with a Pydantic validation error detail.
7. IF an Authenticated_User sends `POST /api/recurring` with `amount <= 0`, THEN THE System SHALL return HTTP 422 with a Pydantic validation error detail.
8. WHEN an Authenticated_User sends `POST /api/recurring/{id}/pause` for a Recurring_Template they own, THE System SHALL set `is_active` to `False` and return the updated `RecurringTemplateResponse` with HTTP 200.
9. WHEN an Authenticated_User sends `POST /api/recurring/{id}/resume` for a Recurring_Template they own, THE System SHALL set `is_active` to `True` and return the updated `RecurringTemplateResponse` with HTTP 200.
10. IF an Authenticated_User sends any mutating request to `/api/recurring/{id}` for a template id that does not exist or belongs to another user, THEN THE System SHALL return HTTP 404 with `{"detail": "Recurring template not found or access denied"}`.
11. WHEN an Authenticated_User sends `GET /api/recurring`, THE System SHALL return only that user's Recurring_Template records as a `List[RecurringTemplateResponse]` with HTTP 200.
12. THE System SHALL require a valid JWT Bearer token for all `/api/recurring` endpoints and return HTTP 401 for unauthenticated requests.

---

### Requirement 4: Reports & Analytics

**User Story:** As an authenticated user, I want to view aggregated financial summaries, category breakdowns, income vs. expense trends, and chart-ready data for any month or year, so that I can understand my spending patterns and make informed financial decisions.

#### Acceptance Criteria

1. WHEN an Authenticated_User sends `GET /api/reports/monthly-summary?month=&year=`, THE System SHALL return a `MonthlySummaryResponse` where `net_balance == total_income - total_expenses`, `total_income` equals the sum of all income Expense amounts for the user in the given month/year, `total_expenses` equals the sum of all non-income Expense amounts, and the sum of all `total_amount` values in the corresponding `CategoryBreakdownResponse` list equals `total_expenses`. *(Property 6)*
2. WHEN an Authenticated_User sends `GET /api/reports/monthly-summary?month=&year=` and there are no Expense records for that period, THE System SHALL return a `MonthlySummaryResponse` with `total_income = 0.0`, `total_expenses = 0.0`, `net_balance = 0.0`, `transaction_count = 0`, and `top_expense_category = null`.
3. WHEN an Authenticated_User sends `GET /api/reports/category-breakdown?month=&year=`, THE System SHALL return a `List[CategoryBreakdownResponse]` sorted by `total_amount` descending, where each entry's `percentage_of_total` equals `(total_amount / grand_total_expenses) * 100` and the sum of all `percentage_of_total` values equals 100.0 (within floating-point tolerance).
4. WHEN an Authenticated_User sends `GET /api/reports/income-vs-expense?year=`, THE System SHALL return a `List[MonthlyTrendResponse]` containing one entry per month that has Expense records for the authenticated user in the given year, with each entry's `net_balance == total_income - total_expenses`.
5. WHEN an Authenticated_User sends `GET /api/reports/chart-data?month=&year=&type=`, THE System SHALL return a `ChartDataResponse` where `chart_type` is one of `"pie"`, `"bar"`, or `"line"`, `labels` is a non-empty list of strings, and each dataset entry contains `label`, `data`, and `colors` fields.
6. IF an Authenticated_User sends `GET /api/reports/monthly-summary` or `GET /api/reports/category-breakdown` with `month` outside [1, 12] or `year < 2000`, THEN THE System SHALL return HTTP 422 with a validation error detail.
7. THE System SHALL require a valid JWT Bearer token for all `/api/reports` endpoints and return HTTP 401 for unauthenticated requests.

---

### Requirement 5: Export to CSV and PDF

**User Story:** As an authenticated user, I want to download my expense data as a CSV or PDF file filtered by date range, category, and income type, so that I can analyse my transactions in external tools or share them as reports.

#### Acceptance Criteria

1. WHEN an Authenticated_User sends `GET /api/export/csv` with valid query parameters, THE System SHALL return a `StreamingResponse` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="expenses_{start_date}_{end_date}.csv"`, where the CSV contains a header row `id,title,amount,date,category,is_income,notes` followed by exactly one data row per Expense record matching all applied filters, ordered by `date` ascending. *(Property 7)*
2. IF an Authenticated_User sends `GET /api/export/csv` or `GET /api/export/pdf` with `start_date > end_date`, THEN THE System SHALL return HTTP 422 with a validation error detail. *(Property 8)*
3. WHEN an Authenticated_User sends `GET /api/export/csv` and no Expense records match the given filters, THE System SHALL return HTTP 200 with a CSV containing only the header row and no data rows.
4. WHEN an Authenticated_User sends `GET /api/export/pdf` with valid query parameters, THE System SHALL return a `StreamingResponse` with `Content-Type: application/pdf` and `Content-Disposition: attachment; filename="expenses_{start_date}_{end_date}.pdf"`, where the PDF includes a title with the user's name and date range, summary totals (total income, total expenses, net balance), and a table of all matching Expense records.
5. WHEN an Authenticated_User sends `GET /api/export/pdf` and no Expense records match the given filters, THE System SHALL return HTTP 200 with a PDF document containing the title, summary section, and a "No records found" message in place of the data table.
6. IF the `reportlab` library is not installed and an Authenticated_User sends `GET /api/export/pdf`, THEN THE System SHALL return HTTP 500 with `{"detail": "PDF export is not available. Install reportlab."}`.
7. WHERE the `category` query parameter is provided, THE System SHALL filter exported records to only those whose `category` field matches the given value exactly.
8. WHERE the `is_income` query parameter is provided, THE System SHALL filter exported records to only those whose `is_income` field matches the given boolean value.
9. THE System SHALL require a valid JWT Bearer token for all `/api/export` endpoints and return HTTP 401 for unauthenticated requests.
