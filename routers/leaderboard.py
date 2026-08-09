from fastapi import APIRouter, Request, Depends
import crud
from auth import get_current_user
from templates_utils import render_template, get_username_map

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.get("")
async def leaderboard_view(request: Request, user: dict = Depends(get_current_user)):
    leaderboard = crud.get_leaderboard_data()
    username_map = get_username_map()
    return render_template("leaderboard.html", request, user=user, leaderboard=leaderboard,
                          username_map=username_map)
