from fastapi import APIRouter

from app.domains.compliance.disclaimers import GENERAL_DISCLAIMER

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


@router.get("/disclaimer")
async def get_disclaimer():
    return {"disclaimer": GENERAL_DISCLAIMER}
