from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.dependencies import (
    get_admin_auth_service,
    get_contact_service,
    get_file_service,
)
from app.core.request_context import client_identifier
from app.domain.exceptions import (
    ContactNotFoundError,
    FileAlreadyExistsError,
    FileNotAvailableError,
    FileTooLargeError,
    InvalidFilenameError,
)
from app.domain.models import ContactStatus
from app.services.auth_service import AdminAuthService
from app.services.contact_service import ContactService
from app.services.file_service import FileService

router = APIRouter(prefix="/admin", tags=["admin"], include_in_schema=False)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    if request.session.get("admin_authenticated"):
        return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)
    return _template(
        request,
        "admin/login.html",
        {"error": None},
    )


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    auth: AdminAuthService = Depends(get_admin_auth_service),
) -> HTMLResponse:
    if not request.app.state.admin_rate_limiter.allow(
        client_identifier(request)
    ):
        return _template(
            request,
            "admin/login.html",
            {
                "error": (
                    "Too many sign-in attempts. Please wait 15 minutes "
                    "and try again."
                )
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    if not auth.verify(username, password):
        return _template(
            request,
            "admin/login.html",
            {"error": "The username or password is incorrect."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    request.session.clear()
    request.session["admin_authenticated"] = True
    request.session["csrf_token"] = auth.new_csrf_token()
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: Annotated[str, Form()],
    auth: AdminAuthService = Depends(get_admin_auth_service),
) -> RedirectResponse:
    _require_admin(request)
    _verify_csrf(request, csrf_token, auth)
    request.session.clear()
    return RedirectResponse(
        "/admin/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: Annotated[str, Query(max_length=100)] = "",
    status_filter: Annotated[str, Query(alias="status")] = "",
    contacts: ContactService = Depends(get_contact_service),
    files: FileService = Depends(get_file_service),
) -> HTMLResponse:
    _require_admin(request)
    selected_status = _parse_status(status_filter)
    return _template(
        request,
        "admin/dashboard.html",
        {
            "contacts": contacts.list(
                search=q,
                status=selected_status,
                limit=200,
            ),
            "counts": contacts.counts(),
            "files": files.list_files(),
            "query": q,
            "status_filter": selected_status.value if selected_status else "",
            "contact_statuses": tuple(ContactStatus),
            "notification_channels": contacts.configured_notification_channels,
            "flash": request.session.pop("flash", None),
            "csrf_token": request.session["csrf_token"],
            "max_upload_mb": (
                request.app.state.settings.max_upload_bytes // (1024 * 1024)
            ),
        },
    )


@router.get("/contacts/{contact_id}", response_class=HTMLResponse)
def contact_detail(
    contact_id: int,
    request: Request,
    contacts: ContactService = Depends(get_contact_service),
) -> HTMLResponse:
    _require_admin(request)
    try:
        contact = contacts.get(contact_id)
        if contact.status is ContactStatus.NEW:
            contact = contacts.update_status(contact_id, ContactStatus.READ)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return _template(
        request,
        "admin/contact_detail.html",
        {
            "contact": contact,
            "contact_statuses": tuple(ContactStatus),
            "csrf_token": request.session["csrf_token"],
            "flash": request.session.pop("flash", None),
        },
    )


@router.post("/contacts/{contact_id}/status")
def update_contact_status(
    contact_id: int,
    request: Request,
    contact_status: Annotated[str, Form(alias="status")],
    csrf_token: Annotated[str, Form()],
    auth: AdminAuthService = Depends(get_admin_auth_service),
    contacts: ContactService = Depends(get_contact_service),
) -> RedirectResponse:
    _require_admin(request)
    _verify_csrf(request, csrf_token, auth)
    parsed_status = _parse_status(contact_status)
    if parsed_status is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid contact status.",
        )
    try:
        contacts.update_status(contact_id, parsed_status)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    _flash(request, "Contact status updated.", "success")
    return RedirectResponse(
        f"/admin/contacts/{contact_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/contacts/{contact_id}/delete")
def delete_contact(
    contact_id: int,
    request: Request,
    csrf_token: Annotated[str, Form()],
    auth: AdminAuthService = Depends(get_admin_auth_service),
    contacts: ContactService = Depends(get_contact_service),
) -> RedirectResponse:
    _require_admin(request)
    _verify_csrf(request, csrf_token, auth)
    try:
        contacts.delete(contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    _flash(request, "Contact submission deleted.", "success")
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/files/upload")
def upload_file(
    request: Request,
    upload: Annotated[UploadFile, File()],
    csrf_token: Annotated[str, Form()],
    auth: AdminAuthService = Depends(get_admin_auth_service),
    files: FileService = Depends(get_file_service),
) -> RedirectResponse:
    _require_admin(request)
    _verify_csrf(request, csrf_token, auth)
    filename = upload.filename or ""
    try:
        files.save_file(
            filename,
            upload.file,
            request.app.state.settings.max_upload_bytes,
        )
    except (
        InvalidFilenameError,
        FileAlreadyExistsError,
        FileTooLargeError,
    ) as exc:
        _flash(request, str(exc), "error")
    else:
        _flash(request, f"'{filename}' is now downloadable.", "success")
    finally:
        upload.file.close()
    return RedirectResponse("/admin#files", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/files/{filename}/delete")
def delete_file(
    filename: str,
    request: Request,
    csrf_token: Annotated[str, Form()],
    auth: AdminAuthService = Depends(get_admin_auth_service),
    files: FileService = Depends(get_file_service),
) -> RedirectResponse:
    _require_admin(request)
    _verify_csrf(request, csrf_token, auth)
    try:
        files.delete_file(filename)
    except (InvalidFilenameError, FileNotAvailableError) as exc:
        _flash(request, str(exc), "error")
    else:
        _flash(request, f"'{filename}' was deleted.", "success")
    return RedirectResponse("/admin#files", status_code=status.HTTP_303_SEE_OTHER)


def _require_admin(request: Request) -> None:
    if not request.session.get("admin_authenticated"):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )


def _verify_csrf(
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


def _parse_status(value: str) -> ContactStatus | None:
    if not value:
        return None
    try:
        return ContactStatus(value)
    except ValueError:
        return None


def _template(
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


def _flash(request: Request, message: str, category: str) -> None:
    request.session["flash"] = {"message": message, "category": category}
