"""Gerenciador de Ramificações do Sistema de Treinamento.

Controla a lógica de ramificações e caminhos, incluindo:
- Obtenção de opções de ramificação para uma etapa
- Seleção de caminho e navegação para primeira etapa
- Rastreamento de caminhos explorados pelo usuário
- Retorno ao ponto de ramificação original
- Validação de ramificações (2-5 opções, labels 3-80 caracteres)

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from models.data_models import BranchOption, Step, StepContent
from models.database import Database
from models.enums import ContentType, StepType

from .errors import PathUnavailableError, ValidationResult


class BranchManager:
    """Gerenciador de ramificações e caminhos.

    Responsável por toda a lógica relacionada a pontos de decisão
    (branches) dentro de um módulo de treinamento.

    Attributes:
        db: Instância do banco de dados.
    """

    def __init__(self, db: Database):
        """Inicializa o BranchManager.

        Args:
            db: Instância do banco de dados SQLite.
        """
        self.db = db

    def get_branch_options(self, step_id: str) -> List[BranchOption]:
        """Retorna opções de ramificação para uma etapa.

        Busca a ramificação associada à etapa e retorna todas as
        opções disponíveis, ordenadas por posição.

        Args:
            step_id: ID da etapa que contém a ramificação.

        Returns:
            Lista de BranchOption ordenada por posição.
            Lista vazia se a etapa não tem ramificação.

        Requirements: 3.1
        """
        # Buscar branch para o step_id
        cursor = self.db.execute(
            "SELECT id FROM branches WHERE step_id = ?", (step_id,)
        )
        branch_row = cursor.fetchone()

        if branch_row is None:
            return []

        branch_id = branch_row["id"]

        # Buscar opções ordenadas por posição
        cursor = self.db.execute(
            "SELECT id, branch_id, label, path_id, position "
            "FROM branch_options WHERE branch_id = ? ORDER BY position",
            (branch_id,),
        )

        options = []
        for row in cursor.fetchall():
            options.append(
                BranchOption(
                    id=row["id"],
                    branch_id=row["branch_id"],
                    label=row["label"],
                    path_id=row["path_id"],
                    position=row["position"],
                )
            )

        return options

    def select_branch(self, user_id: str, step_id: str, option_id: str) -> Step:
        """Registra escolha do usuário e retorna primeira etapa do caminho.

        Quando o usuário seleciona uma opção de ramificação:
        1. Identifica o caminho de destino
        2. Registra o caminho como explorado
        3. Retorna a primeira etapa (position=0) do caminho escolhido

        Args:
            user_id: ID do usuário que fez a escolha.
            step_id: ID da etapa onde a ramificação está.
            option_id: ID da opção escolhida pelo usuário.

        Returns:
            Step: Primeira etapa do caminho escolhido.

        Raises:
            PathUnavailableError: Se o caminho não tem etapas ou não existe.

        Requirements: 3.2, 3.6
        """
        # Buscar a opção selecionada
        cursor = self.db.execute(
            "SELECT bo.path_id, bo.branch_id "
            "FROM branch_options bo WHERE bo.id = ?",
            (option_id,),
        )
        option_row = cursor.fetchone()

        if option_row is None:
            raise PathUnavailableError(
                f"Opção de ramificação '{option_id}' não encontrada."
            )

        path_id = option_row["path_id"]
        branch_id = option_row["branch_id"]

        # Verificar se o caminho tem etapas
        cursor = self.db.execute(
            "SELECT id, module_id, path_id, position, step_type, created_at "
            "FROM steps WHERE path_id = ? ORDER BY position LIMIT 1",
            (path_id,),
        )
        first_step_row = cursor.fetchone()

        if first_step_row is None:
            raise PathUnavailableError(
                "O caminho selecionado não possui conteúdo disponível."
            )

        # Registrar caminho como explorado (INSERT OR IGNORE para idempotência)
        self.db.execute(
            "INSERT OR IGNORE INTO explored_paths (user_id, path_id, branch_id, explored_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, path_id, branch_id, datetime.now().isoformat()),
        )
        self.db.commit()

        # Construir o Step com conteúdo
        step = self._build_step_from_row(first_step_row)
        return step

    def get_explored_paths(self, user_id: str, step_id: str) -> List[str]:
        """Retorna IDs dos caminhos já explorados pelo usuário em um branch.

        Busca na tabela explored_paths todos os caminhos que o usuário
        já visitou a partir da ramificação associada à etapa fornecida.

        Args:
            user_id: ID do usuário.
            step_id: ID da etapa que contém a ramificação.

        Returns:
            Lista de path_ids explorados pelo usuário.
            Lista vazia se nenhum caminho foi explorado.

        Requirements: 3.4, 3.5
        """
        # Buscar branch associado ao step
        cursor = self.db.execute(
            "SELECT id FROM branches WHERE step_id = ?", (step_id,)
        )
        branch_row = cursor.fetchone()

        if branch_row is None:
            return []

        branch_id = branch_row["id"]

        # Buscar caminhos explorados pelo usuário neste branch
        cursor = self.db.execute(
            "SELECT path_id FROM explored_paths "
            "WHERE user_id = ? AND branch_id = ?",
            (user_id, branch_id),
        )

        return [row["path_id"] for row in cursor.fetchall()]

    def get_return_point(self, user_id: str, path_id: str) -> Step:
        """Retorna a etapa do ponto de ramificação original.

        Dado um caminho de ramificação, encontra a etapa onde a
        ramificação foi apresentada ao usuário, permitindo retornar
        para explorar outras opções.

        Args:
            user_id: ID do usuário.
            path_id: ID do caminho atual do usuário.

        Returns:
            Step: A etapa que contém a ramificação original.

        Raises:
            PathUnavailableError: Se o caminho não pertence a uma ramificação
                ou se a etapa de origem não é encontrada.

        Requirements: 3.4
        """
        # Buscar o parent_branch_id do caminho
        cursor = self.db.execute(
            "SELECT parent_branch_id FROM paths WHERE id = ?", (path_id,)
        )
        path_row = cursor.fetchone()

        if path_row is None:
            raise PathUnavailableError(
                f"Caminho '{path_id}' não encontrado."
            )

        parent_branch_id = path_row["parent_branch_id"]

        if parent_branch_id is None:
            raise PathUnavailableError(
                f"O caminho '{path_id}' não pertence a uma ramificação. "
                "Não há ponto de retorno disponível."
            )

        # Buscar a etapa onde a ramificação está
        cursor = self.db.execute(
            "SELECT s.id, s.module_id, s.path_id, s.position, s.step_type, s.created_at "
            "FROM branches b "
            "JOIN steps s ON b.step_id = s.id "
            "WHERE b.id = ?",
            (parent_branch_id,),
        )
        step_row = cursor.fetchone()

        if step_row is None:
            raise PathUnavailableError(
                "Etapa de ramificação original não encontrada."
            )

        return self._build_step_from_row(step_row)

    def validate_branch(self, step_id: str) -> ValidationResult:
        """Valida que uma ramificação atende os critérios.

        Critérios de validação:
        - A ramificação deve ter entre 2 e 5 opções
        - Cada label de opção deve ter entre 3 e 80 caracteres

        Args:
            step_id: ID da etapa que contém a ramificação.

        Returns:
            ValidationResult com is_valid e lista de errors.

        Requirements: 3.3, 6.3
        """
        errors: List[str] = []

        # Buscar branch
        cursor = self.db.execute(
            "SELECT id FROM branches WHERE step_id = ?", (step_id,)
        )
        branch_row = cursor.fetchone()

        if branch_row is None:
            errors.append(
                f"Etapa '{step_id}' não contém uma ramificação."
            )
            return ValidationResult(is_valid=False, errors=errors)

        branch_id = branch_row["id"]

        # Buscar opções
        cursor = self.db.execute(
            "SELECT id, label, position FROM branch_options WHERE branch_id = ? ORDER BY position",
            (branch_id,),
        )
        options = cursor.fetchall()
        num_options = len(options)

        # Validar quantidade de opções (2-5)
        if num_options < 2:
            errors.append(
                f"Ramificação deve ter no mínimo 2 opções, mas tem {num_options}."
            )
        elif num_options > 5:
            errors.append(
                f"Ramificação deve ter no máximo 5 opções, mas tem {num_options}."
            )

        # Validar labels (3-80 caracteres para admin)
        for option in options:
            label = option["label"]
            label_len = len(label)
            if label_len < 3:
                errors.append(
                    f"Opção '{option['id']}': rótulo deve ter no mínimo 3 caracteres "
                    f"(tem {label_len})."
                )
            elif label_len > 80:
                errors.append(
                    f"Opção '{option['id']}': rótulo deve ter no máximo 80 caracteres "
                    f"(tem {label_len})."
                )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _build_step_from_row(self, row) -> Step:
        """Constrói um objeto Step a partir de uma row do banco de dados.

        Args:
            row: sqlite3.Row com colunas do step.

        Returns:
            Step com conteúdo carregado.
        """
        step_id = row["id"]

        # Carregar conteúdo da etapa
        cursor = self.db.execute(
            "SELECT id, step_id, content_type, content_data, alt_text, display_order "
            "FROM step_contents WHERE step_id = ? ORDER BY display_order",
            (step_id,),
        )

        contents = []
        for content_row in cursor.fetchall():
            contents.append(
                StepContent(
                    id=content_row["id"],
                    step_id=content_row["step_id"],
                    content_type=ContentType(content_row["content_type"]),
                    content_data=content_row["content_data"],
                    alt_text=content_row["alt_text"],
                    order=content_row["display_order"],
                )
            )

        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return Step(
            id=step_id,
            module_id=row["module_id"],
            path_id=row["path_id"],
            position=row["position"],
            step_type=StepType(row["step_type"]),
            content=contents,
            created_at=created_at,
        )
