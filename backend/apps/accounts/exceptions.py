import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error")
        return Response(
            {"detail": "An unexpected error occurred. Please try again later."},
            status=500,
        )

    detail = None
    errors = response.data
    if isinstance(response.data, dict) and "detail" in response.data and len(response.data) == 1:
        detail = response.data["detail"]
        errors = None
    elif isinstance(response.data, dict):
        detail = "Request could not be completed."
    elif isinstance(response.data, list):
        detail = response.data[0] if response.data else "Request could not be completed."
        errors = response.data

    payload = {"detail": str(detail) if detail is not None else "Request could not be completed."}
    if errors is not None and not (isinstance(errors, dict) and list(errors.keys()) == ["detail"]):
        payload["errors"] = errors
    response.data = payload
    return response
