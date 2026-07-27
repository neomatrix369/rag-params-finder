"""Tests for cooperative experiment cancel/pause controls."""

from __future__ import annotations

import pytest

from server.core.experiment_control import (
    ExperimentCancelledError,
    check_control,
    register_sweep_control,
    request_cancel,
    unregister_sweep_control,
)


class TestExperimentControl:
    """Scenario: cancel and pause signals for in-flight sweeps."""

    def setup_method(self) -> None:
        unregister_sweep_control("exp-test")

    def teardown_method(self) -> None:
        unregister_sweep_control("exp-test")

    def test_request_cancel_before_register_returns_false(self):
        """
        Given no sweep control registered
        When request_cancel is called
        Then it returns False.
        """
        assert request_cancel("exp-missing") is False

    def test_cancel_signalled_raises_on_check(self):
        """
        Given a registered sweep control
        When request_cancel is called
        Then check_control raises ExperimentCancelledError.
        """
        register_sweep_control("exp-test")
        assert request_cancel("exp-test") is True

        with pytest.raises(ExperimentCancelledError, match="cancelled"):
            check_control("exp-test")

    def test_register_is_idempotent(self):
        """
        Given register_sweep_control is called twice
        When request_cancel is called once
        Then check_control still raises.
        """
        register_sweep_control("exp-test")
        register_sweep_control("exp-test")
        request_cancel("exp-test")

        with pytest.raises(ExperimentCancelledError):
            check_control("exp-test")
