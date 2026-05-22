from typing import Any, cast

import httpx

from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT_S = 10.0  # HTTP client timeout for all server API calls


def get_server_url() -> str:
    """Get server URL from settings (.env or environment)."""
    return settings.server_url


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
        "HTTP %s %s → %s: %s",
        method,
        url,
        response.status_code,
        _response_detail(response),
    )


def _request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    """Issue an HTTP request; log connection/timeout failures with server context."""
    try:
        with httpx.Client() as client:
            return client.request(method, url, timeout=_DEFAULT_TIMEOUT_S, **kwargs)
    except httpx.ConnectError as exc:
        server_url = get_server_url()
        logger.error("Cannot connect to server at %s: %s", server_url, exc)
        raise RuntimeError(
            f"Cannot connect to server at {server_url}. "
            "Is uvicorn running? Try: uv run uvicorn server.main:app --reload --port 8001"
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error("%s %s timed out after %ss: %s", method, url, _DEFAULT_TIMEOUT_S, exc)
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
    logger.info(f"POST {url}")
    logger.debug(f"Payload keys: {list(config.keys())}")

    response = _request("POST", url, json=config)
    logger.debug(f"Response status: {response.status_code}")
    if response.status_code == 404:
        logger.error("POST %s → 404 (no API route at %s)", url, server_url)
        raise RuntimeError(
            f"No route POST {url} (404). Either nothing is running at "
            f"{server_url}, or it is not this project's API. Start it from the repo "
            f"root with: uv run uvicorn server.main:app --reload --port 8001 "
            f'— then confirm GET {server_url}/healthz returns {{"ok": true}}.'
        )
    _ensure_ok(response, method="POST", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info(f"Experiment submitted: {data.get('experiment_id', '?')}")
    return data


def get_experiment(experiment_id: str) -> dict[str, Any]:
    """Get experiment details including run statuses."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}"
    logger.debug(f"GET {url}")

    response = _request("GET", url)
    _ensure_ok(response, method="GET", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.debug(f"Experiment status={data.get('status')}, runs={len(data.get('runs', []))}")
    return data


def get_run_status(run_id: str) -> dict[str, Any]:
    """Get current status of a single run."""
    server_url = get_server_url()
    url = f"{server_url}/runs/{run_id}/status"
    logger.debug(f"GET {url}")

    response = _request("GET", url)
    _ensure_ok(response, method="GET", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.debug(f"Run {run_id} phase={data.get('phase')}")
    return data


def cancel_experiment(experiment_id: str) -> dict[str, Any]:
    """Request cancellation of a running experiment."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}/cancel"
    logger.info(f"POST {url}")

    response = _request("POST", url)
    if response.status_code == 404:
        _log_http_error("POST", url, response)
        raise RuntimeError(f"Experiment {experiment_id} not found")
    if response.status_code == 409:
        _log_http_error("POST", url, response)
        raise RuntimeError(_response_detail(response))
    _ensure_ok(response, method="POST", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info(f"Cancel response: {data}")
    return data


def pause_experiment(experiment_id: str) -> dict[str, Any]:
    """Request pause of a running experiment."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}/pause"
    logger.info(f"POST {url}")

    response = _request("POST", url)
    if response.status_code == 404:
        _log_http_error("POST", url, response)
        raise RuntimeError(f"Experiment {experiment_id} not found")
    if response.status_code == 409:
        _log_http_error("POST", url, response)
        raise RuntimeError(_response_detail(response))
    _ensure_ok(response, method="POST", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info(f"Pause response: {data}")
    return data


def resume_experiment(experiment_id: str) -> dict[str, Any]:
    """Resume a paused experiment."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}/resume"
    logger.info(f"POST {url}")

    response = _request("POST", url)
    if response.status_code == 404:
        _log_http_error("POST", url, response)
        raise RuntimeError(f"Experiment {experiment_id} not found")
    if response.status_code == 409:
        _log_http_error("POST", url, response)
        raise RuntimeError(_response_detail(response))
    _ensure_ok(response, method="POST", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info(f"Resume response: {data}")
    return data


def delete_experiment(experiment_id: str) -> dict[str, Any]:
    """Delete an experiment and all its associated data."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}"
    logger.info(f"DELETE {url}")

    response = _request("DELETE", url)
    if response.status_code == 404:
        _log_http_error("DELETE", url, response)
        raise RuntimeError(f"Experiment {experiment_id} not found")
    if response.status_code == 409:
        _log_http_error("DELETE", url, response)
        raise RuntimeError(_response_detail(response))
    _ensure_ok(response, method="DELETE", url=url)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    logger.info(f"Delete response: {data}")
    return data
