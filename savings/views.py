from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from decimal import Decimal
import datetime

from .models import (
    FixedSavingsAccount, TargetSavingsAccount, FixedDepositAccount,
    InvestmentAccount, SavingsTransaction
)
from .serializers import (
    FixedSavingsAccountSerializer, TargetSavingsAccountSerializer,
    FixedDepositAccountSerializer, InvestmentAccountSerializer,
    SavingsTransactionSerializer
)


# --- Account endpoints per account type ---
class FixedSavingsListCreateView(generics.ListCreateAPIView):
    queryset = FixedSavingsAccount.objects.select_related("member").all()
    serializer_class = FixedSavingsAccountSerializer


class FixedSavingsDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FixedSavingsAccount.objects.all()
    serializer_class = FixedSavingsAccountSerializer


class TargetSavingsListCreateView(generics.ListCreateAPIView):
    queryset = TargetSavingsAccount.objects.select_related("member").all()
    serializer_class = TargetSavingsAccountSerializer


class TargetSavingsDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TargetSavingsAccount.objects.all()
    serializer_class = TargetSavingsAccountSerializer


class FixedDepositListCreateView(generics.ListCreateAPIView):
    queryset = FixedDepositAccount.objects.select_related("member").all()
    serializer_class = FixedDepositAccountSerializer


class FixedDepositDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FixedDepositAccount.objects.all()
    serializer_class = FixedDepositAccountSerializer


class InvestmentListCreateView(generics.ListCreateAPIView):
    queryset = InvestmentAccount.objects.select_related("member").all()
    serializer_class = InvestmentAccountSerializer


class InvestmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = InvestmentAccount.objects.all()
    serializer_class = InvestmentAccountSerializer


# --- Transactions ---
class SavingsTransactionListCreateView(generics.ListCreateAPIView):
    queryset = SavingsTransaction.objects.select_related("content_type").all()
    serializer_class = SavingsTransactionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        account_type = self.request.query_params.get("account_type")
        account_id = self.request.query_params.get("account_id")
        if account_type:
            ct = ContentType.objects.filter(model=account_type.lower()).first()
            if ct:
                qs = qs.filter(content_type=ct)
        if account_id:
            qs = qs.filter(object_id=account_id)
        return qs


class SavingsTransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SavingsTransaction.objects.all()
    serializer_class = SavingsTransactionSerializer


# --- Utilities / Posting interest ---
class PostMonthlyInterestView(APIView):
    """
    POST to trigger posting monthly interest across all active accounts.
    Payload optional:
      - account_types: ["fixed", "target", ...] (models' lower names)
      - date: YYYY-MM-DD (for reporting/transactions)
    """
    def post(self, request):
        data = request.data or {}
        types = data.get("account_types", None)
        created = []
        total = Decimal("0.00")

        # choose relevant querysets
        qs_map = {
            "fixedsavingsaccount": FixedSavingsAccount.objects.filter(status="active"),
            "targetsavingsaccount": TargetSavingsAccount.objects.filter(status="active"),
            "fixeddepositaccount": FixedDepositAccount.objects.filter(status="active"),
            "investmentaccount": InvestmentAccount.objects.filter(status="active"),
        }

        to_run = []
        if types:
            for t in types:
                key = t.lower()
                if key in qs_map:
                    to_run.append(qs_map[key])
        else:
            to_run = list(qs_map.values())

        for qs in to_run:
            for acct in qs:
                amt = acct.post_monthly_interest(create_transaction=True)
                if amt and amt != Decimal("0.00"):
                    total += amt
                    created.append({
                        "account": f"{acct.__class__.__name__}#{acct.pk}",
                        "member": acct.member.registration_number,
                        "amount": str(amt),
                    })

        return Response({"status": "ok", "total_interest_posted": str(total), "details": created}, status=status.HTTP_200_OK)


# Simple account summary / member totals
class MemberSavingsSummaryView(APIView):
    """
    GET /savings/members/{member_id}/summary/
    Returns balances by account type and totals.
    """
    def get(self, request, member_id):
        member = get_object_or_404(settings.AUTH_USER_MODEL if False else None, pk=member_id)  # stub if you want to wire to accounts.Member
        # If you have accounts.Member model in accounts app, change above line to:
        # from accounts.models import Member
        # member = get_object_or_404(Member, pk=member_id)

        # For now attempt to import Member dynamically to avoid import errors:
        try:
            from accounts.models import Member as MemberModel
            member = get_object_or_404(MemberModel, pk=member_id)
        except Exception:
            return Response({"detail": "Member model not available; wire accounts.Member properly."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        fixed = FixedSavingsAccount.objects.filter(member=member).aggregate(total=Sum("balance"))["total"] or Decimal("0.00")
        target = TargetSavingsAccount.objects.filter(member=member).aggregate(total=Sum("balance"))["total"] or Decimal("0.00")
        fd = FixedDepositAccount.objects.filter(member=member).aggregate(total=Sum("balance"))["total"] or Decimal("0.00")
        inv = InvestmentAccount.objects.filter(member=member).aggregate(total=Sum("balance"))["total"] or Decimal("0.00")

        return Response({
            "member": {"id": member.id, "registration_number": getattr(member, "registration_number", None)},
            "balances": {
                "fixed": str(fixed),
                "target": str(target),
                "fixed_deposit": str(fd),
                "investment": str(inv),
            },
            "total_savings": str((fixed + target + fd + inv))
        })
