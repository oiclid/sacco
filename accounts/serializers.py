from rest_framework import serializers
from .models import Member
from decimal import Decimal

class MemberSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="full_name", read_only=True)
    total_savings = serializers.SerializerMethodField()
    loans_outstanding = serializers.SerializerMethodField()
    dividends = serializers.SerializerMethodField()
    net_position = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id",
            "registration_number",
            "first_name",
            "middle_name",
            "last_name",
            "full_name",
            "join_date",
            "status",
            "shutdown_date",
            "shutdown_reason",
            "final_balance",
            "total_savings",
            "loans_outstanding",
            "dividends",
            "net_position",
        ]

    def get_total_savings(self, obj):
        return obj.get_total_savings()

    def get_loans_outstanding(self, obj):
        return obj.get_loans_outstanding()

    def get_dividends(self, obj):
        return obj.get_dividends()

    def get_net_position(self, obj):
        """
        Savings – Loans
        """
        return obj.get_total_savings() - obj.get_loans_outstanding()
