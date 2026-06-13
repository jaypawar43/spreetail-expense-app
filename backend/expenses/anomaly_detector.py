"""
Anomaly Detection Engine for CSV expense data.

Implements 12+ rule-based detections for data quality issues.
Can optionally enhance detection with LLM-based analysis.
"""

import re
from decimal import Decimal, InvalidOperation
from datetime import date
from dateutil import parser as date_parser
from thefuzz import fuzz


# Known permanent roommates
PERMANENT_MEMBERS = {'Aisha', 'Rohan', 'Priya', 'Meera'}


def normalize_name(name):
    """Normalize a person's name to title case, strip whitespace."""
    if not name:
        return ''
    name = name.strip()
    # Handle names like "Priya S" -> "Priya S"
    # Handle names like "priya" -> "Priya"
    # Handle names like "rohan" -> "Rohan"
    return name.title() if name.islower() or name.isupper() else name.strip()


def parse_date_flexible(date_str):
    """
    Try to parse a date string in various formats.
    Returns (date_obj, was_ambiguous, original_format_issue).
    """
    if not date_str or not date_str.strip():
        return None, False, "Empty date"

    date_str = date_str.strip()

    # Try DD-MM-YYYY first (the expected format)
    dd_mm_yyyy = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})$', date_str)
    if dd_mm_yyyy:
        day, month, year = int(dd_mm_yyyy.group(1)), int(dd_mm_yyyy.group(2)), int(dd_mm_yyyy.group(3))
        try:
            return date(year, month, day), False, None
        except ValueError:
            pass

    # Try Mon-DD format (malformed like "Mar-14")
    mon_dd = re.match(r'^([A-Za-z]{3})-(\d{1,2})$', date_str)
    if mon_dd:
        try:
            # Assume current year context (2026)
            parsed = date_parser.parse(f"{mon_dd.group(1)} {mon_dd.group(2)} 2026")
            return parsed.date(), True, f"Malformed date '{date_str}' - assumed year 2026"
        except (ValueError, TypeError):
            pass

    # Try generic parsing as fallback
    try:
        parsed = date_parser.parse(date_str, dayfirst=True)
        return parsed.date(), False, None
    except (ValueError, TypeError):
        return None, False, f"Cannot parse date: '{date_str}'"


def parse_amount(amount_str):
    """Parse amount string to Decimal. Returns (amount, issue)."""
    if not amount_str or not str(amount_str).strip():
        return None, "Empty amount"
    try:
        amount = Decimal(str(amount_str).strip().replace(',', ''))
        return amount, None
    except (InvalidOperation, ValueError):
        return None, f"Cannot parse amount: '{amount_str}'"


def parse_split_with(split_with_str):
    """Parse the split_with field into a list of names."""
    if not split_with_str or not str(split_with_str).strip():
        return []
    return [normalize_name(n) for n in str(split_with_str).split(';') if n.strip()]


def parse_split_details(split_details_str):
    """
    Parse split_details into a dict of {name: value}.
    Handles formats like:
      - "Rohan 700; Priya 400"
      - "Aisha 30%; Rohan 30%"
      - "Aisha 1; Rohan 2; Priya 1"
    """
    if not split_details_str or not str(split_details_str).strip():
        return {}

    details = {}
    parts = str(split_details_str).split(';')

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Try "Name Value%" or "Name Value" pattern
        match = re.match(r'^([A-Za-z\s\']+?)\s+([\d.]+)(%)?$', part)
        if match:
            name = normalize_name(match.group(1))
            value = Decimal(match.group(2))
            is_percentage = match.group(3) == '%'
            details[name] = {'value': value, 'is_percentage': is_percentage}
        else:
            # Just a name with no value (like "Meera" with no percentage)
            name = normalize_name(part)
            if name:
                details[name] = {'value': None, 'is_percentage': False}

    return details


class AnomalyDetector:
    """
    Rule-based anomaly detection for expense data.

    Processes rows and returns a list of anomaly dicts:
    {
        'row_number': int,
        'anomaly_type': str,
        'severity': str,  # 'error', 'warning', 'info'
        'description': str,
        'action_taken': str,  # 'skipped', 'flagged', 'auto_fixed', 'normalized', 'imported_as_is'
        'original_value': str,
        'fixed_value': str,
    }
    """

    def __init__(self):
        self.seen_expenses = []  # For duplicate detection
        self.anomalies = []
        self.currencies_by_group = {}  # Track currency mixing

    def detect_all(self, row, row_number):
        """
        Run all anomaly detections on a single CSV row.
        Returns (cleaned_row, anomalies_list, should_skip).
        """
        anomalies = []
        cleaned = dict(row)
        should_skip = False

        # 1. Date checks
        date_anomalies, parsed_date = self._check_date(row, row_number)
        anomalies.extend(date_anomalies)
        if parsed_date:
            cleaned['_parsed_date'] = parsed_date
        else:
            anomalies.append({
                'row_number': row_number,
                'anomaly_type': 'malformed_date',
                'severity': 'error',
                'description': f"Cannot parse date '{row.get('date', '')}'. Row skipped.",
                'action_taken': 'skipped',
                'original_value': row.get('date', ''),
                'fixed_value': '',
            })
            should_skip = True
            return cleaned, anomalies, should_skip

        # 2. Amount checks
        amount_anomalies, parsed_amount = self._check_amount(row, row_number)
        anomalies.extend(amount_anomalies)
        if parsed_amount is not None:
            cleaned['_parsed_amount'] = parsed_amount
        else:
            should_skip = True
            return cleaned, anomalies, should_skip

        # 3. Currency check
        currency_anomalies = self._check_currency(row, row_number)
        anomalies.extend(currency_anomalies)
        if not row.get('currency', '').strip():
            cleaned['currency'] = 'INR'

        # 4. Payer checks
        payer_anomalies = self._check_payer(row, row_number)
        anomalies.extend(payer_anomalies)

        # 5. Name case inconsistency
        case_anomalies = self._check_name_case(row, row_number)
        anomalies.extend(case_anomalies)

        # 6. Settlement detection
        settlement_anomalies, is_settlement = self._check_settlement(row, row_number)
        anomalies.extend(settlement_anomalies)
        cleaned['_is_settlement'] = is_settlement

        # 7. Zero / negative amount
        sign_anomalies = self._check_amount_sign(parsed_amount, row, row_number)
        anomalies.extend(sign_anomalies)

        # 8. Split type mismatches
        split_anomalies = self._check_split_consistency(row, row_number)
        anomalies.extend(split_anomalies)

        # 9. Missing persons in split details
        person_anomalies = self._check_split_persons(row, row_number)
        anomalies.extend(person_anomalies)

        # 10. Guest/temporary people
        guest_anomalies = self._check_guests(row, row_number)
        anomalies.extend(guest_anomalies)

        # 11. Ambiguous dates in notes
        notes_anomalies = self._check_notes_for_ambiguity(row, row_number)
        anomalies.extend(notes_anomalies)

        # 12. Duplicate detection
        dup_anomalies = self._check_duplicates(row, row_number, parsed_date, parsed_amount)
        anomalies.extend(dup_anomalies)

        # 13. Percentage completeness
        pct_anomalies = self._check_percentage_completeness(row, row_number)
        anomalies.extend(pct_anomalies)

        # 14. Departed person still in split
        dept_anomalies = self._check_departed_person(row, row_number, parsed_date)
        anomalies.extend(dept_anomalies)

        # Store for duplicate detection
        self.seen_expenses.append({
            'row_number': row_number,
            'date': parsed_date,
            'amount': parsed_amount,
            'description': row.get('description', '').strip().lower(),
            'paid_by': normalize_name(row.get('paid_by', '')),
        })

        return cleaned, anomalies, should_skip

    def _check_date(self, row, row_number):
        """Check for malformed or ambiguous dates."""
        anomalies = []
        date_str = row.get('date', '').strip()
        parsed_date, was_ambiguous, issue = parse_date_flexible(date_str)

        if parsed_date and was_ambiguous:
            anomalies.append({
                'row_number': row_number,
                'anomaly_type': 'malformed_date',
                'severity': 'warning',
                'description': issue or f"Date '{date_str}' required interpretation.",
                'action_taken': 'auto_fixed',
                'original_value': date_str,
                'fixed_value': str(parsed_date),
            })

        return anomalies, parsed_date

    def _check_amount(self, row, row_number):
        """Check for unparseable amounts."""
        amount_str = row.get('amount', '')
        parsed_amount, issue = parse_amount(amount_str)

        if issue and parsed_amount is None:
            return [{
                'row_number': row_number,
                'anomaly_type': 'other',
                'severity': 'error',
                'description': issue,
                'action_taken': 'skipped',
                'original_value': str(amount_str),
                'fixed_value': '',
            }], None

        return [], parsed_amount

    def _check_currency(self, row, row_number):
        """Check for missing currency."""
        currency = row.get('currency', '').strip()
        if not currency:
            return [{
                'row_number': row_number,
                'anomaly_type': 'missing_currency',
                'severity': 'warning',
                'description': f"Missing currency for '{row.get('description', '')}'. Defaulting to INR.",
                'action_taken': 'auto_fixed',
                'original_value': '',
                'fixed_value': 'INR',
            }]
        return []

    def _check_payer(self, row, row_number):
        """Check for missing payer."""
        paid_by = row.get('paid_by', '').strip()
        if not paid_by:
            return [{
                'row_number': row_number,
                'anomaly_type': 'missing_payer',
                'severity': 'warning',
                'description': f"No payer specified for '{row.get('description', '')}'. Row flagged for review.",
                'action_taken': 'flagged',
                'original_value': '',
                'fixed_value': '',
            }]
        return []

    def _check_name_case(self, row, row_number):
        """Check for case inconsistencies in names."""
        anomalies = []
        paid_by = row.get('paid_by', '').strip()

        if paid_by and paid_by != normalize_name(paid_by) and paid_by.lower() != paid_by:
            pass  # Mixed case is fine

        if paid_by and paid_by.islower():
            anomalies.append({
                'row_number': row_number,
                'anomaly_type': 'case_inconsistency',
                'severity': 'info',
                'description': f"Payer name '{paid_by}' is lowercase. Normalized to '{normalize_name(paid_by)}'.",
                'action_taken': 'normalized',
                'original_value': paid_by,
                'fixed_value': normalize_name(paid_by),
            })

        # Check suffix like "Priya S"
        normalized = normalize_name(paid_by)
        for known in PERMANENT_MEMBERS:
            if normalized != known and normalized.startswith(known) and len(normalized) > len(known):
                suffix = normalized[len(known):]
                if len(suffix.strip()) <= 2:
                    anomalies.append({
                        'row_number': row_number,
                        'anomaly_type': 'case_inconsistency',
                        'severity': 'info',
                        'description': f"Payer '{paid_by}' looks like '{known}' with suffix '{suffix.strip()}'. Normalized to '{known}'.",
                        'action_taken': 'normalized',
                        'original_value': paid_by,
                        'fixed_value': known,
                    })

        return anomalies

    def _check_settlement(self, row, row_number):
        """Detect settlement/transfer rows."""
        split_type = row.get('split_type', '').strip().lower()
        description = row.get('description', '').strip().lower()
        notes = row.get('notes', '').strip().lower()

        is_settlement = False

        # No split_type + description mentions "paid" or "settlement"
        if not split_type:
            is_settlement = True
        if any(kw in description for kw in ['paid', 'settlement', 'transfer', 'paid back', 'deposit']):
            is_settlement = True
        if any(kw in notes for kw in ['settlement', 'not an expense']):
            is_settlement = True

        anomalies = []
        if is_settlement:
            anomalies.append({
                'row_number': row_number,
                'anomaly_type': 'settlement_row',
                'severity': 'info',
                'description': f"Row appears to be a settlement/transfer: '{row.get('description', '')}'.",
                'action_taken': 'normalized',
                'original_value': row.get('description', ''),
                'fixed_value': 'Marked as settlement',
            })

        return anomalies, is_settlement

    def _check_amount_sign(self, amount, row, row_number):
        """Check for zero or negative amounts."""
        anomalies = []

        if amount is not None and amount == 0:
            anomalies.append({
                'row_number': row_number,
                'anomaly_type': 'zero_amount',
                'severity': 'warning',
                'description': f"Zero amount for '{row.get('description', '')}'. Possibly a correction entry.",
                'action_taken': 'flagged',
                'original_value': str(amount),
                'fixed_value': '',
            })

        if amount is not None and amount < 0:
            anomalies.append({
                'row_number': row_number,
                'anomaly_type': 'negative_amount',
                'severity': 'warning',
                'description': f"Negative amount ({amount}) for '{row.get('description', '')}'. Could be a refund.",
                'action_taken': 'flagged',
                'original_value': str(amount),
                'fixed_value': '',
            })

        return anomalies

    def _check_split_consistency(self, row, row_number):
        """Check if split_type matches split_details."""
        anomalies = []
        split_type = row.get('split_type', '').strip().lower()
        split_details_raw = row.get('split_details', '').strip()
        split_with_raw = row.get('split_with', '').strip()

        if not split_type or not split_details_raw:
            return anomalies

        details = parse_split_details(split_details_raw)
        split_with = parse_split_with(split_with_raw)

        if split_type == 'equal' and details:
            # If split_type is "equal" but split_details has specific amounts
            values = [d['value'] for d in details.values() if d['value'] is not None]
            if values and len(set(values)) > 1:
                anomalies.append({
                    'row_number': row_number,
                    'anomaly_type': 'split_mismatch',
                    'severity': 'error',
                    'description': f"split_type is 'equal' but split_details show unequal amounts: {split_details_raw}",
                    'action_taken': 'flagged',
                    'original_value': f"type={split_type}, details={split_details_raw}",
                    'fixed_value': '',
                })
            elif values and len(split_with) > len(values):
                anomalies.append({
                    'row_number': row_number,
                    'anomaly_type': 'split_mismatch',
                    'severity': 'warning',
                    'description': f"split_type is 'equal' but split_details provided for only some people: {split_details_raw}",
                    'action_taken': 'flagged',
                    'original_value': f"type={split_type}, details={split_details_raw}",
                    'fixed_value': '',
                })

        return anomalies

    def _check_split_persons(self, row, row_number):
        """Check if everyone in split_with is also in split_details (when details exist)."""
        anomalies = []
        split_details_raw = row.get('split_details', '').strip()
        split_with_raw = row.get('split_with', '').strip()
        split_type = row.get('split_type', '').strip().lower()

        if not split_details_raw or not split_with_raw:
            return anomalies

        if split_type == 'equal':
            return anomalies  # Equal splits don't need details per person

        details = parse_split_details(split_details_raw)
        split_with = parse_split_with(split_with_raw)
        details_names = set(details.keys())

        for person in split_with:
            if person not in details_names and person:
                anomalies.append({
                    'row_number': row_number,
                    'anomaly_type': 'missing_split_person',
                    'severity': 'warning',
                    'description': f"'{person}' is in split_with but not in split_details.",
                    'action_taken': 'flagged',
                    'original_value': f"split_with={split_with_raw}, details={split_details_raw}",
                    'fixed_value': '',
                })

        return anomalies

    def _check_guests(self, row, row_number):
        """Detect guest/temporary people in splits."""
        anomalies = []
        split_with = parse_split_with(row.get('split_with', ''))
        paid_by = normalize_name(row.get('paid_by', ''))

        all_people = set(split_with)
        if paid_by:
            all_people.add(paid_by)

        for person in all_people:
            if person and person not in PERMANENT_MEMBERS:
                # Check if it's a compound name like "Dev's friend Kabir"
                is_friend_ref = "'s friend" in person.lower() or "friend" in person.lower()
                anomalies.append({
                    'row_number': row_number,
                    'anomaly_type': 'guest_person',
                    'severity': 'info',
                    'description': f"Non-roommate '{person}' found in expense. {'Tagged as friend reference.' if is_friend_ref else 'Auto-creating as guest.'}",
                    'action_taken': 'normalized',
                    'original_value': person,
                    'fixed_value': f"{person} (guest)",
                })

        return anomalies

    def _check_notes_for_ambiguity(self, row, row_number):
        """Check notes for ambiguous date references or other issues."""
        anomalies = []
        notes = row.get('notes', '').strip().lower()

        # Check for date ambiguity
        ambiguity_patterns = [
            r'is this .+or .+\?',
            r'april \d+ or may',
            r'which date',
            r'not sure.+date',
        ]

        for pattern in ambiguity_patterns:
            if re.search(pattern, notes):
                anomalies.append({
                    'row_number': row_number,
                    'anomaly_type': 'ambiguous_date',
                    'severity': 'warning',
                    'description': f"Notes suggest date ambiguity: '{row.get('notes', '')}'",
                    'action_taken': 'flagged',
                    'original_value': row.get('notes', ''),
                    'fixed_value': '',
                })
                break

        # Check for "also logged" / "counted twice" — possible duplicate logs
        dup_patterns = ['also logged', 'counted twice', 'duplicate', 'logged this']
        for pattern in dup_patterns:
            if pattern in notes:
                anomalies.append({
                    'row_number': row_number,
                    'anomaly_type': 'possible_duplicate_log',
                    'severity': 'warning',
                    'description': f"Notes suggest this may be a duplicate entry: '{row.get('notes', '')}'",
                    'action_taken': 'flagged',
                    'original_value': row.get('notes', ''),
                    'fixed_value': '',
                })
                break

        return anomalies

    def _check_duplicates(self, row, row_number, parsed_date, parsed_amount):
        """
        Detect duplicate expenses using fuzzy matching on description.
        Compares against previously seen expenses.
        """
        anomalies = []
        description = row.get('description', '').strip().lower()

        for seen in self.seen_expenses:
            # Same date and same amount — potential duplicate
            if seen['date'] == parsed_date and seen['amount'] == parsed_amount:
                similarity = fuzz.token_sort_ratio(description, seen['description'])
                if similarity >= 70:
                    anomalies.append({
                        'row_number': row_number,
                        'anomaly_type': 'duplicate',
                        'severity': 'warning',
                        'description': (
                            f"Possible duplicate of row {seen['row_number']}: "
                            f"'{row.get('description', '')}' ≈ '{seen['description']}' "
                            f"(similarity: {similarity}%, same date & amount)"
                        ),
                        'action_taken': 'flagged',
                        'original_value': row.get('description', ''),
                        'fixed_value': f"Similar to row {seen['row_number']}",
                    })

        return anomalies

    def _check_percentage_completeness(self, row, row_number):
        """Check if percentage splits add up to 100%."""
        anomalies = []
        split_type = row.get('split_type', '').strip().lower()

        if split_type != 'percentage':
            return anomalies

        split_details_raw = row.get('split_details', '').strip()
        if not split_details_raw:
            return anomalies

        details = parse_split_details(split_details_raw)
        percentages = [d['value'] for d in details.values() if d.get('is_percentage') and d['value'] is not None]
        missing_pct = [name for name, d in details.items() if d['value'] is None]

        total = sum(percentages)

        if missing_pct:
            anomalies.append({
                'row_number': row_number,
                'anomaly_type': 'percentage_incomplete',
                'severity': 'warning',
                'description': f"Percentage split incomplete. {', '.join(missing_pct)} have no percentage specified. Total specified: {total}%.",
                'action_taken': 'flagged',
                'original_value': split_details_raw,
                'fixed_value': '',
            })
        elif percentages and total != 100:
            anomalies.append({
                'row_number': row_number,
                'anomaly_type': 'percentage_incomplete',
                'severity': 'warning',
                'description': f"Percentages add up to {total}%, not 100%.",
                'action_taken': 'flagged',
                'original_value': split_details_raw,
                'fixed_value': '',
            })

        return anomalies

    def _check_departed_person(self, row, row_number, parsed_date):
        """Check if a departed person (like Meera) is still included in splits after they left."""
        anomalies = []
        notes = row.get('notes', '').strip().lower()

        # Check for notes about people leaving
        if any(kw in notes for kw in ['still in the list', 'oops']):
            anomalies.append({
                'row_number': row_number,
                'anomaly_type': 'departed_person',
                'severity': 'warning',
                'description': f"Notes suggest a departed person may still be in the split: '{row.get('notes', '')}'",
                'action_taken': 'flagged',
                'original_value': row.get('notes', ''),
                'fixed_value': '',
            })

        return anomalies

    def detect_mixed_currencies(self, expenses_data):
        """
        Post-processing check: detect mixed currencies within a trip/group.
        Called after all rows are processed.
        """
        anomalies = []

        # Group by date range (e.g., Goa trip 08-03 to 12-03)
        # Simple heuristic: look for consecutive multi-currency days
        currencies_by_date = {}
        for exp in expenses_data:
            date_key = exp.get('_parsed_date')
            if date_key:
                if date_key not in currencies_by_date:
                    currencies_by_date[date_key] = set()
                currencies_by_date[date_key].add(exp.get('currency', 'INR').strip() or 'INR')

        for dt, currencies in currencies_by_date.items():
            if len(currencies) > 1:
                anomalies.append({
                    'row_number': 0,
                    'anomaly_type': 'mixed_currency',
                    'severity': 'info',
                    'description': f"Mixed currencies on {dt}: {', '.join(sorted(currencies))}. Will convert using configured exchange rate.",
                    'action_taken': 'imported_as_is',
                    'original_value': ', '.join(sorted(currencies)),
                    'fixed_value': '',
                })

        return anomalies
