"""
Database models for the Expense Splitter application.

Models:
- Person: Tracks roommates and guests
- ImportSession: Tracks each CSV upload/import
- Expense: Individual expense records
- SplitDetail: How each expense is split among people
- Anomaly: Data quality issues found during import
- AppConfig: Application-level configuration (exchange rates)
"""

from django.db import models
from django.core.validators import MinLengthValidator


class Person(models.Model):
    """Represents a person involved in expense splitting."""

    name = models.CharField(max_length=100, unique=True, validators=[MinLengthValidator(1)])
    is_permanent = models.BooleanField(
        default=False,
        help_text="True for permanent roommates, False for guests/temporary people"
    )
    joined_date = models.DateField(null=True, blank=True)
    left_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        role = "Roommate" if self.is_permanent else "Guest"
        return f"{self.name} ({role})"


class ImportSession(models.Model):
    """Tracks each CSV import session."""

    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    total_rows = models.IntegerField(default=0)
    imported_rows = models.IntegerField(default=0)
    skipped_rows = models.IntegerField(default=0)
    flagged_rows = models.IntegerField(default=0)
    auto_fixed_rows = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    error_message = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Import #{self.pk} - {self.filename} ({self.status})"

    @property
    def anomaly_count(self):
        return self.anomalies.count()


class Expense(models.Model):
    """Individual expense record imported from CSV."""

    SPLIT_TYPE_CHOICES = [
        ('equal', 'Equal'),
        ('unequal', 'Unequal'),
        ('percentage', 'Percentage'),
        ('share', 'Share'),
    ]

    CURRENCY_CHOICES = [
        ('INR', 'Indian Rupee'),
        ('USD', 'US Dollar'),
    ]

    import_session = models.ForeignKey(
        ImportSession, on_delete=models.CASCADE, related_name='expenses'
    )
    date = models.DateField()
    description = models.TextField()
    paid_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses_paid'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='INR')
    split_type = models.CharField(
        max_length=20, choices=SPLIT_TYPE_CHOICES, null=True, blank=True
    )
    split_with_raw = models.TextField(blank=True, default='', help_text="Raw split_with from CSV")
    split_details_raw = models.TextField(blank=True, default='', help_text="Raw split_details from CSV")
    notes = models.TextField(blank=True, default='')
    is_settlement = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    original_row = models.IntegerField(help_text="Row number in original CSV (1-indexed, header=1)")
    raw_data = models.JSONField(default=dict, help_text="Original CSV row data")
    category = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        ordering = ['date', 'original_row']

    def __str__(self):
        return f"Row {self.original_row}: {self.description} - {self.currency} {self.amount}"


class SplitDetail(models.Model):
    """How an expense is split among participants."""

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='split_details')
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Calculated amount this person owes for this expense"
    )
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Percentage share if split_type is percentage"
    )
    share_units = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Share units if split_type is share"
    )

    class Meta:
        unique_together = ['expense', 'person']
        ordering = ['person__name']

    def __str__(self):
        return f"{self.person.name}: {self.amount} for {self.expense.description}"


class Anomaly(models.Model):
    """Data quality issue found during CSV import."""

    ANOMALY_TYPES = [
        ('duplicate', 'Duplicate Entry'),
        ('malformed_date', 'Malformed Date'),
        ('missing_currency', 'Missing Currency'),
        ('zero_amount', 'Zero Amount'),
        ('negative_amount', 'Negative Amount'),
        ('mixed_currency', 'Mixed Currency in Group'),
        ('settlement_row', 'Settlement Row'),
        ('split_mismatch', 'Split Type Mismatch'),
        ('missing_split_person', 'Missing Person in Split Details'),
        ('ambiguous_date', 'Ambiguous Date'),
        ('guest_person', 'Guest/Temporary Person'),
        ('case_inconsistency', 'Case Inconsistency'),
        ('missing_payer', 'Missing Payer'),
        ('possible_duplicate_log', 'Possible Duplicate Log'),
        ('percentage_incomplete', 'Incomplete Percentages'),
        ('departed_person', 'Departed Person in Split'),
        ('other', 'Other'),
    ]

    SEVERITY_CHOICES = [
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Info'),
    ]

    ACTION_CHOICES = [
        ('skipped', 'Skipped'),
        ('flagged', 'Flagged'),
        ('auto_fixed', 'Auto-Fixed'),
        ('normalized', 'Normalized'),
        ('imported_as_is', 'Imported As-Is'),
    ]

    import_session = models.ForeignKey(
        ImportSession, on_delete=models.CASCADE, related_name='anomalies'
    )
    expense = models.ForeignKey(
        Expense, on_delete=models.SET_NULL, null=True, blank=True, related_name='anomalies'
    )
    row_number = models.IntegerField()
    anomaly_type = models.CharField(max_length=30, choices=ANOMALY_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    description = models.TextField()
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES)
    original_value = models.TextField(blank=True, default='')
    fixed_value = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['row_number', 'anomaly_type']
        verbose_name_plural = 'Anomalies'

    def __str__(self):
        return f"Row {self.row_number}: [{self.anomaly_type}] {self.description}"


class AppConfiguration(models.Model):
    """Singleton model for app-level configuration."""

    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=500)
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get_usd_to_inr_rate(cls):
        """Get the USD to INR exchange rate, falling back to Django settings."""
        from django.conf import settings
        try:
            config = cls.objects.get(key='USD_TO_INR_RATE')
            return float(config.value)
        except cls.DoesNotExist:
            return settings.USD_TO_INR_RATE

    @classmethod
    def set_usd_to_inr_rate(cls, rate):
        """Set the USD to INR exchange rate."""
        obj, _ = cls.objects.update_or_create(
            key='USD_TO_INR_RATE',
            defaults={'value': str(rate), 'description': 'USD to INR conversion rate'}
        )
        return obj
