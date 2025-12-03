from django.contrib import admin
from django.urls import path
from savings.admin_dashboard import savings_dashboard

class CustomAdminSite(admin.AdminSite):
    site_header = "Savings Admin"
    site_title = "NFC MPCSL Admin"
    index_title = "Admin Home"

    def get_urls(self):
        return [
            path("savings-dashboard/", self.admin_view(savings_dashboard), name="savings-dashboard"),
        ] + super().get_urls()


admin_site = CustomAdminSite()
