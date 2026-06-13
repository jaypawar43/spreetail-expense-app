"""
API Views for the Expense Splitter application.
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from .models import Person, ImportSession, Expense, Anomaly, AppConfiguration
from .serializers import (
    PersonSerializer,
    ImportSessionListSerializer,
    ImportSessionDetailSerializer,
    ExpenseListSerializer,
    ExpenseDetailSerializer,
    AnomalySerializer,
    AppConfigSerializer,
)
from .csv_parser import parse_csv
from .balance_calculator import calculate_balances, simplify_settlements


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


# ─── CSV Upload ───────────────────────────────────────────

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_csv(request):
    """
    Upload a CSV file for parsing and import.
    Expects a file field named 'file'.
    """
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No file provided. Send a CSV file with key "file".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    csv_file = request.FILES['file']

    if not csv_file.name.endswith('.csv'):
        return Response(
            {'error': 'File must be a CSV file.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        file_content = csv_file.read()
        session = parse_csv(file_content, filename=csv_file.name)

        # Try AI-enhanced analysis (non-blocking — skips if no API key)
        try:
            from ai_service.llm_client import analyze_anomalies_with_llm, categorize_expenses_with_llm

            # Get expense data for AI analysis
            expenses = session.expenses.all()
            expenses_data = [
                {
                    'row_number': e.original_row,
                    'date': str(e.date),
                    'description': e.description,
                    'paid_by': e.paid_by.name if e.paid_by else '',
                    'amount': str(e.amount),
                    'currency': e.currency,
                    'split_type': e.split_type or '',
                    'notes': e.notes,
                }
                for e in expenses
            ]

            # AI anomaly detection
            ai_anomalies = analyze_anomalies_with_llm(expenses_data)
            for anom in ai_anomalies:
                Anomaly.objects.create(
                    import_session=session,
                    **anom
                )

            # AI categorization
            categories = categorize_expenses_with_llm(expenses_data)
            for expense in expenses:
                cat = categories.get(expense.original_row, '')
                if cat:
                    expense.category = cat
                    expense.save(update_fields=['category'])

        except Exception as e:
            # AI analysis is optional — log and continue
            import logging
            logging.getLogger(__name__).warning(f"AI analysis skipped: {e}")

        serializer = ImportSessionDetailSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': f'Failed to process CSV: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ─── Import Sessions ─────────────────────────────────────

class ImportSessionListView(generics.ListAPIView):
    """List all import sessions."""
    queryset = ImportSession.objects.all()
    serializer_class = ImportSessionListSerializer
    pagination_class = StandardPagination


class ImportSessionDetailView(generics.RetrieveAPIView):
    """Get details of a specific import session with all anomalies."""
    queryset = ImportSession.objects.all()
    serializer_class = ImportSessionDetailSerializer


# ─── Expenses ────────────────────────────────────────────

class ExpenseListView(generics.ListAPIView):
    """
    List expenses with optional filters:
    - ?person=<name> — filter by payer name
    - ?date_from=YYYY-MM-DD — filter by start date
    - ?date_to=YYYY-MM-DD — filter by end date
    - ?currency=INR|USD — filter by currency
    - ?category=<category> — filter by category
    - ?search=<text> — search in description and notes
    - ?session=<id> — filter by import session
    - ?settlement=true|false — filter settlements
    - ?flagged=true|false — filter flagged expenses
    """
    serializer_class = ExpenseListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Expense.objects.select_related('paid_by').all()
        params = self.request.query_params

        if person := params.get('person'):
            qs = qs.filter(paid_by__name__iexact=person)

        if date_from := params.get('date_from'):
            qs = qs.filter(date__gte=date_from)

        if date_to := params.get('date_to'):
            qs = qs.filter(date__lte=date_to)

        if currency := params.get('currency'):
            qs = qs.filter(currency=currency.upper())

        if category := params.get('category'):
            qs = qs.filter(category__iexact=category)

        if search := params.get('search'):
            qs = qs.filter(
                Q(description__icontains=search) | Q(notes__icontains=search)
            )

        if session := params.get('session'):
            qs = qs.filter(import_session_id=session)

        if settlement := params.get('settlement'):
            qs = qs.filter(is_settlement=settlement.lower() == 'true')

        if flagged := params.get('flagged'):
            qs = qs.filter(is_flagged=flagged.lower() == 'true')

        return qs


class ExpenseDetailView(generics.RetrieveAPIView):
    """Get detailed view of a single expense with splits and anomalies."""
    queryset = Expense.objects.select_related('paid_by').prefetch_related('splits__person', 'anomalies')
    serializer_class = ExpenseDetailSerializer


# ─── Balances & Settlements ──────────────────────────────

@api_view(['GET'])
def get_balances(request):
    """Get balance summary for all people."""
    session_id = request.query_params.get('session')
    data = calculate_balances(session_id=session_id)
    return Response(data)


@api_view(['GET'])
def get_settlements(request):
    """Get simplified settlement plan."""
    session_id = request.query_params.get('session')
    data = simplify_settlements(session_id=session_id)
    return Response(data)


# ─── Persons ─────────────────────────────────────────────

class PersonViewSet(viewsets.ModelViewSet):
    """CRUD for persons (roommates and guests)."""
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    pagination_class = StandardPagination


# ─── Anomalies ───────────────────────────────────────────

class AnomalyListView(generics.ListAPIView):
    """
    List anomalies with optional filters:
    - ?session=<id> — filter by import session
    - ?type=<anomaly_type> — filter by type
    - ?severity=<severity> — filter by severity
    - ?action=<action> — filter by action taken
    """
    serializer_class = AnomalySerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Anomaly.objects.all()
        params = self.request.query_params

        if session := params.get('session'):
            qs = qs.filter(import_session_id=session)

        if atype := params.get('type'):
            qs = qs.filter(anomaly_type=atype)

        if severity := params.get('severity'):
            qs = qs.filter(severity=severity)

        if action := params.get('action'):
            qs = qs.filter(action_taken=action)

        return qs


# ─── Config ──────────────────────────────────────────────

@api_view(['GET', 'PATCH'])
def app_config(request):
    """Get or update application configuration (exchange rate)."""
    if request.method == 'GET':
        rate = AppConfiguration.get_usd_to_inr_rate()
        return Response({'usd_to_inr_rate': rate})

    elif request.method == 'PATCH':
        serializer = AppConfigSerializer(data=request.data)
        if serializer.is_valid():
            rate = serializer.validated_data['usd_to_inr_rate']
            AppConfiguration.set_usd_to_inr_rate(rate)
            return Response({'usd_to_inr_rate': rate})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
