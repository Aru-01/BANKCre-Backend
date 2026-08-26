from django.db import models
from django.conf import settings


class LoanRequest(models.Model):
    STATUS_ACTIVE = "Active"
    STATUS_UNDER_REVIEW = "Under Review"
    STATUS_CLOSED = "Closed"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_CLOSED, "Closed"),
    ]

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="loan_requests",
    )
    sponsor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loan_requests",
    )
    sponsor_role = models.ForeignKey(
        "accounts.RoleModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan_requests",
    )
    requested_amount = models.DecimalField(max_digits=15, decimal_places=2)
    loan_term = models.IntegerField(help_text="Loan term in months")
    ltv = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Loan-to-Value percentage"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.property.property_name} — ${self.requested_amount}"

    class Meta:
        verbose_name = "Loan Request"
        verbose_name_plural = "Loan Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sponsor", "status"]),
            models.Index(fields=["property", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]


class LoanQuote(models.Model):
    STATUS_SUBMITTED = "Submitted"
    STATUS_UNDER_REVIEW = "Under Review"
    STATUS_ACCEPTED = "Accepted"
    STATUS_DECLINED = "Declined"
    STATUS_EXPIRED = "Expired"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
        (STATUS_EXPIRED, "Expired"),
    ]

    # Basic Information
    loan_request = models.ForeignKey(
        LoanRequest,
        on_delete=models.CASCADE,
        related_name="quotes",
    )
    lender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loan_quotes",
    )
    lender_role = models.ForeignKey(
        "accounts.RoleModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan_quotes",
    )
    lender_name = models.CharField(max_length=255)
    guarantor = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED
    )
    expires_at = models.DateTimeField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Loan Structure
    loan_amount = models.DecimalField(max_digits=15, decimal_places=2)
    initial_funding = models.DecimalField(max_digits=15, decimal_places=2)
    future_funding = models.DecimalField(max_digits=15, decimal_places=2)
    sponsor_equity = models.DecimalField(max_digits=15, decimal_places=2)

    # LTV & Debt Yield Metrics
    max_as_is_ltv = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Percentage"
    )
    max_ltc = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Percentage"
    )
    max_as_stabilized_ltv = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Percentage"
    )
    min_as_is_dy = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Percentage"
    )
    min_stabilized_dy = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Percentage"
    )

    # Terms & Rates
    term = models.IntegerField(help_text="Term in months")
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Percentage"
    )
    amortization = models.CharField(max_length=255)
    prepayment = models.CharField(max_length=255)

    # Fees & Reserves
    origination_fee = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Percentage"
    )
    capex_reserve = models.DecimalField(max_digits=15, decimal_places=2)
    ff_and_e_reserve = models.DecimalField(max_digits=15, decimal_places=2)
    interest_carry_reserve = models.DecimalField(max_digits=15, decimal_places=2)

    # Additional Terms
    extension_conditions = models.TextField()
    collateral = models.CharField(max_length=255)
    recourse = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.lender_name} quote for {self.loan_request}"

    class Meta:
        verbose_name = "Loan Quote"
        verbose_name_plural = "Loan Quotes"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["loan_request", "status"]),
            models.Index(fields=["lender", "status"]),
            models.Index(fields=["status", "-submitted_at"]),
        ]
