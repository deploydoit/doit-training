"""Enums para o Sistema de Treinamento.

Define os tipos enumerados utilizados nos modelos de dados:
- ModuleStatus: estados de publicação de um módulo
- StepType: tipos de etapa (conteúdo ou ramificação)
- ContentType: tipos de conteúdo multimídia
- ProgressStatus: estados de progresso do usuário
"""

from enum import Enum


class ModuleStatus(Enum):
    """Status de publicação de um módulo de treinamento."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StepType(Enum):
    """Tipo de etapa dentro de um módulo."""

    CONTENT = "content"  # Etapa com conteúdo regular
    BRANCH = "branch"  # Etapa com ramificação


class ContentType(Enum):
    """Tipo de conteúdo multimídia em uma etapa."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"


class ProgressStatus(Enum):
    """Status de progresso do usuário em um módulo."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
