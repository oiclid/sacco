from django.urls import path
from . import views

app_name = "savings"

urlpatterns = [
    # Fixed savings
    path("fixed/", views.FixedSavingsListCreateView.as_view(), name="fixed-list"),
    path("fixed/<int:pk>/", views.FixedSavingsDetailView.as_view(), name="fixed-detail"),

    # Target savings
    path("target/", views.TargetSavingsListCreateView.as_view(), name="target-list"),
    path("target/<int:pk>/", views.TargetSavingsDetailView.as_view(), name="target-detail"),

    # Fixed deposit
    path("fixed-deposit/", views.FixedDepositListCreateView.as_view(), name="fd-list"),
    path("fixed-deposit/<int:pk>/", views.FixedDepositDetailView.as_view(), name="fd-detail"),

    # Investments
    path("investment/", views.InvestmentListCreateView.as_view(), name="inv-list"),
    path("investment/<int:pk>/", views.InvestmentDetailView.as_view(), name="inv-detail"),

    # Transactions
    path("transactions/", views.SavingsTransactionListCreateView.as_view(), name="transactions-list"),
    path("transactions/<int:pk>/", views.SavingsTransactionDetailView.as_view(), name="transactions-detail"),

    # Utilities
    path("post-interest/", views.PostMonthlyInterestView.as_view(), name="post-interest"),
    path("members/<int:member_id>/summary/", views.MemberSavingsSummaryView.as_view(), name="member-summary"),
]
