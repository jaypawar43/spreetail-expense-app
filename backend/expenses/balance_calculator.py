"""
Balance Calculator — Computes who owes whom and generates simplified settlements.

Algorithm:
1. For each non-settlement expense, calculate what each person paid vs what they owe
2. Convert all amounts to INR using the configurable exchange rate
3. Net out the balances
4. Use the min-transactions algorithm to simplify settlements
"""

from decimal import Decimal
from collections import defaultdict
from .models import Expense, SplitDetail, Person, AppConfiguration


def get_exchange_rate():
    """Get the current USD to INR exchange rate."""
    return Decimal(str(AppConfiguration.get_usd_to_inr_rate()))


def convert_to_inr(amount, currency):
    """Convert an amount to INR."""
    if currency == 'INR':
        return amount
    elif currency == 'USD':
        rate = get_exchange_rate()
        return (amount * rate).quantize(Decimal('0.01'))
    return amount


def calculate_balances(session_id=None):
    """
    Calculate net balances for all people.

    Returns:
        {
            'balances': {person_name: net_balance_in_INR},  # positive = owed money, negative = owes money
            'detailed': [
                {
                    'expense_id': int,
                    'description': str,
                    'paid_by': str,
                    'amount': Decimal,
                    'currency': str,
                    'amount_inr': Decimal,
                    'splits': [{'person': str, 'owes': Decimal}]
                }
            ],
            'exchange_rate': float,
        }
    """
    filters = {'is_settlement': False}
    if session_id:
        filters['import_session_id'] = session_id

    expenses = Expense.objects.filter(**filters).select_related('paid_by').prefetch_related('splits__person')

    # Net balance per person: positive means they are owed money, negative means they owe
    balances = defaultdict(Decimal)
    detailed = []

    for expense in expenses:
        if not expense.paid_by:
            continue

        payer = expense.paid_by.name
        amount = expense.amount
        currency = expense.currency
        amount_inr = convert_to_inr(amount, currency)

        # The payer paid the full amount
        balances[payer] += amount_inr

        splits = expense.splits.all()
        split_details = []

        for split in splits:
            person_name = split.person.name
            share_inr = convert_to_inr(split.amount, currency)

            # Each person owes their share
            balances[person_name] -= share_inr

            split_details.append({
                'person': person_name,
                'owes': float(share_inr),
            })

        detailed.append({
            'expense_id': expense.id,
            'description': expense.description,
            'date': str(expense.date),
            'paid_by': payer,
            'amount': float(amount),
            'currency': currency,
            'amount_inr': float(amount_inr),
            'splits': split_details,
        })

    # Process settlements
    settlement_filters = {'is_settlement': True}
    if session_id:
        settlement_filters['import_session_id'] = session_id

    settlements = Expense.objects.filter(**settlement_filters).select_related('paid_by').prefetch_related('splits__person')

    for settlement in settlements:
        if not settlement.paid_by:
            continue

        payer = settlement.paid_by.name
        amount_inr = convert_to_inr(settlement.amount, settlement.currency)

        # Settlement: payer gave money to the people in split_with
        # So payer's balance goes down (they paid out)
        balances[payer] -= amount_inr

        for split in settlement.splits.all():
            # The recipient's balance goes up (they received money)
            balances[split.person.name] += amount_inr

    return {
        'balances': {k: float(v) for k, v in balances.items()},
        'detailed': detailed,
        'exchange_rate': float(get_exchange_rate()),
    }


def simplify_settlements(session_id=None):
    """
    Generate simplified settlement plan using the min-transactions algorithm.

    Returns list of:
    [
        {'from': person_name, 'to': person_name, 'amount': float, 'currency': 'INR'}
    ]
    """
    balance_data = calculate_balances(session_id)
    balances = balance_data['balances']

    # Separate into creditors (positive balance = owed money) and debtors (negative = owes money)
    creditors = []  # (name, amount_owed_to_them)
    debtors = []    # (name, amount_they_owe)

    for person, balance in balances.items():
        rounded = round(balance, 2)
        if rounded > 0.01:  # Person is owed money
            creditors.append([person, rounded])
        elif rounded < -0.01:  # Person owes money
            debtors.append([person, abs(rounded)])

    # Sort by amount (largest first) for efficient settlement
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    settlements = []

    # Greedy algorithm: match largest debtor with largest creditor
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_name, debt = debtors[i]
        creditor_name, credit = creditors[j]

        settle_amount = min(debt, credit)

        if settle_amount > 0.01:
            settlements.append({
                'from': debtor_name,
                'to': creditor_name,
                'amount': round(settle_amount, 2),
                'currency': 'INR',
            })

        debtors[i][1] -= settle_amount
        creditors[j][1] -= settle_amount

        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1

    return {
        'settlements': settlements,
        'balances': balance_data['balances'],
        'exchange_rate': balance_data['exchange_rate'],
    }
