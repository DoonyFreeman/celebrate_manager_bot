import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import CATEGORIES, category_keyboard
from services.holiday_service import get_today_holidays
from services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router()


async def _get_local_user_id(telegram_id: int) -> int | None:
    user = await UserService.get_user(telegram_id)
    if user is None:
        return None
    return user.id


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await UserService.register_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    await message.answer(
        "Welcome to Celebrate Bot!\n\n"
        "I'll send you daily notifications about holidays.\n"
        "Use /subscribe to choose which categories interest you."
    )


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message) -> None:
    await message.answer(
        "Choose holiday categories you want to receive:",
        reply_markup=category_keyboard([]),
    )


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message) -> None:
    user_id = await _get_local_user_id(message.from_user.id)
    if user_id is not None:
        await UserService.clear_subscriptions(user_id)
    await message.answer(
        "You've been unsubscribed from all categories.\nUse /subscribe to choose new categories."
    )


@router.message(Command("categories"))
async def cmd_categories(message: Message) -> None:
    user_id = await _get_local_user_id(message.from_user.id)
    if user_id is None:
        await message.answer("Use /start first to register.")
        return

    subs = await UserService.get_subscription_categories(user_id)
    if not subs:
        await message.answer("You have no subscriptions.\nUse /subscribe to choose categories.")
        return

    cat_names = {c[0]: c[1] for c in CATEGORIES}
    lines = ["Your current subscriptions:"]
    for s in subs:
        name = cat_names.get(s, s)
        lines.append(f"\u2022 {name}")
    lines.append("")
    lines.append("Use /subscribe to change.")
    await message.answer("\n".join(lines))


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    user_id = await _get_local_user_id(message.from_user.id)
    if user_id is None:
        await message.answer("Use /start first to register.")
        return

    holidays = await get_today_holidays()
    if not holidays:
        await message.answer("No holidays today.")
        return

    subs = await UserService.get_subscription_categories(user_id)
    if not subs:
        await message.answer("No holidays today.\nUse /subscribe to choose categories.")
        return

    relevant = [h for h in holidays if h.category in subs or "all" in subs]

    if not relevant:
        await message.answer("No holidays in your subscribed categories today.")
        return

    lines = ["<b>Holidays today:</b>\n"]
    for h in relevant:
        lines.append(f"\U0001f389 <b>{h.name}</b>")
        if h.description:
            lines.append(f"  <i>{h.description}</i>")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Available commands:\n\n"
        "/start - Register\n"
        "/subscribe - Choose categories\n"
        "/unsubscribe - Unsubscribe from all\n"
        "/categories - View subscriptions\n"
        "/today - Holidays today\n"
        "/help - This message"
    )


@router.callback_query(F.data.startswith("sub:"))
async def callback_subscription(callback: CallbackQuery) -> None:
    action = callback.data.removeprefix("sub:")

    if action == "done":
        await callback.message.edit_text("Subscriptions updated!")
        await callback.answer()
        return

    user_id = await _get_local_user_id(callback.from_user.id)
    if user_id is None:
        await callback.answer("Use /start first to register.", show_alert=True)
        return

    current_subs = await UserService.get_subscription_categories(user_id)

    if action in current_subs:
        new_subs = [s for s in current_subs if s != action]
    else:
        new_subs = current_subs + [action]

    await UserService.update_subscriptions(user_id, new_subs)

    await callback.message.edit_reply_markup(reply_markup=category_keyboard(new_subs))
    await callback.answer()
