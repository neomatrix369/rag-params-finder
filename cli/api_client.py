from typing import Any, cast
from urllib.parse import urlparse

import httpx

from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT_S = 10.0  # HTTP client timeout for all server API calls


def get_server_url() -> str:
    """Get server URL from settings (.env or environment)."""
    return settings.server_url


def _http_label(method: str, url: str) -> str:
    path = urlparse(url).path or url
    return f"{method} {path}"


def _response_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            detail = body.get("detail")
            if isinstance(detail, str):
                return detail
            error = body.get("error")
            if isinstance(error, str):
                return error
    except Exception:
        pass
    text = response.text.strip()
    return text[:200] if text else "(empty body)"


def _log_http_error(method: str, url: str, response: httpx.Response) -> None:
    logger.error(
        "HTTP error — %s %s: %s",
        response.status_code,
        _http_label(method, url),
        _response_detail(response),
    )


def _request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    """Issue an HTTP request; log connection/timeout failures with server context."""
    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT_S) as client:
            return client.request(method, url, **kwargs)
    except httpx.ConnectError as exc:
        server_url = get_server_url()
        logger.error("network failure — cannot connect to %s: %s", server_url, exc)
        raise RuntimeError(
            f"Cannot connect to server at {server_url}. "
            "Is uvicorn running? Try: uv run uvicorn server.main:app --reload --port 8001"
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error(
            "timeout — %s timed out after %ss: %s",
            _http_label(method, url),
            _DEFAULT_TIMEOUT_S,
            exc,
        )
        raise RuntimeError(
            f"Request timed out after {_DEFAULT_TIMEOUT_S}s: {method} {url}"
        ) from exc


def _ensure_ok(response: httpx.Response, *, method: str, url: str) -> None:
    if response.is_success:
        return
    _log_http_error(method, url, response)
    response.raise_for_status()


def submit_experiment(config: dict[str, Any]) -> dict[str, Any]:
    """Submit experiment configuration to server."""
    server_url = get_server_url()
    url = f"{server_url}/experiments"
    logger.info("submit started — %s", _http_label("POST", url))
    logger.debug("submit payload — keys=%s", list(config.keys()))

    response = _request("POST", url, json=config)
    logger.debug("submit response — status=%s", response.status_code)
    if response.status_code == 404:
        logger.error(
            "submit failed — %s → 404 (no API route at %s)",
            _http_label("POST", url),
            server_url,
        )
        raise RuntimeError(
            f"No route POST {url} (404). Either nothing is running at "
            f"{server_url}, or it is not this project's API. Start it from the repo "
            f"root with: uv run uvicorn server.main:app --reload --port 8001 "
            f'— then confirm GET {server_url}/healthz returns {{"ok": true, "mongodb": "ok"}}.'
        )
    _ensure_ok(response, method="POST", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info("submit OK — experiment_id=%s", data.get("experiment_id", "?"))
    return data


def get_experiment(experiment_id: str) -> dict[str, Any]:
    """Get experiment details including run statuses."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}"
    logger.debug("detail poll — %s", _http_label("GET", url))

    response = _request("GET", url)
    _ensure_ok(response, method="GET", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.debug(
        "detail poll OK — status=%s, runs=%s",
        data.get("status"),
        len(data.get("runs", [])),
    )
    return data


def get_run_status(run_id: str) -> dict[str, Any]:
    """Get current status of a single run."""
    server_url = get_server_url()
    url = f"{server_url}/runs/{run_id}/status"
    logger.debug("run status — %s", _http_label("GET", url))

    response = _request("GET", url)
    _ensure_ok(response, method="GET", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.debug("run status OK — %s phase=%s", run_id, data.get("phase"))
    return data


def cancel_experiment(experiment_id: str) -> dict[str, Any]:
    """Request cancellation of a running experiment."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}/cancel"
    logger.info("cancel started — %s", _http_label("POST", url))

    response = _request("POST", url)
    if response.status_code == 404:
        _log_http_error("POST", url, response)
        raise RuntimeError(f"Experiment {experiment_id} not found")
    if response.status_code == 409:
        _log_http_error("POST", url, response)
        raise RuntimeError(_response_detail(response))
    _ensure_ok(response, method="POST", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info("cancel OK — %s", data)
    return data


def pause_experiment(experiment_id: str) -> dict[str, Any]:
    """Request pause of a running experiment."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}/pause"
    logger.info("pause started — %s", _http_label("POST", url))

    response = _request("POST", url)
    if response.status_code == 404:
        _log_http_error("POST", url, response)
        raise RuntimeError(f"Experiment {experiment_id} not found")
    if response.status_code == 409:
        _log_http_error("POST", url, response)
        raise RuntimeError(_response_detail(response))
    _ensure_ok(response, method="POST", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info("pause OK — %s", data)
    return data


def resume_experiment(experiment_id: str) -> dict[str, Any]:
    """Resume a paused experiment."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}/resume"
    logger.info("resume started — %s", _http_label("POST", url))

    response = _request("POST", url)
    if response.status_code == 404:
        _log_http_error("POST", url, response)
        raise RuntimeError(f"Experiment {experiment_id} not found")
    if response.status_code == 409:
        _log_http_error("POST", url, response)
        raise RuntimeError(_response_detail(response))
    _ensure_ok(response, method="POST", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info("resume OK — %s", data)
    return data


def delete_experiment(experiment_id: str) -> dict[str, Any]:
    """Delete an experiment and all its associated data."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}"
    logger.info("delete started — %s", _http_label("DELETE", url))

    response = _request("DELETE", url)
    if response.status_code == 404:
        _log_http_error("DELETE", url, response)
        raise RuntimeError(f"Experiment {experiment_id} not found")
    if response.status_code == 409:
        _log_http_error("DELETE", url, response)
        raise RuntimeError(_response_detail(response))
    _ensure_ok(response, method="DELETE", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info("delete OK — %s", data)
    return data
