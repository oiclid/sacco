from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

TRANSACTION_TYPES = [
    ("deposit", "Deposit"),
    ("withdrawal", "Withdrawal"),
    ("interest", "Interest"),
]

class SavingsTransaction(models.Model):
    # Generic link to any savings account
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    account = GenericForeignKey("content_type", "object_id")

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    description = models.TextField(default="N/A")  # non-nullable with default
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def record(account, transaction_type, amount, description=None):
        """
        Record a transaction for a given account instance.
        """
        from django.contrib.contenttypes.models import ContentType

        if description is None:
            description = "N/A"

        ct = ContentType.objects.get_for_model(account)
        SavingsTransaction.objects.create(
            content_type=ct,
            object_id=account.id,
            account=account,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
        )
