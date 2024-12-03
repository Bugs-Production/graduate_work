from fastapi import APIRouter, Depends

from api.jwt_access_token import require_admin
from api.v1.admin.subscription import router as subscription_router
from api.v1.admin.subscription_plan import router as subscription_plan_router
from api.v1.admin.transaction import router as transaction_router

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
router.include_router(subscription_router, prefix="/subscriptions")
router.include_router(subscription_plan_router, prefix="/subscription_plans")
router.include_router(transaction_router, prefix="/transactions")
