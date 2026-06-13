"""
CSV Parser — Reads uploaded CSV and orchestrates import into the database.

Flow:
1. Read CSV rows
2. Run anomaly detection on each row
3. Create Person records as needed
4. Create Expense + SplitDetail records
5. Create Anomaly records
6. Update ImportSession with counts
"""

import csv
import io
from decimal import Decimal
from django.db import transaction

from .models import Person, ImportSession, Expense, SplitDetail, Anomaly
from .anomaly_detector import (
    AnomalyDetector, normalize_name, parse_split_with,
    parse_split_details, parse_date_flexible, parse_amount,
    PERMANENT_MEMBERS,
)


def ensure_person(name, is_permanent=None):
    """Get or create a Person record. Auto-detect if permanent member."""
    name = normalize_name(name)
    if not name:
        return None

    # Handle compound guest names like "Dev's friend Kabir"
    # Extract the actual name
    if "'s friend" in name.lower():
        # "Dev'S Friend Kabir" -> just use "Kabir"
        parts = name.split()
        # Take the last word as the guest name
        actual_name = parts[-1] if parts else name
        name = normalize_name(actual_name)

    if is_permanent is None:
        is_permanent = name in PERMANENT_MEMBERS

    person, created = Person.objects.get_or_create(
        name=name,
        defaults={'is_permanent': is_permanent}
    )
    return person


def resolve_payer_name(raw_name):
    """Resolve the payer name, handling suffixes like 'Priya S'."""
    name = normalize_name(raw_name)
    if not name:
        return name

    # Check for known name with suffix
    for known in PERMANENT_MEMBERS:
        if name.startswith(known) and len(name) > len(known):
            suffix = name[len(known):].strip()
            if len(suffix) <= 2:
                return known

    return name


def calculate_splits(expense_amount, split_type, split_with_names, split_details_raw, currency):
    """
    Calculate how much each person owes based on split type.
    Returns list of dicts: [{'name': str, 'amount': Decimal, 'percentage': Decimal|None, 'share_units': Decimal|None}]
    """
    if not split_with_names:
        return []

    num_people = len(split_with_names)
    result = []

    if split_type == 'equal' or not split_type:
        # Equal split among all people
        per_person = (expense_amount / num_people).quantize(Decimal('0.01'))
        remainder = expense_amount - (per_person * num_people)

        for i, name in enumerate(split_with_names):
            amount = per_person
            if i == 0:
                amount += remainder  # Give remainder to first person
            result.append({
                'name': name,
                'amount': amount,
                'percentage': None,
                'share_units': None,
            })

    elif split_type == 'unequal':
        details = parse_split_details(split_details_raw)
        allocated = Decimal('0')

        for name in split_with_names:
            if name in details and details[name]['value'] is not None:
                amount = details[name]['value']
                result.append({
                    'name': name,
                    'amount': amount,
                    'percentage': None,
                    'share_units': None,
                })
                allocated += amount
            else:
                # Person not in details — will get remainder split equally
                result.append({
                    'name': name,
                    'amount': None,  # Placeholder
                    'percentage': None,
                    'share_units': None,
                })

        # Distribute unallocated amount equally among people without specific amounts
        unallocated = expense_amount - allocated
        unspecified = [r for r in result if r['amount'] is None]
        if unspecified:
            per_person = (unallocated / len(unspecified)).quantize(Decimal('0.01'))
            for r in unspecified:
                r['amount'] = per_person
        elif allocated != expense_amount:
            # All specified but doesn't match total — import as-is
            pass

    elif split_type == 'percentage':
        details = parse_split_details(split_details_raw)
        total_pct = Decimal('0')
        unspecified_names = []

        for name in split_with_names:
            if name in details and details[name].get('is_percentage') and details[name]['value'] is not None:
                pct = details[name]['value']
                total_pct += pct
                amount = (expense_amount * pct / Decimal('100')).quantize(Decimal('0.01'))
                result.append({
                    'name': name,
                    'amount': amount,
                    'percentage': pct,
                    'share_units': None,
                })
            else:
                unspecified_names.append(name)

        # Distribute remaining percentage equally
        if unspecified_names:
            remaining_pct = Decimal('100') - total_pct
            per_person_pct = (remaining_pct / len(unspecified_names)).quantize(Decimal('0.01'))
            for name in unspecified_names:
                amount = (expense_amount * per_person_pct / Decimal('100')).quantize(Decimal('0.01'))
                result.append({
                    'name': name,
                    'amount': amount,
                    'percentage': per_person_pct,
                    'share_units': None,
                })

    elif split_type == 'share':
        details = parse_split_details(split_details_raw)
        total_shares = Decimal('0')

        shares = {}
        for name in split_with_names:
            if name in details and details[name]['value'] is not None:
                shares[name] = details[name]['value']
                total_shares += details[name]['value']
            else:
                shares[name] = Decimal('1')  # Default 1 share
                total_shares += Decimal('1')

        for name in split_with_names:
            share = shares.get(name, Decimal('1'))
            amount = (expense_amount * share / total_shares).quantize(Decimal('0.01'))
            result.append({
                'name': name,
                'amount': amount,
                'percentage': None,
                'share_units': share,
            })
    else:
        # Unknown split type — equal split as fallback
        per_person = (expense_amount / num_people).quantize(Decimal('0.01'))
        for name in split_with_names:
            result.append({
                'name': name,
                'amount': per_person,
                'percentage': None,
                'share_units': None,
            })

    return result


@transaction.atomic
def parse_csv(file_content, filename='upload.csv'):
    """
    Main CSV parsing entry point.
    Reads CSV content, detects anomalies, and imports records.

    Args:
        file_content: String or bytes content of the CSV file
        filename: Original filename

    Returns:
        ImportSession instance with all related records created
    """
    if isinstance(file_content, bytes):
        file_content = file_content.decode('utf-8-sig')  # Handle BOM

    session = ImportSession.objects.create(
        filename=filename,
        status='processing'
    )

    try:
        reader = csv.DictReader(io.StringIO(file_content))

        # Normalize header names
        if reader.fieldnames:
            reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

        detector = AnomalyDetector()
        all_cleaned_rows = []
        row_number = 1  # Header is row 1

        rows = list(reader)
        session.total_rows = len(rows)

        imported_count = 0
        skipped_count = 0
        flagged_count = 0
        auto_fixed_count = 0

        for row in rows:
            row_number += 1  # Data starts at row 2

            # Run anomaly detection
            cleaned, anomalies, should_skip = detector.detect_all(row, row_number)
            all_cleaned_rows.append(cleaned)

            # Track if this row had auto-fixes
            has_auto_fix = any(a['action_taken'] == 'auto_fixed' for a in anomalies)
            has_flag = any(a['action_taken'] == 'flagged' for a in anomalies)

            if should_skip:
                skipped_count += 1
                # Still save anomalies for the report
                for anom_data in anomalies:
                    Anomaly.objects.create(
                        import_session=session,
                        expense=None,
                        **anom_data
                    )
                continue

            # Create the expense record
            parsed_date = cleaned.get('_parsed_date')
            parsed_amount = cleaned.get('_parsed_amount')
            is_settlement = cleaned.get('_is_settlement', False)

            if parsed_date is None or parsed_amount is None:
                skipped_count += 1
                continue

            # Resolve payer
            raw_paid_by = row.get('paid_by', '').strip()
            payer_name = resolve_payer_name(raw_paid_by)
            payer = ensure_person(payer_name) if payer_name else None

            # Determine currency
            currency = row.get('currency', '').strip().upper()
            if not currency:
                currency = 'INR'

            # Determine split type
            split_type = row.get('split_type', '').strip().lower()
            if split_type and split_type not in ('equal', 'unequal', 'percentage', 'share'):
                split_type = 'equal'

            expense = Expense.objects.create(
                import_session=session,
                date=parsed_date,
                description=row.get('description', '').strip(),
                paid_by=payer,
                amount=parsed_amount,
                currency=currency,
                split_type=split_type if split_type else None,
                split_with_raw=row.get('split_with', '').strip(),
                split_details_raw=row.get('split_details', '').strip(),
                notes=row.get('notes', '').strip(),
                is_settlement=is_settlement,
                is_flagged=has_flag,
                original_row=row_number,
                raw_data=dict(row),
            )

            # Parse split_with and create Person + SplitDetail records
            split_with_names = parse_split_with(row.get('split_with', ''))

            # Ensure all people exist
            for name in split_with_names:
                ensure_person(name)

            # Calculate splits
            if not is_settlement and split_with_names and parsed_amount != 0:
                splits = calculate_splits(
                    abs(parsed_amount),
                    split_type,
                    split_with_names,
                    row.get('split_details', ''),
                    currency
                )

                for split in splits:
                    person = ensure_person(split['name'])
                    if person:
                        SplitDetail.objects.create(
                            expense=expense,
                            person=person,
                            amount=split['amount'] if split['amount'] is not None else Decimal('0'),
                            percentage=split.get('percentage'),
                            share_units=split.get('share_units'),
                        )
            elif is_settlement and split_with_names:
                # For settlements, create a simple detail
                for name in split_with_names:
                    person = ensure_person(name)
                    if person:
                        SplitDetail.objects.create(
                            expense=expense,
                            person=person,
                            amount=parsed_amount,
                        )

            # Save anomalies
            for anom_data in anomalies:
                Anomaly.objects.create(
                    import_session=session,
                    expense=expense,
                    **anom_data
                )

            imported_count += 1
            if has_flag:
                flagged_count += 1
            if has_auto_fix:
                auto_fixed_count += 1

        # Post-processing: mixed currency detection
        mixed_anomalies = detector.detect_mixed_currencies(all_cleaned_rows)
        for anom_data in mixed_anomalies:
            Anomaly.objects.create(
                import_session=session,
                expense=None,
                **anom_data
            )

        # Update session
        session.imported_rows = imported_count
        session.skipped_rows = skipped_count
        session.flagged_rows = flagged_count
        session.auto_fixed_rows = auto_fixed_count
        session.status = 'completed'
        session.save()

    except Exception as e:
        session.status = 'failed'
        session.error_message = str(e)
        session.save()
        raise

    return session
