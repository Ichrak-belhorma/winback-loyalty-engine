from django.contrib import admin
from django.urls import path

from compliance.views import inbound_sms
from config.health import health
from customers.views import signup
from dashboard.views import recent_messages, stats_messages_over_time, stats_overview
from flows.views import process_due, refresh
from orders.views import order_created
from referrals.views import redeem_referral
from reviews.views import create_review, delivery_completed

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health, name="health"),
    path("api/webhooks/inbound-sms", inbound_sms, name="inbound-sms"),
    path("api/flows/process-due", process_due, name="process-due"),
    path("api/segments/refresh", refresh, name="segments-refresh"),
    path("api/customers", signup, name="signup"),
    path("api/webhooks/order-created", order_created, name="order-created"),
    path("api/referrals/redeem", redeem_referral, name="redeem-referral"),
    path("api/webhooks/delivery-completed", delivery_completed, name="delivery-completed"),
    path("api/reviews", create_review, name="create-review"),
    path("api/stats/overview", stats_overview, name="stats-overview"),
    path("api/stats/messages-over-time", stats_messages_over_time, name="stats-timeseries"),
    path("api/messages/recent", recent_messages, name="recent-messages"),
]
