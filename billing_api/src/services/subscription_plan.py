from models.models import SubscriptionPlan
from schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanUpdate
from services.base import SQLAlchemyRepository


class SubscriptionPlanService(
    SQLAlchemyRepository[SubscriptionPlan, SubscriptionPlanCreate, SubscriptionPlanUpdate]
):
    def __init__(self):
        super().__init__(model=SubscriptionPlan)


async def get_subscription_plan_service() -> SubscriptionPlanService:
    return SubscriptionPlanService()
