"""Testes para o tratamento centralizado de erros na interface.

Testa:
- Mensagens amigáveis por tipo de erro
- Timeout de 10 segundos com mensagem de erro
- Rastreamento de falhas consecutivas
- Mensagem após 3 falhas consecutivas orientando verificar conexão
- Garantia de que falhas de mídia não bloqueiam navegação

Requirements: 4.5, 7.4, 7.5
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from managers.errors import (
    ContentLoadError,
    ModuleNotFoundError,
    PathUnavailableError,
    ProgressSaveError,
    TrainingError,
    ValidationError,
)
from pages.error_handler import (
    MAX_CONSECUTIVE_FAILURES,
    TIMEOUT_SECONDS,
    _get_friendly_message,
    execute_with_timeout,
    handle_content_load,
    reset_failure_count,
)


# ============================================================
# Testes para _get_friendly_message
# ============================================================


class TestFriendlyMessages:
    """Verifica que mensagens amigáveis são retornadas para cada tipo de erro."""

    def test_content_load_error_message(self):
        error = ContentLoadError("timeout na imagem")
        message = _get_friendly_message(error)
        assert "carregar o conteúdo" in message
        assert "Tente novamente" in message

    def test_progress_save_error_message(self):
        error = ProgressSaveError("falha no banco")
        message = _get_friendly_message(error)
        assert "salvar seu progresso" in message

    def test_module_not_found_error_message(self):
        error = ModuleNotFoundError("id_xyz")
        message = _get_friendly_message(error)
        assert "não foi encontrado" in message

    def test_path_unavailable_error_message(self):
        error = PathUnavailableError("caminho_x")
        message = _get_friendly_message(error)
        assert "não está disponível" in message

    def test_validation_error_message(self):
        error = ValidationError(["campo vazio", "limite excedido"])
        message = _get_friendly_message(error)
        assert "campo vazio" in message
        assert "limite excedido" in message

    def test_generic_training_error_message(self):
        error = TrainingError("algo genérico")
        message = _get_friendly_message(error)
        assert "sistema de treinamento" in message

    def test_timeout_error_message(self):
        error = TimeoutError("expirou")
        message = _get_friendly_message(error)
        assert "tempo limite" in message

    def test_unknown_error_with_context(self):
        error = RuntimeError("algo inesperado")
        message = _get_friendly_message(error, context="carregar módulo")
        assert "carregar módulo" in message

    def test_unknown_error_without_context(self):
        error = RuntimeError("algo inesperado")
        message = _get_friendly_message(error)
        assert "erro inesperado" in message


# ============================================================
# Testes para execute_with_timeout
# ============================================================


class TestExecuteWithTimeout:
    """Testa execução de operações com timeout de 10 segundos."""

    def test_successful_operation_within_timeout(self):
        """Operação rápida retorna sucesso."""
        success, result = execute_with_timeout(lambda: "dados", timeout_seconds=10)
        assert success is True
        assert result == "dados"

    def test_operation_returning_none_is_success(self):
        """Operação que retorna None é diferente de falha."""
        success, result = execute_with_timeout(lambda: None, timeout_seconds=10)
        assert success is True
        assert result is None

    def test_operation_raising_exception_is_failure(self):
        """Operação que levanta exceção retorna falha."""

        def failing_op():
            raise ContentLoadError("falhou")

        success, result = execute_with_timeout(failing_op, timeout_seconds=10)
        assert success is False
        assert result is None

    @patch("pages.error_handler.time.time")
    def test_operation_exceeding_timeout_is_failure(self, mock_time):
        """Operação que excede o timeout retorna falha."""
        # Simula time: primeira chamada retorna 0, segunda retorna 11 (excede 10s)
        mock_time.side_effect = [0.0, 11.0]

        success, result = execute_with_timeout(lambda: "dados", timeout_seconds=10)
        assert success is False
        assert result is None

    @patch("pages.error_handler.time.time")
    def test_operation_exactly_at_timeout_is_success(self, mock_time):
        """Operação que completa exatamente no limite do timeout é sucesso."""
        mock_time.side_effect = [0.0, 10.0]

        success, result = execute_with_timeout(lambda: "ok", timeout_seconds=10)
        assert success is True
        assert result == "ok"

    def test_default_timeout_is_10_seconds(self):
        """Verifica que o timeout padrão é 10 segundos."""
        assert TIMEOUT_SECONDS == 10


# ============================================================
# Testes para handle_content_load (com mock do Streamlit)
# ============================================================


class TestHandleContentLoad:
    """Testa carregamento de conteúdo com timeout e falhas consecutivas."""

    @patch("pages.error_handler.st")
    def test_successful_load_resets_failure_count(self, mock_st):
        """Carregamento bem-sucedido reseta contador de falhas."""
        mock_st.session_state = {}

        success, result = handle_content_load(
            operation=lambda: "conteúdo",
            content_id="img_001",
            context="carregar imagem",
        )

        assert success is True
        assert result == "conteúdo"
        assert mock_st.session_state.get("consecutive_failures_img_001", 0) == 0

    @patch("pages.error_handler.st")
    def test_failure_increments_counter(self, mock_st):
        """Falha incrementa o contador de falhas consecutivas."""
        mock_st.session_state = {}
        mock_st.button = MagicMock(return_value=False)
        mock_st.error = MagicMock()

        def failing_op():
            raise ContentLoadError("timeout")

        success, result = handle_content_load(
            operation=failing_op,
            content_id="img_002",
            context="carregar imagem",
        )

        assert success is False
        assert result is None
        assert mock_st.session_state["consecutive_failures_img_002"] == 1

    @patch("pages.error_handler.st")
    def test_three_failures_shows_connection_message(self, mock_st):
        """Após 3 falhas consecutivas, exibe mensagem de conexão."""
        mock_st.session_state = {"consecutive_failures_vid_001": 2}
        mock_st.button = MagicMock(return_value=False)
        mock_st.error = MagicMock()

        def failing_op():
            raise ContentLoadError("timeout")

        success, result = handle_content_load(
            operation=failing_op,
            content_id="vid_001",
            context="carregar vídeo",
        )

        assert success is False
        # Verifica que st.error foi chamado com mensagem de conexão
        mock_st.error.assert_called()
        error_msg = mock_st.error.call_args[0][0]
        assert "conexão" in error_msg.lower() or "Verifique" in error_msg

    @patch("pages.error_handler.st")
    def test_already_at_max_failures_shows_connection_message(self, mock_st):
        """Se já está no limite de falhas, mostra mensagem de conexão diretamente."""
        mock_st.session_state = {"consecutive_failures_content_x": 3}
        mock_st.button = MagicMock(return_value=False)
        mock_st.error = MagicMock()

        success, result = handle_content_load(
            operation=lambda: "dados",
            content_id="content_x",
            context="carregar conteúdo",
        )

        assert success is False
        mock_st.error.assert_called()
        error_msg = mock_st.error.call_args[0][0]
        assert "Verifique" in error_msg or "conexão" in error_msg.lower()

    @patch("pages.error_handler.st")
    def test_navigation_not_blocked_on_media_failure(self, mock_st):
        """Falha de mídia NÃO bloqueia - função retorna sem exceção."""
        mock_st.session_state = {}
        mock_st.button = MagicMock(return_value=False)
        mock_st.error = MagicMock()

        def failing_media():
            raise ContentLoadError("imagem não encontrada")

        # Deve retornar normalmente (sem levantar exceção)
        success, result = handle_content_load(
            operation=failing_media,
            content_id="img_broken",
            context="carregar imagem",
        )

        assert success is False
        assert result is None
        # Não levanta exceção — navegação permanece funcional

    def test_max_consecutive_failures_is_three(self):
        """Verifica que o limite de falhas consecutivas é 3."""
        assert MAX_CONSECUTIVE_FAILURES == 3


# ============================================================
# Testes para reset_failure_count
# ============================================================


class TestResetFailureCount:
    """Testa reset do contador de falhas."""

    @patch("pages.error_handler.st")
    def test_reset_clears_failure_key(self, mock_st):
        """Reset remove a chave de falhas do session_state."""
        mock_st.session_state = {"consecutive_failures_img_001": 3}
        reset_failure_count("img_001")
        assert "consecutive_failures_img_001" not in mock_st.session_state

    @patch("pages.error_handler.st")
    def test_reset_nonexistent_key_is_safe(self, mock_st):
        """Reset de chave inexistente não levanta erro."""
        mock_st.session_state = {}
        # Não deve levantar exceção
        reset_failure_count("nonexistent")
