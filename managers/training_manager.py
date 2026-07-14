"""Gerenciador de Treinamento do Sistema de Treinamento.

Responsável pela lógica de navegação entre etapas e módulos, incluindo:
- Listagem de módulos com status de progresso do usuário
- Obtenção de etapas por ID
- Navegação sequencial (próximo/anterior)
- Verificação de posição (primeira/última etapa)
- Conclusão de módulo

Requirements: 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from models.data_models import Step, StepContent
from models.database import Database
from models.enums import ContentType, ModuleStatus, ProgressStatus, StepType

from .branch_manager import BranchManager
from .errors import ModuleNotFoundError
from .progress_manager import ProgressManager


@dataclass
class ModuleInfo:
    """Informações de um módulo para exibição na lista.

    Contém os dados necessários para renderizar um card de módulo
    com título, descrição, quantidade de etapas e status de progresso.

    Attributes:
        id: Identificador único do módulo.
        title: Título do módulo.
        description: Descrição resumida (máximo 150 caracteres).
        total_steps: Quantidade total de etapas no módulo.
        progress_status: Status de progresso do usuário no módulo.
        progress_percentage: Percentual de conclusão (0.0 a 100.0).
    """

    id: str
    title: str
    description: str
    total_steps: int
    progress_status: ProgressStatus
    progress_percentage: float


class TrainingManager:
    """Gerenciador de treinamento e navegação.

    Responsável por toda a lógica de navegação entre etapas,
    listagem de módulos e conclusão de módulos.

    Attributes:
        db: Instância do banco de dados.
        progress_manager: Gerenciador de progresso.
        branch_manager: Gerenciador de ramificações.
    """

    def __init__(self, db: Database):
        """Inicializa o TrainingManager.

        Args:
            db: Instância do banco de dados SQLite.
        """
        self.db = db
        self.progress_manager = ProgressManager(db)
        self.branch_manager = BranchManager(db)

    def get_modules(self, user_id: str) -> List[ModuleInfo]:
        """Retorna lista de módulos publicados com status de progresso do usuário.

        Busca todos os módulos com status 'published' e enriquece com
        informações de progresso do usuário (status e percentual).

        Args:
            user_id: ID do usuário para buscar progresso.

        Returns:
            Lista de ModuleInfo com dados de cada módulo e progresso.
            Lista vazia se nenhum módulo publicado existe.

        Requirements: 1.3
        """
        cursor = self.db.execute(
            "SELECT id, title, description, status FROM modules WHERE status = ? ORDER BY created_at",
            (ModuleStatus.PUBLISHED.value,),
        )
        modules_rows = cursor.fetchall()

        result: List[ModuleInfo] = []
        for row in modules_rows:
            module_id = row["id"]

            # Contar total de etapas do módulo
            step_count_row = self.db.execute(
                "SELECT COUNT(*) as cnt FROM steps WHERE module_id = ?",
                (module_id,),
            ).fetchone()
            total_steps = step_count_row["cnt"] if step_count_row else 0

            # Buscar progresso do usuário
            progress = self.progress_manager.get_progress(user_id, module_id)

            if progress is None:
                progress_status = ProgressStatus.NOT_STARTED
                progress_percentage = 0.0
            else:
                progress_status = progress.status
                progress_percentage = progress.percentage

            result.append(
                ModuleInfo(
                    id=module_id,
                    title=row["title"],
                    description=row["description"],
                    total_steps=total_steps,
                    progress_status=progress_status,
                    progress_percentage=progress_percentage,
                )
            )

        return result

    def get_step(self, module_id: str, step_id: str) -> Step:
        """Retorna o conteúdo de uma etapa específica.

        Busca a etapa pelo ID e carrega todo seu conteúdo multimídia
        associado, ordenado por display_order.

        Args:
            module_id: ID do módulo ao qual a etapa pertence.
            step_id: ID da etapa a ser carregada.

        Returns:
            Step com conteúdo completo.

        Raises:
            ModuleNotFoundError: Se a etapa não é encontrada ou não pertence ao módulo.

        Requirements: 1.4
        """
        cursor = self.db.execute(
            "SELECT id, module_id, path_id, position, step_type, created_at "
            "FROM steps WHERE id = ? AND module_id = ?",
            (step_id, module_id),
        )
        row = cursor.fetchone()

        if row is None:
            raise ModuleNotFoundError(
                f"Etapa '{step_id}' não encontrada no módulo '{module_id}'."
            )

        return self._build_step_from_row(row)

    def get_next_step(
        self,
        module_id: str,
        current_step_id: str,
        path_id: Optional[str] = None,
    ) -> Optional[Step]:
        """Retorna a próxima etapa no caminho atual.

        Busca a etapa com position = current_position + 1 no mesmo
        caminho (path_id). Se path_id não é fornecido, determina o
        caminho a partir da etapa atual.

        Args:
            module_id: ID do módulo.
            current_step_id: ID da etapa atual.
            path_id: ID do caminho atual (opcional, derivado da etapa se omitido).

        Returns:
            Step seguinte ou None se é a última etapa do caminho.

        Requirements: 2.2
        """
        # Buscar a etapa atual para obter posição e path_id
        current_step_row = self.db.execute(
            "SELECT id, module_id, path_id, position FROM steps WHERE id = ? AND module_id = ?",
            (current_step_id, module_id),
        ).fetchone()

        if current_step_row is None:
            return None

        effective_path_id = path_id if path_id is not None else current_step_row["path_id"]
        current_position = current_step_row["position"]

        # Buscar próxima etapa (position + 1) no mesmo caminho
        next_row = self.db.execute(
            "SELECT id, module_id, path_id, position, step_type, created_at "
            "FROM steps WHERE module_id = ? AND path_id = ? AND position = ?",
            (module_id, effective_path_id, current_position + 1),
        ).fetchone()

        if next_row is None:
            return None

        return self._build_step_from_row(next_row)

    def get_previous_step(
        self,
        module_id: str,
        current_step_id: str,
        path_id: Optional[str] = None,
    ) -> Optional[Step]:
        """Retorna a etapa anterior no caminho atual.

        Busca a etapa com position = current_position - 1 no mesmo
        caminho (path_id). Se path_id não é fornecido, determina o
        caminho a partir da etapa atual.

        Args:
            module_id: ID do módulo.
            current_step_id: ID da etapa atual.
            path_id: ID do caminho atual (opcional, derivado da etapa se omitido).

        Returns:
            Step anterior ou None se é a primeira etapa do caminho.

        Requirements: 2.3
        """
        # Buscar a etapa atual para obter posição e path_id
        current_step_row = self.db.execute(
            "SELECT id, module_id, path_id, position FROM steps WHERE id = ? AND module_id = ?",
            (current_step_id, module_id),
        ).fetchone()

        if current_step_row is None:
            return None

        effective_path_id = path_id if path_id is not None else current_step_row["path_id"]
        current_position = current_step_row["position"]

        # Não há etapa anterior se position é 0
        if current_position <= 0:
            return None

        # Buscar etapa anterior (position - 1) no mesmo caminho
        prev_row = self.db.execute(
            "SELECT id, module_id, path_id, position, step_type, created_at "
            "FROM steps WHERE module_id = ? AND path_id = ? AND position = ?",
            (module_id, effective_path_id, current_position - 1),
        ).fetchone()

        if prev_row is None:
            return None

        return self._build_step_from_row(prev_row)

    def is_first_step(
        self,
        module_id: str,
        step_id: str,
        path_id: Optional[str] = None,
    ) -> bool:
        """Verifica se é a primeira etapa do caminho.

        A primeira etapa é aquela com position == 0 no caminho.

        Args:
            module_id: ID do módulo.
            step_id: ID da etapa.
            path_id: ID do caminho (opcional, derivado da etapa se omitido).

        Returns:
            True se é a primeira etapa, False caso contrário.

        Requirements: 2.4
        """
        row = self.db.execute(
            "SELECT position, path_id FROM steps WHERE id = ? AND module_id = ?",
            (step_id, module_id),
        ).fetchone()

        if row is None:
            return False

        return row["position"] == 0

    def is_last_step(
        self,
        module_id: str,
        step_id: str,
        path_id: Optional[str] = None,
    ) -> bool:
        """Verifica se é a última etapa do caminho.

        A última etapa é aquela com a maior position no caminho.

        Args:
            module_id: ID do módulo.
            step_id: ID da etapa.
            path_id: ID do caminho (opcional, derivado da etapa se omitido).

        Returns:
            True se é a última etapa, False caso contrário.

        Requirements: 2.5
        """
        row = self.db.execute(
            "SELECT position, path_id FROM steps WHERE id = ? AND module_id = ?",
            (step_id, module_id),
        ).fetchone()

        if row is None:
            return False

        effective_path_id = path_id if path_id is not None else row["path_id"]
        current_position = row["position"]

        # Buscar posição máxima no caminho
        max_row = self.db.execute(
            "SELECT MAX(position) as max_pos FROM steps WHERE module_id = ? AND path_id = ?",
            (module_id, effective_path_id),
        ).fetchone()

        if max_row is None or max_row["max_pos"] is None:
            return False

        return current_position == max_row["max_pos"]

    def complete_module(self, user_id: str, module_id: str) -> bool:
        """Marca módulo como concluído se critérios forem atendidos.

        Verifica se o usuário completou todas as etapas obrigatórias
        (caminho principal + pelo menos um caminho completo por ramificação)
        e marca o módulo como concluído.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.

        Returns:
            True se o módulo foi marcado como concluído, False se
            os critérios não foram atendidos.

        Requirements: 2.5, 5.4
        """
        # Verificar se o módulo existe
        module_row = self.db.execute(
            "SELECT id FROM modules WHERE id = ?",
            (module_id,),
        ).fetchone()

        if module_row is None:
            raise ModuleNotFoundError(
                f"Módulo '{module_id}' não encontrado."
            )

        # Delegar verificação de completude ao ProgressManager
        is_complete = self.progress_manager.is_module_complete(user_id, module_id)

        if is_complete:
            # Atualizar status para COMPLETED no user_progress
            now = datetime.now().isoformat()
            self.db.execute(
                "UPDATE user_progress SET status = ?, percentage = 100.0, last_accessed = ? "
                "WHERE user_id = ? AND module_id = ?",
                (ProgressStatus.COMPLETED.value, now, user_id, module_id),
            )
            self.db.commit()
            return True

        return False

    def get_first_step(self, module_id: str) -> Optional[Step]:
        """Retorna a primeira etapa do caminho principal de um módulo.

        Busca o caminho principal (is_main=1) do módulo e retorna
        a etapa com position=0.

        Args:
            module_id: ID do módulo.

        Returns:
            Step na posição 0 do caminho principal, ou None se não há etapas.

        Requirements: 1.4
        """
        # Buscar caminho principal do módulo
        main_path = self.db.execute(
            "SELECT id FROM paths WHERE module_id = ? AND is_main = 1",
            (module_id,),
        ).fetchone()

        if main_path is None:
            return None

        # Buscar primeira etapa (position=0) do caminho principal
        first_step_row = self.db.execute(
            "SELECT id, module_id, path_id, position, step_type, created_at "
            "FROM steps WHERE module_id = ? AND path_id = ? AND position = 0",
            (module_id, main_path["id"]),
        ).fetchone()

        if first_step_row is None:
            return None

        return self._build_step_from_row(first_step_row)

    def _build_step_from_row(self, row) -> Step:
        """Constrói um objeto Step a partir de uma row do banco de dados.

        Carrega o conteúdo multimídia associado à etapa, ordenado
        por display_order.

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
