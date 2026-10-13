from django.contrib import admin

from flows.models import FlowEnrollment


@admin.register(FlowEnrollment)
class FlowEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "flow", "step", "status", "next_run_at", "cancel_reason")
    list_filter = ("flow", "status", "step")
