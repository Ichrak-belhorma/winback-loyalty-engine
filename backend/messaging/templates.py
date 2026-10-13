"""Template copy per (flow, step). Placeholders: {first_name}, {store}, {discount}, {code},
{link}. {discount}/{code}/{link} are facts injected from config, never written by a model."""

TEMPLATES: dict[tuple[str, str], tuple[str, str]] = {
    ("welcome", "welcome"): (
        "Welcome to {store}, {first_name}!",
        "Hi {first_name}, welcome to {store}! Groceries and essentials at your door the same "
        "day. Your first order is just a few taps away.",
    ),
    ("welcome", "first_order_nudge"): (
        "Your first {store} order is waiting",
        "Hi {first_name}, still deciding? Most {store} orders arrive in under 2 hours. Here's "
        "{discount} off your first order to get you started.",
    ),
    ("winback", "reminder"): (
        "We miss you, {first_name}",
        "Hi {first_name}, it's been a while! Your favourites are still in stock at {store}, "
        "delivered today.",
    ),
    ("winback", "offer"): (
        "{discount} off your next {store} order",
        "Hi {first_name}, come back to {store} and take {discount} off your next order this week.",
    ),
    ("winback", "final_offer"): (
        "Last chance: {discount} off at {store}",
        "Hi {first_name}, our best offer: {discount} off your next {store} order. It expires in "
        "3 days.",
    ),
    ("referral", "referrer_reward"): (
        "Your friend just ordered: {discount} off for you",
        "Hi {first_name}, thanks for spreading the word! Your friend placed their first {store} "
        "order, so your next order is {discount} off.",
    ),
    ("review", "request"): (
        "How was your {store} delivery?",
        "Hi {first_name}, how did we do on today's delivery? Rate it in 10 seconds: {link}",
    ),
    ("review", "public_thanks"): (
        "Thanks for the kind words!",
        "Thanks {first_name}! Would you share that on Google? It helps a local business a lot: "
        "{link}",
    ),
    ("review", "fix_it"): (
        "We're sorry, let us fix this",
        "Hi {first_name}, sorry your order wasn't right. A real person from {store} will reach "
        "out today to make it right.",
    ),
}
