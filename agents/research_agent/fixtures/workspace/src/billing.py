"""Billing helpers."""


def monthly_price(plan: str) -> int:
    # Prices in INR; keep in sync with the pricing page.
    return {"starter": 499, "pro": 1499}.get(plan.lower(), 0)
