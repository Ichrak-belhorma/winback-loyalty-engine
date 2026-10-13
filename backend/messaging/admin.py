from django.contrib import admin

from messaging.models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "flow", "step", "channel", "status", "block_reason")
    list_filter = ("flow", "status", "channel", "personalization", "block_reason")
