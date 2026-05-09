import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from db.models import Holiday
from db.repository import NotificationLogRepository
from services.user_service import UserService

logger = logging.getLogger(__name__)


def _format_holiday_message(holidays: list[Holiday]) -> str:
    if not holidays:
        return "Сегодня нет праздников."

    lines = ["<b>Праздники сегодня:</b>\n"]
    for h in holidays:
        lines.append(f"\U0001f389 <b>{h.name}</b>")
        if h.description:
            lines.append(f"  <i>{h.description}</i>")
    return "\n".join(lines)


async def send_daily_notifications(bot: Bot) -> None:
    from services.holiday_service import get_today_holidays

    holidays = await get_today_holidays()
    if not holidays:
        logger.info("No holidays today, skipping notifications")
        return

    users = await UserService.get_active_subscribers()

    for user in users:
        user_id = user.id
        if user_id is None:
            continue

        user_subs = await UserService.get_subscription_categories(user_id)

        if not user_subs:
            continue

        relevant = [h for h in holidays if h.category in user_subs or "all" in user_subs]

        if not relevant:
            continue

        try:
            text = _format_holiday_message(relevant)
            await bot.send_message(chat_id=user.telegram_id, text=text, parse_mode="HTML")

            for h in relevant:
                if h.id is not None and user_id is not None:
                    await NotificationLogRepository.add(user_id, h.id)

        except TelegramForbiddenError:
            logger.warning("Bot blocked by user %s, deactivating", user.telegram_id)
            await UserService.deactivate_user(user.telegram_id)
        except Exception:
            logger.exception("Failed to send notification to user %s", user.telegram_id)
