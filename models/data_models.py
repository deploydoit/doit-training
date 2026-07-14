"""Modelos de dados para o Sistema de Treinamento.

Define todas as dataclasses que representam as entidades do sistema:
- Module: módulo de treinamento
- Step: etapa dentro de um módulo
- StepContent: conteúdo multimídia de uma etapa
- Branch: ponto de ramificação
- BranchOption: opção dentro de uma ramificação
- Path: caminho (sequência de etapas)
- UserProgress: progresso do usuário em um módulo
- UserProfile: perfil do usuário
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import ContentType, ModuleStatus, ProgressStatus, StepType


@dataclass
class Module:
    """Módulo de treinamento que agrupa etapas relacionadas a um tema."""

    id: str
    title: str
    description: str  # Máximo 150 caracteres
    status: ModuleStatus
    created_at: datetime
    updated_at: datetime
    version: int = 1


@dataclass
class StepContent:
    """Conteúdo multimídia de uma etapa."""

    id: str
    step_id: str
    content_type: ContentType
    content_data: str  # Texto, URL da imagem, URL do vídeo, URL do link
    alt_text: Optional[str]  # Texto alternativo para acessibilidade
    order: int  # Ordem de exibição no passo


@dataclass
class Step:
    """Etapa (tela individual) dentro de um módulo."""

    id: str
    module_id: str
    path_id: Optional[str]  # None se está no caminho principal
    position: int  # Posição sequencial no caminho
    step_type: StepType
    content: list[StepContent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BranchOption:
    """Opção dentro de uma ramificação."""

    id: str
    branch_id: str
    label: str  # Rótulo descritivo (3-80 caracteres para admin, até 150 para exibição)
    path_id: str  # ID do caminho de destino
    position: int  # Ordem de exibição


@dataclass
class Branch:
    """Ponto de ramificação onde o usuário escolhe entre caminhos."""

    id: str
    step_id: str  # Etapa onde a ramificação aparece
    options: list[BranchOption] = field(default_factory=list)


@dataclass
class Path:
    """Caminho (sequência de etapas) dentro de um módulo."""

    id: str
    module_id: str
    parent_branch_id: Optional[str]  # Ramificação que originou este caminho
    name: str
    steps: list[Step] = field(default_factory=list)


@dataclass
class UserProgress:
    """Progresso do usuário em um módulo."""

    id: str
    user_id: str
    module_id: str
    current_step_id: str
    current_path_id: Optional[str]
    completed_steps: list[str] = field(default_factory=list)  # IDs das etapas concluídas
    explored_paths: list[str] = field(default_factory=list)  # IDs dos caminhos explorados
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    percentage: float = 0.0
    last_accessed: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserProfile:
    """Perfil do usuário no sistema de treinamento."""

    id: str
    name: str
    email: str
    is_first_visit: bool = True
    is_admin: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_login: datetime = field(default_factory=datetime.now)
