from unittest.mock import patch

from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from main import app

client = TestClient(app)
data = {"club_name": "  Robotics Club ", "contact_email": " CLUB@example.org "}


def test_public_form():
    response = client.get("/request-access")
    assert response.status_code == 200
    assert 'action="/request-access"' in response.text


@patch("routers.access_requests.supabase_admin")
def test_request_only(db):
    response = client.post("/request-access", data={**data, "status": "approved"})
    assert response.url.path == "/request-access/received"
    assert "Request received" in response.text
    db.table.assert_called_once_with("club_access_requests")
    db.table.return_value.insert.assert_called_once_with(
        {"club_name": "Robotics Club", "contact_email": "club@example.org"}, returning="minimal"
    )
    db.table.return_value.insert.return_value.execute.assert_called_once_with()


@patch("routers.access_requests.supabase_admin")
def test_invalid_input(db):
    for fields in ({}, {"club_name": " "}, {"club_name": "x" * 121},
                   {"club_name": "two\nlines"}, {"contact_email": "bad..local@example.org"}):
        payload = {**data, **fields} if fields else {}
        assert client.post("/request-access", data=payload).status_code == 422
    db.table.assert_not_called()


@patch("routers.access_requests.supabase_admin")
def test_retries_and_storage_failures(db):
    execute = db.table.return_value.insert.return_value.execute
    execute.side_effect = APIError({"code": "23505", "message": "duplicate"})
    assert client.post("/request-access", data=data).url.path == "/request-access/received"
    execute.side_effect = RuntimeError("private details")
    response = client.post("/request-access", data=data)
    assert response.status_code == 503
    assert "private details" not in response.text


@patch("routers.access_requests.notify_club_access_request")
@patch("routers.access_requests.supabase_admin")
def test_only_new_requests_trigger_mail(db, notify):
    assert client.post("/request-access", data=data).status_code == 200
    notify.assert_called_once_with("Robotics Club", "club@example.org")
    notify.reset_mock()
    execute = db.table.return_value.insert.return_value.execute
    for error in [APIError({"code": "23505", "message": "duplicate"}), RuntimeError()]:
        execute.side_effect = error
        client.post("/request-access", data=data)
    notify.assert_not_called()


@patch.dict("os.environ", {"KAIZEN_GMAIL_SENDER": "sender@example.org",
                           "KAIZEN_GMAIL_APP_PASSWORD": "test-only"})
@patch("notifications.smtplib.SMTP_SSL")
def test_direct_mail_recipient(smtp):
    from notifications import notify_club_access_request

    notify_club_access_request("Robotics Club", "club@example.org")
    connection = smtp.return_value.__enter__.return_value
    message = connection.send_message.call_args.args[0]
    assert message["To"] == "vihangdroneclub@gmail.com"
    assert "club@example.org" in message.get_content()
