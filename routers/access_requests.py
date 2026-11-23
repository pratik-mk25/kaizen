import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from postgrest.exceptions import APIError

from database import supabase_admin
from templates_utils import render_template

router = APIRouter(prefix="/request-access")
DOMAIN_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
EMAIL = re.compile(r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
                   + DOMAIN_LABEL + r"(?:\." + DOMAIN_LABEL + r")+", re.ASCII)


def page(request, status=200, **context):
    response = render_template("request_access.html", request, username_map={}, **context)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("")
def form(request: Request):
    return page(request)


@router.get("/received")
def received(request: Request):
    return page(request, received=True)


@router.post("")
def submit(request: Request, club_name: str = Form(""), contact_email: str = Form("")):
    club_name = club_name.strip()
    contact_email = contact_email.strip().lower()
    values = {"club_name": club_name, "contact_email": contact_email}
    if not (1 <= len(club_name) <= 120 and club_name.isprintable()):
        return page(request, 422, error="Enter a club name of up to 120 printable characters.", **values)
    if (len(contact_email) > 254 or len(contact_email.partition("@")[0]) > 64
            or not EMAIL.fullmatch(contact_email)):
        return page(request, 422, error="Enter a valid contact email address.", **values)

    try:
        supabase_admin.table("club_access_requests").insert(values, returning="minimal").execute()
    except APIError as exc:
        # A retry of a pending request gets the same receipt.
        if exc.code != "23505":
            return page(request, 503, error="Unable to submit right now. Please try again.", **values)
    except Exception:
        return page(request, 503, error="Unable to submit right now. Please try again.", **values)
    return RedirectResponse("/request-access/received", status_code=303)
