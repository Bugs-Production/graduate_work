from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get():
    return {"detail": "success"}
