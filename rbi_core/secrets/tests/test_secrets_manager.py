"""Unit tests for SecretsManager — TDD RED phase.

All keyring calls are mocked; no actual OS keyring interaction
occurs during the test suite.
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from rbi_core.secrets.secrets_manager import SecretsManager
from rbi_core.exceptions import SecretsNotFoundError


SERVICE = "rbi_swarm"
KEY = "exchange_api_key"
VALUE = "super_secret_value"


class TestGetSecret:

    def test_returns_value_when_found(self):
        with patch("keyring.get_password", return_value=VALUE):
            result = SecretsManager.get_secret(SERVICE, KEY)
        assert result == VALUE

    def test_raises_secrets_not_found_when_none(self):
        with patch("keyring.get_password", return_value=None):
            with pytest.raises(SecretsNotFoundError, match=KEY):
                SecretsManager.get_secret(SERVICE, KEY)

    def test_error_message_includes_service_and_key(self):
        with patch("keyring.get_password", return_value=None):
            try:
                SecretsManager.get_secret(SERVICE, KEY)
            except SecretsNotFoundError as exc:
                assert SERVICE in str(exc)
                assert KEY in str(exc)

    def test_calls_keyring_with_correct_args(self):
        with patch("keyring.get_password", return_value=VALUE) as mock_get:
            SecretsManager.get_secret(SERVICE, KEY)
            mock_get.assert_called_once_with(SERVICE, KEY)


@pytest.fixture
def capture_secret_logs(caplog):
    logger = logging.getLogger("rbi_core.secrets.secrets_manager")
    # Capture at the source without depending on root handler configuration.
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.DEBUG, logger=logger.name):
            yield caplog
    finally:
        logger.removeHandler(caplog.handler)


class TestSetSecret:

    def test_calls_keyring_set_password(self):
        with patch("keyring.set_password") as mock_set:
            SecretsManager.set_secret(SERVICE, KEY, VALUE)
            mock_set.assert_called_once_with(SERVICE, KEY, VALUE)

    def test_emits_structured_log_on_set(self, capture_secret_logs):
        with patch("keyring.set_password"):
            SecretsManager.set_secret(SERVICE, KEY, VALUE)
        assert any(
            record.levelno == logging.INFO
            and getattr(record, "event", None) == "secret_stored"
            for record in capture_secret_logs.records
        )

    def test_does_not_log_secret_value(self, capture_secret_logs):
        with patch("keyring.set_password"):
            SecretsManager.set_secret(SERVICE, KEY, VALUE)
        assert capture_secret_logs.records
        for record in capture_secret_logs.records:
            assert VALUE not in record.getMessage()
            assert VALUE not in str(record.__dict__)


class TestDeleteSecret:

    def test_calls_keyring_delete_password(self):
        with patch("keyring.delete_password") as mock_del:
            SecretsManager.delete_secret(SERVICE, KEY)
            mock_del.assert_called_once_with(SERVICE, KEY)

    def test_does_not_raise_when_secret_not_found(self):
        import keyring.errors
        with patch("keyring.delete_password", side_effect=keyring.errors.PasswordDeleteError):
            # Must not propagate — missing secret on delete is not an error
            SecretsManager.delete_secret(SERVICE, KEY)
