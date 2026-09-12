"""
jalali.py
=========

تبدیل تاریخ میلادی به شمسی (جلالی) به‌صورت خالص و بدون نیاز به هیچ
Dependency خارجی. فقط برای نمایش تاریخ‌ها در داشبورد استفاده می‌شود.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

_MONTH_NAMES = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]

_WEEKDAY_NAMES = [
    "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه",
    "جمعه", "شنبه", "یکشنبه",
]


def _gregorian_to_jalali(gy: int, gm: int, gd: int) -> Tuple[int, int, int]:
    """تبدیل (سال، ماه، روز) میلادی به معادل شمسی."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1

    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    g_day_no += g_d_m[gm2] + gd2
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    if j_day_no < 186:
        jm = 1 + j_day_no // 31
        jd = 1 + j_day_no % 31
    else:
        jm = 7 + (j_day_no - 186) // 30
        jd = 1 + (j_day_no - 186) % 30

    return jy, jm, jd


def _to_persian_digits(text: str) -> str:
    """تبدیل ارقام انگلیسی به فارسی."""
    mapping = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return text.translate(mapping)


def to_jalali_str(dt: Optional[datetime], with_time: bool = True,
                  persian_digits: bool = True) -> str:
    """
    تبدیل یک شیء datetime به رشته‌ی تاریخ شمسی خوانا.
    اگر ورودی None باشد رشته‌ی خالی («—») برمی‌گرداند.
    """
    if not dt:
        return "—"
    if isinstance(dt, str):
        # تلاش برای parse تاریخ‌های ذخیره‌شده به‌صورت رشته
        try:
            dt = datetime.fromisoformat(dt)
        except (ValueError, TypeError):
            return dt

    jy, jm, jd = _gregorian_to_jalali(dt.year, dt.month, dt.day)
    month_name = _MONTH_NAMES[jm - 1]
    result = f"{jd} {month_name} {jy}"
    if with_time:
        result += f" - {dt.hour:02d}:{dt.minute:02d}"

    return _to_persian_digits(result) if persian_digits else result


def fa_number(value) -> str:
    """قالب‌بندی عدد با جداکننده‌ی هزارگان و ارقام فارسی."""
    try:
        formatted = f"{int(value):,}"
    except (ValueError, TypeError):
        formatted = str(value)
    return _to_persian_digits(formatted)
