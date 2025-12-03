from django.contrib import admin
from django.utils.html import format_html
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "registration_number",
        "colored_name",
        "status",
        "join_date",
        "shutdown_date",
        "final_balance",
    )

    search_fields = ("registration_number", "first_name", "last_name")
    list_filter = ("status",)

    actions = ['shutdown_quit', 'shutdown_retirement', 'shutdown_deceased']

    def colored_name(self, obj):
        color = {
            'active': "green",
            'quit': "orange",
            'retired': "blue",
            'deceased': "red",
        }.get(obj.status, "black")

        return format_html(
            f"<b style='color:{color};'>{obj.full_name()}</b>"
        )

    colored_name.short_description = "Member Name"

    # -------------------------------------------------------
    # Admin Bulk Actions
    # -------------------------------------------------------
    def shutdown_quit(self, request, queryset):
        for m in queryset:
            m.shutdown('quit')
        self.message_user(request, "Selected members shut down as Quit.")

    def shutdown_retirement(self, request, queryset):
        for m in queryset:
            m.shutdown('retired')
        self.message_user(request, "Selected members shut down as Retired.")

    def shutdown_deceased(self, request, queryset):
        for m in queryset:
            m.shutdown('deceased')
        self.message_user(request, "Selected members recorded as Deceased.")
