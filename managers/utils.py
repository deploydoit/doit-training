"""Utilitários do Sistema de Treinamento.

Funções auxiliares compartilhadas entre os managers:
- retry_with_backoff: executa operação com retentativas automáticas

Requirements: 5.5, 7.4, 7.5
"""

import time
from typing import Callable, Optional, Tuple, TypeVar

T = TypeVar("T")


def retry_with_backoff(
    operation: Callable[[], T],
    max_retries: int = 3,
    interval_seconds: int = 5,
) -> Tuple[bool, Optional[T]]:
    """Executa operação com retentativas automáticas.

    Tenta executar a operação até `max_retries` vezes. Em caso de falha,
    aguarda `interval_seconds` entre tentativas. Retorna uma tupla indicando
    sucesso e o resultado da operação.

    Args:
        operation: Função sem argumentos que será executada.
        max_retries: Número máximo de tentativas (padrão: 3).
        interval_seconds: Intervalo em segundos entre tentativas (padrão: 5).

    Returns:
        Tupla (sucesso, resultado):
        - (True, resultado) se a operação foi bem-sucedida em alguma tentativa.
        - (False, None) se todas as tentativas falharam.

    Examples:
        >>> success, result = retry_with_backoff(lambda: save_to_db(data))
        >>> if not success:
        ...     notify_user("Falha ao salvar progresso")

    Requirements: 5.5, 7.4, 7.5
    """
    for attempt in range(max_retries):
        try:
            result = operation()
            return True, result
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(interval_seconds)
    return False, None
