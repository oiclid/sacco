from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import (
    FixedSavingsAccount, TargetSavingsAccount, FixedDepositAccount,
    InvestmentAccount, SavingsTransaction
)


class SavingsTransactionSerializer(serializers.ModelSerializer):
    account_type = serializers.SerializerMethodField()
    account_id = serializers.IntegerField(source="object_id", read_only=True)

    class Meta:
        model = SavingsTransaction
        fields = ["id", "account_type", "account_id", "transaction_type", "amount", "date", "description", "created_at"]

    def get_account_type(self, obj):
        return obj.content_type.model


class FixedSavingsAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixedSavingsAccount
        fields = ["id", "member", "balance", "interest_rate", "status", "created_at"]


class TargetSavingsAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetSavingsAccount
        fields = ["id", "member", "balance", "interest_rate", "target_amount", "target_date", "status", "created_at"]


class FixedDepositAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixedDepositAccount
        fields = ["id", "member", "balance", "interest_rate", "start_date", "maturity_date", "penalty_percent", "status", "created_at"]


class InvestmentAccountSerializer(serializers.ModelSerializer):
    market_value = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentAccount
        fields = ["id", "member", "balance", "units", "unit_price", "market_value", "status", "created_at"]

    def get_market_value(self, obj):
        return obj.market_value()
