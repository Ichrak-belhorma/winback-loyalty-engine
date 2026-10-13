from django.contrib import admin

from customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "first_name", "timezone", "unsubscribed", "signed_up_at")
    list_filter = ("unsubscribed",)
    search_fields = ("email", "phone", "first_name", "last_name", "referral_code")
