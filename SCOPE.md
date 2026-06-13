# SCOPE.md — Project Scope, Anomaly Log & Database Schema

## Project Scope

### What the App Does
1. **CSV Upload & Ingestion** — Parses messy expense CSV data and imports into a structured database
2. **Anomaly Detection** — Detects 14+ types of data quality issues using rule-based + optional AI analysis
3. **Import Report** — Color-coded report showing every anomaly found and action taken
4. **Expense Dashboard** — Filterable table view of all expenses
5. **Balance Calculator** — Computes net balances and simplified settlement plan
6. **Person Management** — Tracks roommates (permanent) and guests (temporary)

### What the App Does NOT Do
- Real-time multi-user collaboration
- Receipt/photo upload
- Recurring expense automation
- Bank account integration
- Mobile-native app (it's responsive web)

---

## Database Schema

### Person
| Column | Type | Description |
|--------|------|-------------|
| id | BigAutoField | Primary key |
| name | CharField(100) | Unique person name |
| is_permanent | BooleanField | True = roommate, False = guest |
| joined_date | DateField (nullable) | When they joined the house |
| left_date | DateField (nullable) | When they left |
| created_at | DateTimeField | Auto-set on creation |

### ImportSession
| Column | Type | Description |
|--------|------|-------------|
| id | BigAutoField | Primary key |
| filename | CharField(255) | Original CSV filename |
| uploaded_at | DateTimeField | Auto-set |
| total_rows | IntegerField | Total data rows in CSV |
| imported_rows | IntegerField | Successfully imported |
| skipped_rows | IntegerField | Skipped due to errors |
| flagged_rows | IntegerField | Imported but flagged |
| auto_fixed_rows | IntegerField | Auto-corrected |
| status | CharField(20) | processing / completed / failed |
| error_message | TextField | Error details if failed |

### Expense
| Column | Type | Description |
|--------|------|-------------|
| id | BigAutoField | Primary key |
| import_session | FK → ImportSession | Which import this came from |
| date | DateField | Expense date |
| description | TextField | What was paid for |
| paid_by | FK → Person (nullable) | Who paid |
| amount | DecimalField(12,2) | Amount in original currency |
| currency | CharField(3) | INR or USD |
| split_type | CharField(20, nullable) | equal / unequal / percentage / share |
| split_with_raw | TextField | Raw split_with from CSV |
| split_details_raw | TextField | Raw split_details from CSV |
| notes | TextField | Notes from CSV |
| is_settlement | BooleanField | True if this is a transfer |
| is_flagged | BooleanField | True if has warnings |
| original_row | IntegerField | CSV row number |
| raw_data | JSONField | Original CSV row as JSON |
| category | CharField(100) | AI-assigned category |

### SplitDetail
| Column | Type | Description |
|--------|------|-------------|
| id | BigAutoField | Primary key |
| expense | FK → Expense | Parent expense |
| person | FK → Person | Who owes this share |
| amount | DecimalField(12,2) | Calculated share amount |
| percentage | DecimalField(5,2, nullable) | If percentage split |
| share_units | DecimalField(5,2, nullable) | If share split |

### Anomaly
| Column | Type | Description |
|--------|------|-------------|
| id | BigAutoField | Primary key |
| import_session | FK → ImportSession | Which import |
| expense | FK → Expense (nullable) | Related expense if applicable |
| row_number | IntegerField | CSV row number |
| anomaly_type | CharField(30) | See types below |
| severity | CharField(10) | error / warning / info |
| description | TextField | Human-readable explanation |
| action_taken | CharField(20) | skipped / flagged / auto_fixed / normalized |
| original_value | TextField | What was in the CSV |
| fixed_value | TextField | What it was changed to |

### AppConfiguration
| Column | Type | Description |
|--------|------|-------------|
| id | BigAutoField | Primary key |
| key | CharField(100) | Config key (e.g., USD_TO_INR_RATE) |
| value | CharField(500) | Config value |
| description | TextField | What this config does |

---

## Complete Anomaly Log (from sample CSV)

The following anomalies are detected when importing the provided `Expenses Export.csv`:

### Row 5–6: Duplicate Entry
- **Type:** `duplicate`
- **Severity:** Warning
- **Issue:** "Dinner at Marina Bite" (row 5, Dev, ₹3200) and "dinner - marina bites" (row 6, Dev, ₹3200) — same date, same amount, fuzzy match similarity ~80%
- **Action:** Row 6 flagged as possible duplicate

### Row 9: Case Inconsistency
- **Type:** `case_inconsistency`
- **Severity:** Info
- **Issue:** `paid_by` is "priya" (lowercase) instead of "Priya"
- **Action:** Auto-normalized to "Priya"

### Row 11: Name Suffix
- **Type:** `case_inconsistency`
- **Severity:** Info
- **Issue:** `paid_by` is "Priya S" — looks like "Priya" with suffix "S"
- **Action:** Auto-normalized to "Priya"

### Row 12: Missing Split Person
- **Type:** `missing_split_person`
- **Severity:** Warning
- **Issue:** Aisha birthday cake: split_type is "unequal", split_details has "Rohan 700; Priya 400" but Meera has no amount specified
- **Action:** Flagged — Meera gets the remainder (₹400)

### Row 13: Missing Payer
- **Type:** `missing_payer`
- **Severity:** Warning
- **Issue:** House cleaning supplies has no `paid_by` value — "can't remember who paid"
- **Action:** Flagged for manual review

### Row 14: Settlement Row
- **Type:** `settlement_row`
- **Severity:** Info
- **Issue:** "Rohan paid Aisha back" — no split_type, notes say "settlement not an expense"
- **Action:** Marked as settlement, excluded from split calculations

### Row 15: Percentage Incomplete
- **Type:** `percentage_incomplete`
- **Severity:** Warning
- **Issue:** Pizza Friday: percentage split with "Aisha 30%; Rohan 30%" — only 60% specified for 4 people
- **Action:** Flagged — Priya and Meera each get 20% of remaining

### Row 5, 6, 19, 20, 23: Guest/Temporary People
- **Type:** `guest_person`
- **Severity:** Info
- **Issue:** Dev, Kabir, Sam appear in expenses but aren't permanent roommates
- **Action:** Auto-created as guest persons

### Row 23: Compound Guest Name
- **Type:** `guest_person`
- **Severity:** Info
- **Issue:** "Dev's friend Kabir" — compound name with friend reference
- **Action:** Extracted "Kabir" as the actual guest name

### Row 24–25: Possible Duplicate Log
- **Type:** `possible_duplicate_log`
- **Severity:** Warning
- **Issue:** "Dinner at Thalassa" (Aisha, ₹2400) and "Thalassa dinner" (Rohan, ₹2450) on same date — notes say "Aisha also logged this"
- **Action:** Flagged for review (different payers, could be separate bills or double-logged)

### Row 26: Negative Amount
- **Type:** `negative_amount`
- **Severity:** Warning
- **Issue:** Parasailing refund = -30 USD
- **Action:** Flagged as possible refund, imported as-is

### Row 27: Malformed Date
- **Type:** `malformed_date`
- **Severity:** Warning
- **Issue:** Date is "Mar-14" instead of DD-MM-YYYY format
- **Action:** Auto-fixed to 2026-03-14 (assumed year 2026 from context)

### Row 27: Case Inconsistency
- **Type:** `case_inconsistency`
- **Severity:** Info
- **Issue:** `paid_by` is "rohan" (lowercase)
- **Action:** Auto-normalized to "Rohan"

### Row 28: Missing Currency
- **Type:** `missing_currency`
- **Severity:** Warning
- **Issue:** Groceries DMart has no currency specified — "forgot to set currency"
- **Action:** Auto-fixed to INR (most common currency in dataset)

### Row 31: Zero Amount
- **Type:** `zero_amount`
- **Severity:** Warning
- **Issue:** Dinner order Swiggy has amount = 0 — "counted twice earlier"
- **Action:** Flagged as possible correction entry

### Row 32: Percentage Incomplete
- **Type:** `percentage_incomplete`
- **Severity:** Warning
- **Issue:** Weekend brunch: "Aisha 30%; Rohan 30%; Priya 30%; Meera" — Meera has no percentage, total specified = 90%
- **Action:** Flagged — Meera assigned remaining 10%

### Row 34: Ambiguous Date
- **Type:** `ambiguous_date`
- **Severity:** Warning
- **Issue:** Date is "04-05-2026" and notes say "is this April 5 or May?" — DD-MM vs MM-DD ambiguity
- **Action:** Flagged — parsed as May 4 (DD-MM format per Indian convention)

### Row 36: Departed Person
- **Type:** `departed_person`
- **Severity:** Warning
- **Issue:** Groceries BigBasket includes Meera in split_with — notes say "oops Meera still in the list"
- **Action:** Flagged for review

### Row 38: Settlement Row
- **Type:** `settlement_row`
- **Severity:** Info
- **Issue:** "Sam deposit share" — Sam paying deposit to Aisha
- **Action:** Marked as settlement

### Row 42: Split Mismatch
- **Type:** `split_mismatch`
- **Severity:** Error
- **Issue:** Furniture for common room: split_type is "equal" but split_details say "Aisha 1; Rohan 1; Priya 1" — notes confirm "split_type says equal but details say otherwise"
- **Action:** Flagged — the split_details suggest a share-based split (1:1:1), which is equal, but Sam is missing from details while being in split_with

### Mixed Currency (Post-Processing)
- **Type:** `mixed_currency`
- **Severity:** Info
- **Issue:** Dates 09-03-2026 to 12-03-2026 have both INR and USD expenses (Goa trip)
- **Action:** Imported as-is, converted using configurable exchange rate (1 USD = 83 INR)
