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
        response.raise_for_status()
        return response.json()


def get_experiments() -> dict:
    """Get list of experiments from server."""

    server_url = get_server_url()
    url = f"{server_url}/experiments"

    with httpx.Client() as client:
        response = client.get(url, timeout=10.0)
        response.raise_for_status()
        return response.json()
