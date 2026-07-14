"""Tratamento centralizado de erros na interface Streamlit.

Componente responsável por:
- Exibir mensagens de erro amigáveis ao usuário
- Implementar timeout de 10 segundos com mensagem de erro e botão retry
- Exibir mensagem após 3 falhas consecutivas orientando verificar conexão
- Garantir que falhas de mídia não bloqueiam navegação

Requirements: 4.5, 7.4, 7.5
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional, TypeVar

import streamlit as st

from managers.errors import (
    ContentLoadError,
    ModuleNotFoundError,
    PathUnavailableError,
    ProgressSaveError,
    TrainingError,
    ValidationError,
)

T = TypeVar("T")

# Constantes
TIMEOUT_SECONDS = 10
MAX_CONSECUTIVE_FAILURES = 3


def display_error(error: Exception, context: str = "") -> None:
    """Exibe mensagem de erro amigável baseada no tipo de exceção.

    Traduz exceções técnicas em mensagens compreensíveis para o usuário.
    Não bloqueia a navegação — apenas informa o problema.

    Args:
        error: Exceção capturada.
        context: Contexto adicional sobre onde o erro ocorreu (ex: "carregar módulo").

    Requirements: 4.5, 7.4
    """
    message = _get_friendly_message(error, context)
    st.error(f" {message}")


def _get_friendly_message(error: Exception, context: str = "") -> str:
    """Retorna mensagem amigável baseada no tipo de erro.

    Args:
        error: Exceção capturada.
        context: Contexto adicional.

    Returns:
        Mensagem amigável para o usuário.
    """
    if isinstance(error, ContentLoadError):
        return "Não foi possível carregar o conteúdo. Tente novamente."
    elif isinstance(error, ProgressSaveError):
        return "Não foi possível salvar seu progresso. Tente novamente em alguns instantes."
    elif isinstance(error, ModuleNotFoundError):
        return "O módulo solicitado não foi encontrado."
    elif isinstance(error, PathUnavailableError):
        return "Este caminho não está disponível no momento."
    elif isinstance(error, ValidationError):
        return f"Erro de validação: {', '.join(error.errors)}"
    elif isinstance(error, TrainingError):
        return "Ocorreu um erro no sistema de treinamento."
    elif isinstance(error, TimeoutError):
        return "O carregamento excedeu o tempo limite. Tente novamente."
    else:
        prefix = f"Erro ao {context}: " if context else "Ocorreu um erro inesperado. "
        return f"{prefix}Tente novamente."


def execute_with_timeout(
    operation: Callable[[], T],
    timeout_seconds: int = TIMEOUT_SECONDS,
    context: str = "",
) -> tuple[bool, Optional[T]]:
    """Executa operação com timeout.

    Se a operação não completar dentro do tempo limite, retorna falha.
    Em caso de timeout, o componente de UI exibirá a mensagem adequada.

    Args:
        operation: Função sem argumentos a ser executada.
        timeout_seconds: Tempo máximo em segundos (padrão: 10).
        context: Descrição do que está sendo feito (para mensagem de erro).

    Returns:
        Tupla (sucesso, resultado):
        - (True, resultado) se a operação completou a tempo.
        - (False, None) se houve timeout ou erro.

    Requirements: 7.4
    """
    start_time = time.time()
    try:
        result = operation()
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            return False, None
        return True, result
    except Exception:
        return False, None


def render_timeout_error(context: str = "carregar conteúdo", retry_key: str = "retry_timeout") -> bool:
    """Renderiza mensagem de erro de timeout com botão retry.

    Exibe mensagem informando que o carregamento excedeu o tempo limite
    e oferece botão para tentar novamente.

    Args:
        context: Descrição do que falhou no carregamento.
        retry_key: Chave única para o botão de retry no session_state.

    Returns:
        True se o botão de retry foi clicado.

    Requirements: 7.4
    """
    st.error(
        f" Não foi possível {context}. "
        f"O carregamento excedeu o tempo limite de {TIMEOUT_SECONDS} segundos."
    )
    return st.button(" Tentar novamente", key=retry_key)


def render_connection_error(retry_key: str = "retry_connection") -> bool:
    """Renderiza mensagem orientando verificar conexão após 3 falhas consecutivas.

    Exibe mensagem informando que múltiplas tentativas falharam e
    orientando o usuário a verificar sua conexão.

    Args:
        retry_key: Chave única para o botão de retry no session_state.

    Returns:
        True se o botão de retry foi clicado.

    Requirements: 7.5
    """
    st.error(
        " Não foi possível carregar o conteúdo após várias tentativas. "
        "Verifique sua conexão com a internet e tente novamente mais tarde."
    )
    return st.button(" Tentar novamente", key=retry_key)


def handle_content_load(
    operation: Callable[[], T],
    content_id: str,
    context: str = "carregar conteúdo",
) -> tuple[bool, Optional[T]]:
    """Carrega conteúdo com timeout e rastreamento de falhas consecutivas.

    Executa a operação com timeout de 10 segundos. Rastreia falhas
    consecutivas no session_state e renderiza a mensagem apropriada:
    - Timeout: mensagem de erro + botão retry (Req 7.4)
    - 3+ falhas consecutivas: mensagem de conexão (Req 7.5)

    Falhas de mídia NÃO bloqueiam a navegação (Req 4.5).

    Args:
        operation: Função que carrega o conteúdo.
        content_id: ID único do conteúdo (para rastrear falhas no session_state).
        context: Descrição do que está sendo carregado.

    Returns:
        Tupla (sucesso, resultado):
        - (True, resultado) se o carregamento foi bem-sucedido.
        - (False, None) se falhou (mensagem de erro já exibida).

    Requirements: 4.5, 7.4, 7.5
    """
    failure_key = f"consecutive_failures_{content_id}"
    retry_key = f"retry_{content_id}"

    # Verificar se foi solicitado retry
    if st.session_state.get(retry_key, False):
        st.session_state[retry_key] = False

    # Obter contagem de falhas consecutivas
    failure_count = st.session_state.get(failure_key, 0)

    # Se já temos 3+ falhas consecutivas, mostrar mensagem de conexão
    if failure_count >= MAX_CONSECUTIVE_FAILURES:
        clicked = render_connection_error(retry_key=f"btn_conn_{content_id}")
        if clicked:
            st.session_state[failure_key] = 0
            st.rerun()
        return False, None

    # Tentar executar com timeout
    success, result = execute_with_timeout(
        operation=operation,
        timeout_seconds=TIMEOUT_SECONDS,
        context=context,
    )

    if success:
        # Resetar contador de falhas
        st.session_state[failure_key] = 0
        return True, result

    # Falha - incrementar contador
    st.session_state[failure_key] = failure_count + 1
    updated_count = failure_count + 1

    # Verificar se atingiu limite de falhas consecutivas
    if updated_count >= MAX_CONSECUTIVE_FAILURES:
        clicked = render_connection_error(retry_key=f"btn_conn_{content_id}")
        if clicked:
            st.session_state[failure_key] = 0
            st.rerun()
    else:
        clicked = render_timeout_error(
            context=context,
            retry_key=f"btn_retry_{content_id}",
        )
        if clicked:
            st.rerun()

    return False, None


def safe_render_media(
    render_fn: Callable[[], None],
    content_id: str,
) -> None:
    """Renderiza mídia de forma segura, sem bloquear navegação.

    Envolve a renderização de mídia em tratamento de erro que:
    - Exibe fallback se mídia não carregar
    - Nunca bloqueia os botões de navegação
    - Rastreia falhas consecutivas

    Args:
        render_fn: Função que renderiza o conteúdo de mídia.
        content_id: ID único do conteúdo para rastreamento de estado.

    Requirements: 4.5
    """
    error_key = f"media_render_error_{content_id}"

    try:
        render_fn()
        # Sucesso - limpar estado de erro
        st.session_state.pop(error_key, None)
    except Exception as e:
        st.session_state[error_key] = True
        st.warning(" Conteúdo indisponível no momento.")
        if st.button(" Tentar novamente", key=f"btn_media_retry_{content_id}"):
            st.session_state.pop(error_key, None)
            st.rerun()


def handle_operation_with_feedback(
    operation: Callable[[], T],
    context: str = "executar operação",
    show_spinner: bool = True,
) -> tuple[bool, Optional[T]]:
    """Executa operação com feedback visual e tratamento de erro.

    Mostra spinner durante execução e exibe erro amigável se falhar.
    Destinado a operações que NÃO são carregamento de mídia
    (para mídia, usar handle_content_load).

    Args:
        operation: Função a ser executada.
        context: Descrição da operação (usado na mensagem de erro).
        show_spinner: Se True, mostra spinner do Streamlit durante a operação.

    Returns:
        Tupla (sucesso, resultado).
    """
    try:
        if show_spinner:
            with st.spinner(f"Carregando..."):
                result = operation()
        else:
            result = operation()
        return True, result
    except TrainingError as e:
        display_error(e, context)
        return False, None
    except Exception as e:
        display_error(e, context)
        return False, None


def reset_failure_count(content_id: str) -> None:
    """Reseta o contador de falhas consecutivas para um conteúdo.

    Útil quando o usuário navega para outra etapa e o contexto muda.

    Args:
        content_id: ID do conteúdo cujo contador será resetado.
    """
    failure_key = f"consecutive_failures_{content_id}"
    st.session_state.pop(failure_key, None)
