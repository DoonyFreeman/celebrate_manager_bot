from db.models import User
from db.repository import SubscriptionRepository, UserRepository


class UserService:
    @staticmethod
    async def register_user(telegram_id: int, username: str | None) -> User:
        existing = await UserRepository.get_by_telegram_id(telegram_id)
        if existing is not None:
            return existing
        return await UserRepository.create(telegram_id, username)

    @staticmethod
    async def get_user(telegram_id: int) -> User | None:
        return await UserRepository.get_by_telegram_id(telegram_id)

    @staticmethod
    async def get_active_subscribers() -> list[User]:
        return await UserRepository.get_active_subscribers()

    @staticmethod
    async def deactivate_user(telegram_id: int) -> None:
        await UserRepository.deactivate(telegram_id)

    @staticmethod
    async def get_subscription_categories(user_id: int) -> list[str]:
        subs = await SubscriptionRepository.get_by_user(user_id)
        return [s.category for s in subs]

    @staticmethod
    async def update_subscriptions(user_id: int, categories: list[str]) -> None:
        await SubscriptionRepository.remove_all(user_id)
        for cat in categories:
            await SubscriptionRepository.add(user_id, cat)

    @staticmethod
    async def clear_subscriptions(user_id: int) -> None:
        await SubscriptionRepository.remove_all(user_id)
