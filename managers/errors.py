"""Hierarquia de erros do Sistema de Treinamento.

Define exceções customizadas para tratamento estruturado de erros:
- TrainingError: erro base do sistema
- ProgressSaveError: falha ao salvar progresso (retry automático)
- ContentLoadError: falha ao carregar conteúdo/mídia
- ValidationError: erro de validação de dados
- ModuleNotFoundError: módulo não encontrado
- PathUnavailableError: caminho de ramificação indisponível
- ValidationResult: resultado estruturado de validação

Requirements: 5.5, 7.4, 7.5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


class TrainingError(Exception):
    """Erro base do sistema de treinamento.

    Todas as exceções específicas do sistema herdam desta classe,
    permitindo captura genérica quando necessário.
    """

    pass


class ProgressSaveError(TrainingError):
    """Falha ao salvar progresso do usuário.

    Levantada quando o sistema não consegue registrar o progresso
    após todas as tentativas de retry (3 tentativas, intervalo de 5s).

    Requirements: 5.5
    """

    pass


class ContentLoadError(TrainingError):
    """Falha ao carregar conteúdo (mídia, etapa).

    Levantada quando uma imagem, vídeo ou outro conteúdo multimídia
    não pode ser carregado após timeout (10s) ou falhas consecutivas.

    Requirements: 7.4, 7.5
    """

    pass


class ValidationError(TrainingError):
    """Erro de validação de dados (módulo, ramificação).

    Contém a lista de erros encontrados durante a validação,
    permitindo exibir todos os problemas de uma vez ao administrador.

    Attributes:
        errors: Lista de mensagens descrevendo cada violação encontrada.

    Requirements: 6.3, 6.5
    """

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validação falhou: {', '.join(errors)}")


class ModuleNotFoundError(TrainingError):
    """Módulo não encontrado.

    Levantada quando se tenta acessar um módulo com ID inexistente
    ou que foi excluído.
    """

    pass


class PathUnavailableError(TrainingError):
    """Caminho de ramificação indisponível.

    Levantada quando o usuário seleciona um caminho que não possui
    conteúdo ou está indisponível. O usuário deve permanecer no
    ponto de ramificação atual.

    Requirements: 3.6
    """

    pass


@dataclass
class ValidationResult:
    """Resultado de uma validação de ramificação ou módulo.

    Attributes:
        is_valid: Se a validação passou sem erros.
        errors: Lista de mensagens de erro encontradas.
    """

    is_valid: bool
    errors: List[str] = field(default_factory=list)
