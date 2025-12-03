from django.urls import path
from . import views

app_name = "loans"

urlpatterns = [
    path("reports/", views.loan_report_view, name="loan_report"),
    path("api/loan/<int:pk>/", views.loan_detail_json, name="loan_detail_json"),
]
