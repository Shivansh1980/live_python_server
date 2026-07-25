from fastapi import HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.services.auth_service import AdminAuthService


def require_admin(request: Request) -> None:
    if not request.session.get("admin_authenticated"):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )


def verify_csrf(
    request: Request,
    supplied_token: str,
    auth: AdminAuthService,
) -> None:
    expected_token = str(request.session.get("csrf_token", ""))
    if not auth.verify_csrf(expected_token, supplied_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token.",
        )


def template(
    request: Request,
    name: str,
    context: dict[str, object],
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        request=request,
        name=name,
        context=context,
        status_code=status_code,
    )


def flash(request: Request, message: str, category: str) -> None:
    request.session["flash"] = {"message": message, "category": category}
