# DECISIONS.md — Technical Decision Log

Each decision documents what options were considered, the trade-offs, and why the final choice was made.

---

## Decision 1: Database — SQLite vs PostgreSQL

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **SQLite** | Zero setup, file-based, great for dev | No concurrent writes, limited types |
| **PostgreSQL** | Production-ready, JSONB support, Render-native | Requires setup, heavier |
| **MySQL** | Widely used | Less Django-idiomatic, no native JSONB |

### Decision: SQLite for dev, PostgreSQL for production
**Rationale:** SQLite requires zero configuration for local development and is perfect for the assignment's scope. PostgreSQL is used in production (Render) via the `DATABASE_URL` environment variable. Django's ORM abstracts the difference — switching is a one-line `.env` change. The `dj-database-url` package handles the connection string parsing.

---

## Decision 2: Anomaly Detection — Rule-Based vs Pure LLM

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **Pure rule-based** | Deterministic, fast, no API cost | Misses semantic duplicates |
| **Pure LLM** | Smart, catches subtle issues | Slow, expensive, non-deterministic |
| **Hybrid (rule-based + LLM)** | Best of both worlds | More complex code |

### Decision: Hybrid with rule-based primary, LLM enhancement optional
**Rationale:** Rule-based detection catches 90% of anomalies reliably and instantly. The LLM layer adds value for semantic duplicate detection and expense categorization but isn't required for the app to function. This means the app works offline/without API keys while being smarter when the key is provided. The LLM integration is wrapped in a try/catch to never block the import pipeline.

---

## Decision 3: Date Parsing Strategy

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **Strict DD-MM-YYYY only** | Simple, no ambiguity | Rejects valid-but-messy data |
| **Python dateutil with dayfirst=True** | Handles many formats | Can misinterpret ambiguous dates |
| **Custom parser with fallback chain** | Handles known edge cases | More code |

### Decision: Custom parser with DD-MM-YYYY primary, dateutil fallback
**Rationale:** The CSV data is Indian-format (DD-MM-YYYY) but contains malformed entries like "Mar-14". Our parser tries DD-MM-YYYY first, then handles known patterns (Mon-DD), and falls back to `dateutil` with `dayfirst=True`. Ambiguous dates are flagged rather than silently misinterpreted.

---

## Decision 4: Duplicate Detection Algorithm

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **Exact match** | Fast, no false positives | Misses "Dinner at Marina Bite" vs "dinner - marina bites" |
| **Levenshtein distance** | Good for typos | Slow for many comparisons |
| **Token sort ratio (thefuzz)** | Order-independent, handles rearrangement | Some false positives |

### Decision: Token sort ratio with 70% threshold + same date + same amount
**Rationale:** `thefuzz.fuzz.token_sort_ratio` tokenizes and sorts words before comparing, which correctly matches "Dinner at Marina Bite" with "dinner - marina bites". Requiring same date AND same amount significantly reduces false positives. The 70% threshold was tuned on the sample data.

---

## Decision 5: Split Calculation for Edge Cases

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **Reject incomplete splits** | Clean data only | Loses data |
| **Equal fallback for unspecified** | Always produces numbers | May not match intent |
| **Remainder distribution** | Fair to specified people | Complex |

### Decision: Remainder distribution to unspecified people
**Rationale:** When split_details are incomplete (e.g., unequal split with only some amounts specified), the remaining amount is split equally among people without specified amounts. For percentage splits, missing percentages get an equal share of the remaining percentage. This preserves the data owner's intent while being fair.

---

## Decision 6: Frontend Framework — CRA vs Vite vs Next.js

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **Create React App** | Well-known | Deprecated, slow builds |
| **Vite** | Fast HMR, modern, lightweight | Less opinionated |
| **Next.js** | SSR, file-based routing | Overkill for SPA |

### Decision: Vite
**Rationale:** Vite offers near-instant HMR, fast builds, and native ESM support. Since this is a client-side SPA that talks to a separate Django API, we don't need SSR. Vite's dev proxy feature cleanly forwards `/api` requests to the Django backend during development.

---

## Decision 7: State Management — Context vs Redux vs Local State

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **Redux** | Predictable, devtools | Boilerplate, overkill |
| **Context API** | Built-in, simple | Re-render issues at scale |
| **Local state + prop drilling** | Simplest, no deps | Prop passing |
| **Zustand/Jotai** | Lightweight | Extra dependency |

### Decision: Local state with prop drilling
**Rationale:** The app has a simple data flow: upload → report → dashboard → balances. There are only 5 components and the shared state is minimal (importSession + anomalyCount). This doesn't warrant a state management library. If the app grows, migrating to Context or Zustand would be straightforward.

---

## Decision 8: Settlement Algorithm

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **Pairwise debts** | Tracks exact flows | O(n²) transactions |
| **Net balance + greedy matching** | Minimal transactions | May not be globally optimal |
| **Min-cost max-flow** | Optimal | Complex to implement |

### Decision: Net balance with greedy matching
**Rationale:** Compute each person's net balance (paid − owed), then greedily match the largest debtor with the largest creditor. This produces near-optimal settlements (often optimal for ≤6 people) and is simple to implement and explain. For our 4-6 person use case, this is effectively optimal.

---

## Decision 9: Multi-Currency Handling

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **Reject mixed currencies** | Simple | Loses Goa trip data |
| **Store in original, convert at display** | Accurate | Complex queries |
| **Convert at import time** | Simple queries | Loses original |
| **Store original + convert at settlement** | Best of both | Slightly more complex |

### Decision: Store in original currency, convert at settlement calculation time
**Rationale:** Expenses are stored in their original currency (INR or USD). The balance calculator converts everything to INR using a configurable exchange rate (default: 1 USD = 83 INR) when computing settlements. This preserves the original data while providing unified settlement amounts. The rate is editable from the UI.

---

## Decision 10: CSS Framework — Vanilla CSS vs Tailwind vs Material UI

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| **Vanilla CSS** | Full control | Verbose |
| **Tailwind CSS** | Utility-first, fast styling | Learning curve |
| **Material UI** | Pre-built components | Heavy, opinionated |
| **Chakra UI** | Nice API | Extra dependency |

### Decision: Tailwind CSS v3
**Rationale:** User requested Tailwind. It's utility-first which keeps component files self-contained, has excellent dark mode support, and the JIT compiler means only used classes are in the bundle. We supplement with custom CSS for glassmorphism effects and animations.
