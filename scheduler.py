import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-not-found]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-not-found]

from config import settings
from services.notification_service import send_daily_notifications

logger = logging.getLogger(__name__)


async def daily_job(bot: Bot) -> None:
    logger.info("Running daily notification job")
    await send_daily_notifications(bot)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    hour, minute = settings.notify_time.split(":")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        daily_job,
        trigger=CronTrigger(hour=int(hour), minute=int(minute)),
        kwargs={"bot": bot},
        id="daily_notification",
        replace_existing=True,
    )

    logger.info("Scheduler configured for %s:%s daily", hour, minute)
    return scheduler
