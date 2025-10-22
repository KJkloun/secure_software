from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

PROBLEM_BASE_URI = "https://ideacatalog.app/problems"


def _default_title(code: str) -> str:
    return code.replace("_", " ").replace("-", " ").capitalize()


def _problem_type(code: str) -> str:
    safe = code.strip().lower().replace(" ", "-")
    return f"{PROBLEM_BASE_URI}/{safe}"


def _merge_extras(
    payload: Dict[str, Any], extras: Dict[str, Any] | None
) -> Dict[str, Any]:
    if not extras:
        return payload
    reserved = {"type", "title", "status", "detail", "correlation_id", "code"}
    for key, value in extras.items():
        if key in reserved:
            continue
        payload[key] = value
    return payload


def problem_response(
    *,
    status: int,
    code: str,
    detail: str,
    request: Optional[Request] = None,
    title: Optional[str] = None,
    type_: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    correlation_id = str(uuid4())
    if request is not None:
        request.state.correlation_id = correlation_id

    payload: Dict[str, Any] = {
        "type": type_ or _problem_type(code),
        "title": title or _default_title(code),
        "status": status,
        "detail": detail,
        "correlation_id": correlation_id,
        "code": code,
    }
    payload = _merge_extras(payload, extras)

    response = JSONResponse(payload, status_code=status)
    response.headers["X-Correlation-Id"] = correlation_id
    return response


@dataclass
class ApiProblem(Exception):
    code: str
    detail: str
    status: int = 400
    title: Optional[str] = None
    type_: Optional[str] = None
    extras: Optional[Dict[str, Any]] = None

    def as_response(self, request: Optional[Request] = None) -> JSONResponse:
        return problem_response(
            status=self.status,
            code=self.code,
            detail=self.detail,
            request=request,
            title=self.title,
            type_=self.type_,
            extras=self.extras,
        )
