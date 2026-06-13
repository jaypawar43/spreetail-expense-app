# AI_USAGE.md — AI Tools Used, Key Prompts & Corrections

## AI Tools Used in Development

### 1. Antigravity (Google DeepMind) — Primary Development Assistant
- **Used for:** Code generation, architecture design, anomaly detection logic, documentation
- **Model:** Claude Opus 4.6 (Thinking)
- **Integration:** Direct code generation and planning

### 2. OpenAI GPT-3.5/4 — Runtime AI Features
- **Used for:** In-app anomaly detection enhancement, expense categorization
- **Integration:** API calls during CSV import for semantic analysis
- **Note:** Optional — app works fully without it using rule-based fallback

---

## Key Prompts Used

### Prompt 1: Anomaly Detection Strategy
```
"Analyze these expense records for a shared apartment and identify data quality issues.
Look for:
1. Semantic duplicates (same expense logged differently by different people)
2. Suspicious patterns (unusually high amounts, wrong categorization)
3. Inconsistencies between description and amount
4. Any other data quality concerns

Return a JSON array of issues found..."
```
**Purpose:** Runtime LLM analysis of imported CSV data to find issues that rule-based detection might miss.

### Prompt 2: Expense Categorization
```
"Categorize these apartment expenses into one of these categories:
- Rent, Utilities, Groceries, Food & Dining, Transportation, 
  Entertainment, Household, Travel, Settlement, Other

Return a JSON object mapping row numbers to categories."
```
**Purpose:** Auto-categorize expenses using LLM intelligence rather than keyword matching.

### Prompt 3: Architecture Planning
```
"Build me a full-stack Expense Splitter web app... [full requirements]"
```
**Purpose:** Initial project planning, architecture decisions, and code generation.

---

## 3 Cases Where AI Was Wrong & Corrections Applied

### Case 1: Date Parsing — Assumed MM-DD-YYYY Format

**What AI initially did:**
The initial date parser used Python's `dateutil.parse()` without specifying `dayfirst=True`. This meant dates like "08-02-2026" were parsed as **August 2** instead of **February 8** (Indian DD-MM-YYYY format).

**The problem:**
```python
# AI's initial code:
from dateutil import parser
parsed = parser.parse("08-02-2026")  # → 2026-08-02 (WRONG for Indian dates)
```

**How it was corrected:**
Added explicit DD-MM-YYYY regex matching as the primary parser, and set `dayfirst=True` on the dateutil fallback:
```python
# Corrected code:
# 1. Try DD-MM-YYYY regex first
dd_mm_yyyy = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})$', date_str)
if dd_mm_yyyy:
    day, month, year = int(groups...)
    return date(year, month, day)

# 2. Fallback with dayfirst=True
parsed = date_parser.parse(date_str, dayfirst=True)
```

**Lesson:** Always be explicit about date format assumptions, especially for regional formats.

---

### Case 2: Duplicate Detection — Too Aggressive Matching

**What AI initially did:**
The first version of duplicate detection used a 50% similarity threshold, which flagged completely different expenses as duplicates just because they had a few common words (e.g., "Groceries BigBasket Feb" and "Groceries DMart Mar" were both flagged).

**The problem:**
```python
# AI's initial code:
if similarity >= 50:  # Too low threshold
    flag_as_duplicate()
# Result: 15+ false positive duplicates flagged
```

**How it was corrected:**
1. Raised the similarity threshold to 70%
2. Added the requirement that **both date AND amount** must match (not just description similarity)
3. Used `token_sort_ratio` instead of `ratio` for word-order independence

```python
# Corrected code:
if (seen['date'] == parsed_date and 
    seen['amount'] == parsed_amount and 
    fuzz.token_sort_ratio(description, seen['description']) >= 70):
    flag_as_duplicate()
# Result: Only true duplicates flagged (rows 5-6, 24-25)
```

**Lesson:** Fuzzy matching needs multiple confirming signals, not just text similarity.

---

### Case 3: Settlement Detection — Missed "Deposit" as Settlement

**What AI initially did:**
The initial settlement detector only looked for keywords "paid" and "settlement" in the description. It missed "Sam deposit share" (row 38) because "deposit" wasn't in the keyword list.

**The problem:**
```python
# AI's initial code:
is_settlement = any(kw in description for kw in ['paid', 'settlement', 'transfer'])
# "Sam deposit share" → NOT detected as settlement
```

Also, the initial logic only checked the description field, not the notes field where "this is a settlement not an expense" was written.

**How it was corrected:**
1. Added "deposit" and "paid back" to the keyword list
2. Extended detection to also check the `notes` field
3. Added the rule: if `split_type` is empty, it's likely a settlement

```python
# Corrected code:
if not split_type:
    is_settlement = True
if any(kw in description for kw in ['paid', 'settlement', 'transfer', 'paid back', 'deposit']):
    is_settlement = True
if any(kw in notes for kw in ['settlement', 'not an expense']):
    is_settlement = True
```

**Lesson:** Settlement detection needs to check multiple fields and have a broader keyword vocabulary.

---

## AI Usage Statistics

| Metric | Value |
|--------|-------|
| Total AI-assisted files generated | 25+ |
| Lines of code generated | ~3,000+ |
| Manual corrections needed | 3 significant (documented above) |
| Architecture iterations | 1 planning phase + 1 execution phase |
| Documentation files auto-generated | 4 (README, SCOPE, DECISIONS, AI_USAGE) |

## Ethical Considerations

- **Transparency:** All AI-generated code was reviewed and tested before inclusion
- **Fallback design:** The app works without AI/LLM features using rule-based detection
- **No data sent externally without consent:** OpenAI API calls only happen if the user provides an API key
- **Corrections documented:** This file honestly documents where AI was wrong
