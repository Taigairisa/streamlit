from datetime import date
import calendar


def month_context(budget: int, spent: int, today: date) -> dict:
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed = today.day
    days_left = max(days_in_month - days_passed, 1)
    forecast = int((spent / max(days_passed, 1)) * days_in_month)
    per_day = int(max(budget - spent, 0) / days_left)
    progress_pct = min(100, int(100 * spent / max(budget, 1)))
    return {
        "forecast": forecast,
        "per_day": per_day,
        "progress_pct": progress_pct,
        "days_in_month": days_in_month,
        "days_left": days_left,
    }
