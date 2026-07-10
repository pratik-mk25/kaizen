from fastapi import APIRouter, Form, Response, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/settings", tags=["settings"])

@router.post("/preferences")
async def update_preferences(
    request: Request
):
    form_data = await request.form()
    # Handle multiple values (hidden input + button click) by taking the last one
    theme = form_data.getlist("theme")[-1] if form_data.getlist("theme") else "dark"
    ui_mode = form_data.getlist("ui_mode")[-1] if form_data.getlist("ui_mode") else "tactical"

    # Get the URL to redirect back to (referer) or default to dashboard
    referer = request.headers.get("referer", "/dashboard")
    response = RedirectResponse(url=referer, status_code=303)
    
    # Set cookies with a long expiration (e.g., 1 year)
    max_age = 365 * 24 * 60 * 60
    
    if theme in ("dark", "light", "system"):
        response.set_cookie(key="theme", value=theme, max_age=max_age, path="/")
    
    if ui_mode in ("tactical", "standard"):
        response.set_cookie(key="ui_mode", value=ui_mode, max_age=max_age, path="/")
        
    return response
