"""Testes para hierarquia de erros e utilitário de retry.

Testa:
- Hierarquia de exceções (herança de TrainingError)
- ValidationError com lista de erros
- retry_with_backoff: sucesso na primeira tentativa
- retry_with_backoff: sucesso após falhas
- retry_with_backoff: falha após esgotar tentativas
"""

import time
from unittest.mock import patch

import pytest

from managers.errors import (
    ContentLoadError,
    ModuleNotFoundError,
    PathUnavailableError,
    ProgressSaveError,
    TrainingError,
    ValidationError,
)
from managers.utils import retry_with_backoff


# ============================================================
# Testes da Hierarquia de Erros
# ============================================================


class TestErrorHierarchy:
    """Verifica que todas as exceções herdam de TrainingError."""

    def test_training_error_is_exception(self):
        assert issubclass(TrainingError, Exception)

    def test_progress_save_error_inherits_training_error(self):
        assert issubclass(ProgressSaveError, TrainingError)

    def test_content_load_error_inherits_training_error(self):
        assert issubclass(ContentLoadError, TrainingError)

    def test_validation_error_inherits_training_error(self):
        assert issubclass(ValidationError, TrainingError)

    def test_module_not_found_error_inherits_training_error(self):
        assert issubclass(ModuleNotFoundError, TrainingError)

    def test_path_unavailable_error_inherits_training_error(self):
        assert issubclass(PathUnavailableError, TrainingError)

    def test_catch_all_errors_with_training_error(self):
        """Todas as exceções do sistema podem ser capturadas com TrainingError."""
        errors = [
            ProgressSaveError("falha"),
            ContentLoadError("timeout"),
            ValidationError(["erro1"]),
            ModuleNotFoundError("id_inexistente"),
            PathUnavailableError("caminho_x"),
        ]
        for error in errors:
            with pytest.raises(TrainingError):
                raise error


class TestValidationError:
    """Testes específicos para ValidationError com lista de erros."""

    def test_validation_error_stores_errors_list(self):
        errors = ["campo obrigatório", "valor inválido"]
        exc = ValidationError(errors)
        assert exc.errors == errors

    def test_validation_error_message_contains_all_errors(self):
        errors = ["erro1", "erro2", "erro3"]
        exc = ValidationError(errors)
        assert "erro1" in str(exc)
        assert "erro2" in str(exc)
        assert "erro3" in str(exc)

    def test_validation_error_message_format(self):
        errors = ["ramificação sem caminhos", "etapa sem conteúdo"]
        exc = ValidationError(errors)
        expected = "Validação falhou: ramificação sem caminhos, etapa sem conteúdo"
        assert str(exc) == expected

    def test_validation_error_single_error(self):
        exc = ValidationError(["único erro"])
        assert exc.errors == ["único erro"]
        assert "único erro" in str(exc)

    def test_validation_error_empty_list(self):
        exc = ValidationError([])
        assert exc.errors == []


# ============================================================
# Testes do Utilitário retry_with_backoff
# ============================================================


class TestRetryWithBackoff:
    """Testes para a função retry_with_backoff."""

    @patch("managers.utils.time.sleep")
    def test_success_on_first_attempt(self, mock_sleep):
        """Operação bem-sucedida na primeira tentativa não faz sleep."""
        success, result = retry_with_backoff(lambda: 42)
        assert success is True
        assert result == 42
        mock_sleep.assert_not_called()

    @patch("managers.utils.time.sleep")
    def test_success_after_one_failure(self, mock_sleep):
        """Operação que falha uma vez e depois sucede."""
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise RuntimeError("falha temporária")
            return "recuperado"

        success, result = retry_with_backoff(operation, max_retries=3, interval_seconds=5)
        assert success is True
        assert result == "recuperado"
        assert attempts["count"] == 2
        mock_sleep.assert_called_once_with(5)

    @patch("managers.utils.time.sleep")
    def test_failure_after_all_retries(self, mock_sleep):
        """Operação que falha em todas as tentativas."""
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            raise RuntimeError("falha persistente")

        success, result = retry_with_backoff(operation, max_retries=3, interval_seconds=5)
        assert success is False
        assert result is None
        assert attempts["count"] == 3
        # Sleep é chamado entre tentativas (2 vezes para 3 tentativas)
        assert mock_sleep.call_count == 2

    @patch("managers.utils.time.sleep")
    def test_default_parameters(self, mock_sleep):
        """Verifica parâmetros padrão: 3 tentativas, 5s intervalo."""
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            raise ValueError("erro")

        success, result = retry_with_backoff(operation)
        assert success is False
        assert result is None
        assert attempts["count"] == 3
        # Deve ter dormido 5 segundos entre cada tentativa
        mock_sleep.assert_any_call(5)
        assert mock_sleep.call_count == 2

    @patch("managers.utils.time.sleep")
    def test_custom_max_retries(self, mock_sleep):
        """Respeita max_retries customizado."""
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            raise RuntimeError("erro")

        success, result = retry_with_backoff(operation, max_retries=5, interval_seconds=1)
        assert success is False
        assert attempts["count"] == 5
        assert mock_sleep.call_count == 4

    @patch("managers.utils.time.sleep")
    def test_custom_interval(self, mock_sleep):
        """Respeita interval_seconds customizado."""

        def operation():
            raise RuntimeError("erro")

        retry_with_backoff(operation, max_retries=2, interval_seconds=10)
        mock_sleep.assert_called_with(10)

    @patch("managers.utils.time.sleep")
    def test_success_on_last_attempt(self, mock_sleep):
        """Sucesso na última tentativa possível."""
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("ainda não")
            return "finalmente"

        success, result = retry_with_backoff(operation, max_retries=3, interval_seconds=5)
        assert success is True
        assert result == "finalmente"
        assert attempts["count"] == 3
        assert mock_sleep.call_count == 2

    @patch("managers.utils.time.sleep")
    def test_returns_none_value_on_success(self, mock_sleep):
        """Operação que retorna None é distinguida de falha."""
        success, result = retry_with_backoff(lambda: None)
        assert success is True
        assert result is None

    @patch("managers.utils.time.sleep")
    def test_single_retry(self, mock_sleep):
        """max_retries=1 executa apenas uma vez, sem sleep."""

        def operation():
            raise RuntimeError("erro")

        success, result = retry_with_backoff(operation, max_retries=1, interval_seconds=5)
        assert success is False
        assert result is None
        mock_sleep.assert_not_called()
