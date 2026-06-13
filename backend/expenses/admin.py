"""Django admin configuration for Expense Splitter."""

from django.contrib import admin
from .models import Person, ImportSession, Expense, SplitDetail, Anomaly, AppConfiguration


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_permanent', 'joined_date', 'left_date', 'created_at']
    list_filter = ['is_permanent']
    search_fields = ['name']


class SplitDetailInline(admin.TabularInline):
    model = SplitDetail
    extra = 0
    readonly_fields = ['person', 'amount', 'percentage', 'share_units']


class AnomalyInline(admin.TabularInline):
    model = Anomaly
    extra = 0
    readonly_fields = ['anomaly_type', 'severity', 'description', 'action_taken']
    fk_name = 'expense'


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['original_row', 'date', 'description', 'paid_by', 'amount', 'currency', 'split_type', 'is_settlement', 'is_flagged']
    list_filter = ['currency', 'split_type', 'is_settlement', 'is_flagged', 'import_session']
    search_fields = ['description', 'notes']
    inlines = [SplitDetailInline, AnomalyInline]


@admin.register(ImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'filename', 'uploaded_at', 'status', 'total_rows', 'imported_rows', 'skipped_rows', 'flagged_rows']
    list_filter = ['status']


@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display = ['row_number', 'anomaly_type', 'severity', 'action_taken', 'description']
    list_filter = ['anomaly_type', 'severity', 'action_taken', 'import_session']
    search_fields = ['description']


@admin.register(AppConfiguration)
class AppConfigurationAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description']
