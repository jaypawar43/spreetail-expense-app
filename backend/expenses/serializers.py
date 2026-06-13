"""
DRF Serializers for the Expense Splitter API.
"""

from rest_framework import serializers
from .models import Person, ImportSession, Expense, SplitDetail, Anomaly, AppConfiguration


class PersonSerializer(serializers.ModelSerializer):
    expense_count = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ['id', 'name', 'is_permanent', 'joined_date', 'left_date', 'created_at', 'expense_count']
        read_only_fields = ['created_at']

    def get_expense_count(self, obj):
        return obj.expenses_paid.count()


class SplitDetailSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.name', read_only=True)

    class Meta:
        model = SplitDetail
        fields = ['id', 'person', 'person_name', 'amount', 'percentage', 'share_units']


class AnomalySerializer(serializers.ModelSerializer):
    anomaly_type_display = serializers.CharField(source='get_anomaly_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    action_taken_display = serializers.CharField(source='get_action_taken_display', read_only=True)

    class Meta:
        model = Anomaly
        fields = [
            'id', 'row_number', 'anomaly_type', 'anomaly_type_display',
            'severity', 'severity_display', 'description',
            'action_taken', 'action_taken_display',
            'original_value', 'fixed_value',
        ]


class ExpenseListSerializer(serializers.ModelSerializer):
    paid_by_name = serializers.CharField(source='paid_by.name', read_only=True, default=None)
    anomaly_count = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            'id', 'date', 'description', 'paid_by', 'paid_by_name',
            'amount', 'currency', 'split_type',
            'split_with_raw', 'notes',
            'is_settlement', 'is_flagged', 'original_row',
            'category', 'anomaly_count',
        ]

    def get_anomaly_count(self, obj):
        return obj.anomalies.count()


class ExpenseDetailSerializer(serializers.ModelSerializer):
    paid_by_name = serializers.CharField(source='paid_by.name', read_only=True, default=None)
    splits = SplitDetailSerializer(many=True, read_only=True)
    anomalies = AnomalySerializer(many=True, read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'date', 'description', 'paid_by', 'paid_by_name',
            'amount', 'currency', 'split_type',
            'split_with_raw', 'split_details_raw', 'notes',
            'is_settlement', 'is_flagged', 'original_row',
            'raw_data', 'category',
            'splits', 'anomalies',
        ]


class ImportSessionListSerializer(serializers.ModelSerializer):
    anomaly_count = serializers.IntegerField(source='anomalies.count', read_only=True)

    class Meta:
        model = ImportSession
        fields = [
            'id', 'filename', 'uploaded_at', 'status',
            'total_rows', 'imported_rows', 'skipped_rows',
            'flagged_rows', 'auto_fixed_rows',
            'anomaly_count', 'error_message',
        ]


class ImportSessionDetailSerializer(serializers.ModelSerializer):
    anomalies = AnomalySerializer(many=True, read_only=True)
    anomaly_count = serializers.IntegerField(source='anomalies.count', read_only=True)

    class Meta:
        model = ImportSession
        fields = [
            'id', 'filename', 'uploaded_at', 'status',
            'total_rows', 'imported_rows', 'skipped_rows',
            'flagged_rows', 'auto_fixed_rows',
            'anomaly_count', 'error_message',
            'anomalies',
        ]


class AppConfigSerializer(serializers.Serializer):
    usd_to_inr_rate = serializers.FloatField()
