import httpx

from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)


def get_server_url() -> str:
    """Get server URL from settings (.env or environment)."""
    return settings.server_url


def submit_experiment(config: dict) -> dict:
    """Submit experiment configuration to server."""
    server_url = get_server_url()
    url = f"{server_url}/experiments"
    logger.info(f"POST {url}")
    logger.debug(f"Payload keys: {list(config.keys())}")

    with httpx.Client() as client:
        response = client.post(url, json=config, timeout=10.0)
        logger.debug(f"Response status: {response.status_code}")
        if response.status_code == 404:
            raise RuntimeError(
                f"No route POST {url} (404). Either nothing is running at "
                f"{server_url}, or it is not this project's API. Start it from the repo "
                f"root with: uv run uvicorn server.main:app --reload --port 8001 "
                f"— then confirm GET {server_url}/healthz returns {{\"ok\": true}}."
            )
        response.raise_for_status()
        data = response.json()
        logger.info(f"Experiment submitted: {data.get('experiment_id', '?')}")
        return data


def get_experiment(experiment_id: str) -> dict:
    """Get experiment details including run statuses."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}"
    logger.debug(f"GET {url}")

    with httpx.Client() as client:
        response = client.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Experiment status={data.get('status')}, runs={len(data.get('runs', []))}")
        return data


def get_run_status(run_id: str) -> dict:
    """Get current status of a single run."""
    server_url = get_server_url()
    url = f"{server_url}/runs/{run_id}/status"
    logger.debug(f"GET {url}")

    with httpx.Client() as client:
        response = client.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Run {run_id} phase={data.get('phase')}")
        return data


def cancel_experiment(experiment_id: str) -> dict:
    """Request cancellation of a running experiment."""
    server_url = get_server_url()
    url = f"{server_url}/experiments/{experiment_id}/cancel"
    logger.info(f"POST {url}")

    with httpx.Client() as client:
        response = client.post(url, timeout=10.0)
        if response.status_code == 404:
            raise RuntimeError(f"Experiment {experiment_id} not found")
        if response.status_code == 409:
            detail = response.json().get("detail", "Experiment is not running")
            raise RuntimeError(detail)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Cancel response: {data}")
        return data
