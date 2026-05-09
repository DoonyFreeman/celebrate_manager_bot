from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

CATEGORIES: list[tuple[str, str]] = [
    ("national", "National"),
    ("observance", "Observance"),
    ("seasonal", "Seasonal"),
    ("local", "Local"),
    ("religious", "Religious"),
    ("other", "Other"),
]


def category_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat_id, cat_label in CATEGORIES:
        prefix = "\U0001f7c8 " if cat_id not in selected else "\u2705 "
        builder.button(text=f"{prefix}{cat_label}", callback_data=f"sub:{cat_id}")
    builder.button(text="\u2705 Done", callback_data="sub:done")
    builder.adjust(1)
    return builder.as_markup()
