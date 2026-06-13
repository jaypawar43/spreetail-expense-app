"""
LLM Client — OpenAI integration for enhanced anomaly detection.

Provides smart parsing capabilities:
1. Semantic duplicate detection (fuzzy matching beyond string similarity)
2. Expense categorization
3. Anomaly analysis and recommendations

Falls back gracefully when API key is missing or rate-limited.
"""

import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def get_openai_client():
    """Get an OpenAI client instance, or None if not configured."""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.info("OpenAI API key not configured. Using rule-based detection only.")
        return None

    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        logger.warning("openai package not installed. Using rule-based detection only.")
        return None
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        return None


def analyze_anomalies_with_llm(expenses_data):
    """
    Send expense data to LLM for deeper anomaly analysis.

    Args:
        expenses_data: List of dicts representing CSV rows

    Returns:
        List of additional anomaly dicts found by the LLM,
        or empty list if LLM is unavailable.
    """
    client = get_openai_client()
    if not client:
        return []

    try:
        # Prepare a concise summary of the data
        summary = []
        for i, exp in enumerate(expenses_data[:50]):  # Limit to 50 rows
            summary.append(
                f"Row {i+2}: date={exp.get('date','')}, desc={exp.get('description','')}, "
                f"paid_by={exp.get('paid_by','')}, amount={exp.get('amount','')}, "
                f"currency={exp.get('currency','')}, split_type={exp.get('split_type','')}, "
                f"notes={exp.get('notes','')}"
            )

        prompt = f"""Analyze these expense records for a shared apartment and identify data quality issues.
Look for:
1. Semantic duplicates (same expense logged differently by different people)
2. Suspicious patterns (unusually high amounts, wrong categorization)
3. Inconsistencies between description and amount
4. Any other data quality concerns

Expense data:
{chr(10).join(summary)}

Return a JSON array of issues found. Each issue should have:
- "row_number": int
- "issue_type": string (one of: "semantic_duplicate", "suspicious_amount", "inconsistency", "other")
- "description": string explaining the issue
- "confidence": float (0-1)

Return ONLY the JSON array, no other text."""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a data quality analyst. Analyze expense data and return JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        result_text = response.choices[0].message.content.strip()

        # Try to parse JSON from the response
        # Handle cases where LLM wraps in markdown code blocks
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        issues = json.loads(result_text)

        # Convert to our anomaly format
        anomalies = []
        for issue in issues:
            if issue.get('confidence', 0) >= 0.6:
                anomalies.append({
                    'row_number': issue.get('row_number', 0),
                    'anomaly_type': 'other',
                    'severity': 'info',
                    'description': f"[AI] {issue.get('description', 'Unknown issue')}",
                    'action_taken': 'flagged',
                    'original_value': '',
                    'fixed_value': f"Confidence: {issue.get('confidence', 0):.0%}",
                })

        logger.info(f"LLM analysis found {len(anomalies)} additional issues.")
        return anomalies

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        return []


def categorize_expenses_with_llm(expenses_data):
    """
    Use LLM to categorize expenses into meaningful categories.

    Returns dict mapping row_number -> category string.
    """
    client = get_openai_client()
    if not client:
        return categorize_expenses_rule_based(expenses_data)

    try:
        descriptions = []
        for exp in expenses_data[:50]:
            descriptions.append(
                f"Row {exp.get('row_number', 0)}: {exp.get('description', '')}"
            )

        prompt = f"""Categorize these apartment expenses into one of these categories:
- Rent
- Utilities (electricity, wifi, gas)
- Groceries
- Food & Dining
- Transportation
- Entertainment
- Household (cleaning, furniture, supplies)
- Travel
- Settlement
- Other

Expenses:
{chr(10).join(descriptions)}

Return a JSON object mapping row numbers to categories. Example: {{"2": "Rent", "3": "Groceries"}}
Return ONLY the JSON object."""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expense categorizer. Return only JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        categories = json.loads(result_text)
        return {int(k): v for k, v in categories.items()}

    except Exception as e:
        logger.error(f"LLM categorization failed: {e}")
        return categorize_expenses_rule_based(expenses_data)


def categorize_expenses_rule_based(expenses_data):
    """
    Fallback rule-based expense categorization.
    """
    category_keywords = {
        'Rent': ['rent'],
        'Utilities': ['electricity', 'wifi', 'bill', 'cylinder', 'gas'],
        'Groceries': ['groceries', 'bigbasket', 'dmart', 'd-mart'],
        'Food & Dining': ['dinner', 'lunch', 'restaurant', 'pizza', 'snacks', 'brunch',
                          'swiggy', 'zomato', 'shack', 'thalassa', 'farewell'],
        'Transportation': ['cab', 'uber', 'ola', 'airport', 'flights', 'scooter'],
        'Entertainment': ['movie', 'parasailing', 'housewarming'],
        'Household': ['cleaning', 'maid', 'furniture', 'supplies', 'deep clean'],
        'Travel': ['goa', 'villa', 'booking', 'flights', 'beach'],
        'Settlement': ['paid', 'settlement', 'transfer', 'deposit', 'paid back'],
    }

    result = {}
    for exp in expenses_data:
        desc = exp.get('description', '').lower()
        row = exp.get('row_number', 0)
        category = 'Other'

        for cat, keywords in category_keywords.items():
            if any(kw in desc for kw in keywords):
                category = cat
                break

        result[row] = category

    return result
