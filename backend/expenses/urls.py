"""URL routing for the Expense Splitter API."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'persons', views.PersonViewSet)

urlpatterns = [
    # CSV Upload
    path('upload/', views.upload_csv, name='upload-csv'),

    # Import Sessions
    path('import-sessions/', views.ImportSessionListView.as_view(), name='import-session-list'),
    path('import-sessions/<int:pk>/', views.ImportSessionDetailView.as_view(), name='import-session-detail'),

    # Expenses
    path('expenses/', views.ExpenseListView.as_view(), name='expense-list'),
    path('expenses/<int:pk>/', views.ExpenseDetailView.as_view(), name='expense-detail'),

    # Balances & Settlements
    path('balances/', views.get_balances, name='balances'),
    path('settlements/', views.get_settlements, name='settlements'),

    # Anomalies
    path('anomalies/', views.AnomalyListView.as_view(), name='anomaly-list'),

    # Config
    path('config/', views.app_config, name='app-config'),

    # Router URLs (persons CRUD)
    path('', include(router.urls)),
]
