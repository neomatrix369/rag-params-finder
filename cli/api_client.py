import httpx
import os


def get_server_url() -> str:
    """Get server URL from environment or use default."""
    return os.environ.get("SERVER_URL", "http://localhost:8000")


def submit_experiment(config: dict) -> dict:
    """Submit experiment configuration to server."""

    server_url = get_server_url()
    url = f"{server_url}/experiments"

    with httpx.Client() as client:
        response = client.post(url, json=config, timeout=10.0)
        if response.status_code == 404:
            raise RuntimeError(
                f"No route POST {url} (404). Either nothing is running at "
                f"{server_url}, or it is not this project's API. Start it from the repo "
                f"root with: uv run uvicorn server.main:app --reload "
                f"— then confirm GET {server_url}/healthz returns {{\"ok\": true}}."
            )
        response.raise_for_status()
        return response.json()


def get_experiments() -> dict:
    """Get list of experiments from server."""

    server_url = get_server_url()
    url = f"{server_url}/experiments"

    with httpx.Client() as client:
        response = client.get(url, timeout=10.0)
        if response.status_code == 404:
            raise RuntimeError(
                f"No route GET {url} (404). Start the API from the repo root: "
                f"uv run uvicorn server.main:app --reload"
            )
        response.raise_for_status()
        return response.json()
