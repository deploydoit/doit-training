"""Gerenciador de Progresso do Sistema de Treinamento.

Responsável por salvar, recuperar e gerenciar o progresso dos usuários
nos módulos de treinamento.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from models.database import Database
from models.data_models import UserProgress
from models.enums import ProgressStatus


class ProgressManager:
    """Gerencia salvamento e recuperação do progresso do usuário.

    Attributes:
        db: Instância do banco de dados.
        max_retries: Número máximo de tentativas ao salvar progresso.
        retry_interval: Intervalo em segundos entre tentativas.
    """

    def __init__(self, db: Database, max_retries: int = 3, retry_interval: int = 5):
        """Inicializa o ProgressManager.

        Args:
            db: Instância do banco de dados.
            max_retries: Número máximo de tentativas para salvar progresso.
            retry_interval: Intervalo em segundos entre tentativas de retry.
        """
        self.db = db
        self.max_retries = max_retries
        self.retry_interval = retry_interval

    def save_progress(
        self,
        user_id: str,
        module_id: str,
        step_id: str,
        path_id: Optional[str] = None,
    ) -> bool:
        """Salva progresso do usuário. Retenta até 3x em caso de falha.

        Registra a etapa atual do usuário, marca a etapa como concluída,
        e atualiza o percentual de conclusão do módulo.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.
            step_id: ID da etapa atual.
            path_id: ID do caminho atual (opcional).

        Returns:
            True se o progresso foi salvo com sucesso, False caso contrário.

        Requirements: 5.1, 5.5
        """
        for attempt in range(self.max_retries):
            try:
                self._do_save_progress(user_id, module_id, step_id, path_id)
                return True
            except Exception:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_interval)
        return False

    def _do_save_progress(
        self,
        user_id: str,
        module_id: str,
        step_id: str,
        path_id: Optional[str],
    ) -> None:
        """Executa o salvamento de progresso no banco de dados.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.
            step_id: ID da etapa atual.
            path_id: ID do caminho atual (opcional).
        """
        now = datetime.now().isoformat()

        # Marcar etapa como concluída (INSERT OR IGNORE para idempotência)
        self.db.execute(
            "INSERT OR IGNORE INTO completed_steps (user_id, step_id, completed_at) "
            "VALUES (?, ?, ?)",
            (user_id, step_id, now),
        )

        # Calcular percentual de conclusão
        percentage = self._calculate_percentage(user_id, module_id)

        # Determinar status
        if percentage >= 100.0:
            status = ProgressStatus.COMPLETED.value
        elif percentage > 0:
            status = ProgressStatus.IN_PROGRESS.value
        else:
            status = ProgressStatus.IN_PROGRESS.value

        # Inserir ou atualizar progresso (UPSERT com user_id + module_id como chave única)
        existing = self.db.execute(
            "SELECT id FROM user_progress WHERE user_id = ? AND module_id = ?",
            (user_id, module_id),
        ).fetchone()

        if existing:
            self.db.execute(
                "UPDATE user_progress SET current_step_id = ?, current_path_id = ?, "
                "status = ?, percentage = ?, last_accessed = ? "
                "WHERE user_id = ? AND module_id = ?",
                (step_id, path_id, status, percentage, now, user_id, module_id),
            )
        else:
            progress_id = str(uuid.uuid4())
            self.db.execute(
                "INSERT INTO user_progress "
                "(id, user_id, module_id, current_step_id, current_path_id, status, percentage, last_accessed, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (progress_id, user_id, module_id, step_id, path_id, status, percentage, now, now),
            )

        self.db.commit()

    def get_progress(self, user_id: str, module_id: str) -> Optional[UserProgress]:
        """Recupera último progresso do usuário em um módulo.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.

        Returns:
            UserProgress se existe progresso salvo, None caso contrário.

        Requirements: 5.2
        """
        row = self.db.execute(
            "SELECT * FROM user_progress WHERE user_id = ? AND module_id = ?",
            (user_id, module_id),
        ).fetchone()

        if row is None:
            return None

        # Buscar etapas concluídas
        completed_steps = self._get_completed_steps(user_id, module_id)

        # Buscar caminhos explorados
        explored_paths = self._get_explored_paths_list(user_id, module_id)

        return UserProgress(
            id=row["id"],
            user_id=row["user_id"],
            module_id=row["module_id"],
            current_step_id=row["current_step_id"],
            current_path_id=row["current_path_id"],
            completed_steps=completed_steps,
            explored_paths=explored_paths,
            status=ProgressStatus(row["status"]),
            percentage=row["percentage"],
            last_accessed=datetime.fromisoformat(row["last_accessed"])
            if row["last_accessed"]
            else datetime.now(),
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else datetime.now(),
        )

    def get_module_completion_percentage(self, user_id: str, module_id: str) -> float:
        """Calcula percentual de conclusão do módulo.

        O percentual é baseado na razão entre etapas concluídas e total
        de etapas do módulo.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.

        Returns:
            Percentual de conclusão (0.0 a 100.0).

        Requirements: 5.3
        """
        return self._calculate_percentage(user_id, module_id)

    def is_module_complete(self, user_id: str, module_id: str) -> bool:
        """Verifica se usuário completou todas etapas obrigatórias.

        Um módulo é considerado completo quando todas as etapas do caminho
        principal foram concluídas e pelo menos um caminho completo foi
        percorrido em cada ramificação.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.

        Returns:
            True se o módulo está completo, False caso contrário.

        Requirements: 5.4
        """
        # Buscar o caminho principal do módulo
        main_path = self.db.execute(
            "SELECT id FROM paths WHERE module_id = ? AND is_main = 1",
            (module_id,),
        ).fetchone()

        if main_path is None:
            return False

        # Buscar todas etapas do caminho principal
        main_steps = self.db.execute(
            "SELECT id FROM steps WHERE module_id = ? AND path_id = ?",
            (module_id, main_path["id"]),
        ).fetchall()

        if not main_steps:
            return False

        # Verificar se todas etapas do caminho principal foram concluídas
        main_step_ids = {row["id"] for row in main_steps}
        completed = set(self._get_completed_steps(user_id, module_id))

        if not main_step_ids.issubset(completed):
            return False

        # Verificar ramificações: pelo menos um caminho completo por branch
        branches = self.db.execute(
            "SELECT b.id as branch_id FROM branches b "
            "JOIN steps s ON b.step_id = s.id "
            "WHERE s.module_id = ?",
            (module_id,),
        ).fetchall()

        for branch in branches:
            # Buscar caminhos dessa ramificação
            branch_paths = self.db.execute(
                "SELECT p.id FROM paths p "
                "JOIN branch_options bo ON bo.path_id = p.id "
                "WHERE bo.branch_id = ?",
                (branch["branch_id"],),
            ).fetchall()

            if not branch_paths:
                continue

            # Pelo menos um caminho deve estar completamente percorrido
            any_path_complete = False
            for bp in branch_paths:
                path_steps = self.db.execute(
                    "SELECT id FROM steps WHERE path_id = ?",
                    (bp["id"],),
                ).fetchall()

                if not path_steps:
                    continue

                path_step_ids = {row["id"] for row in path_steps}
                if path_step_ids.issubset(completed):
                    any_path_complete = True
                    break

            if not any_path_complete:
                return False

        return True

    def get_all_progress(self, user_id: str) -> dict[str, UserProgress]:
        """Retorna progresso em todos os módulos.

        Args:
            user_id: ID do usuário.

        Returns:
            Dicionário com module_id como chave e UserProgress como valor.

        Requirements: 5.2, 5.3
        """
        rows = self.db.execute(
            "SELECT module_id FROM user_progress WHERE user_id = ?",
            (user_id,),
        ).fetchall()

        result: dict[str, UserProgress] = {}
        for row in rows:
            module_id = row["module_id"]
            progress = self.get_progress(user_id, module_id)
            if progress is not None:
                result[module_id] = progress

        return result

    def cleanup_expired(self, days: int = 90) -> int:
        """Remove progresso com mais de N dias sem acesso.

        Args:
            days: Número de dias de inatividade para considerar expirado.
                  Padrão: 90 dias.

        Returns:
            Número de registros de progresso removidos.

        Requirements: 5.2
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Contar registros a serem removidos
        count_row = self.db.execute(
            "SELECT COUNT(*) as cnt FROM user_progress WHERE last_accessed < ?",
            (cutoff_date,),
        ).fetchone()
        count = count_row["cnt"] if count_row else 0

        if count > 0:
            # Remover etapas concluídas dos registros expirados
            self.db.execute(
                "DELETE FROM completed_steps WHERE user_id IN "
                "(SELECT user_id FROM user_progress WHERE last_accessed < ?) "
                "AND step_id IN "
                "(SELECT s.id FROM steps s JOIN user_progress up ON s.module_id = up.module_id "
                "WHERE up.last_accessed < ? AND up.user_id = completed_steps.user_id)",
                (cutoff_date, cutoff_date),
            )

            # Remover caminhos explorados dos registros expirados
            self.db.execute(
                "DELETE FROM explored_paths WHERE user_id IN "
                "(SELECT user_id FROM user_progress WHERE last_accessed < ?)",
                (cutoff_date,),
            )

            # Remover os registros de progresso
            self.db.execute(
                "DELETE FROM user_progress WHERE last_accessed < ?",
                (cutoff_date,),
            )

            self.db.commit()

        return count

    def _calculate_percentage(self, user_id: str, module_id: str) -> float:
        """Calcula o percentual de conclusão baseado em etapas concluídas.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.

        Returns:
            Percentual de conclusão (0.0 a 100.0).
        """
        # Total de etapas do módulo
        total_row = self.db.execute(
            "SELECT COUNT(*) as cnt FROM steps WHERE module_id = ?",
            (module_id,),
        ).fetchone()
        total_steps = total_row["cnt"] if total_row else 0

        if total_steps == 0:
            return 0.0

        # Etapas concluídas pelo usuário neste módulo
        completed_row = self.db.execute(
            "SELECT COUNT(*) as cnt FROM completed_steps cs "
            "JOIN steps s ON cs.step_id = s.id "
            "WHERE cs.user_id = ? AND s.module_id = ?",
            (user_id, module_id),
        ).fetchone()
        completed_count = completed_row["cnt"] if completed_row else 0

        return round((completed_count / total_steps) * 100.0, 1)

    def _get_completed_steps(self, user_id: str, module_id: str) -> list[str]:
        """Retorna IDs das etapas concluídas pelo usuário em um módulo.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.

        Returns:
            Lista de IDs de etapas concluídas.
        """
        rows = self.db.execute(
            "SELECT cs.step_id FROM completed_steps cs "
            "JOIN steps s ON cs.step_id = s.id "
            "WHERE cs.user_id = ? AND s.module_id = ?",
            (user_id, module_id),
        ).fetchall()
        return [row["step_id"] for row in rows]

    def _get_explored_paths_list(self, user_id: str, module_id: str) -> list[str]:
        """Retorna IDs dos caminhos explorados pelo usuário em um módulo.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.

        Returns:
            Lista de IDs de caminhos explorados.
        """
        rows = self.db.execute(
            "SELECT ep.path_id FROM explored_paths ep "
            "JOIN paths p ON ep.path_id = p.id "
            "WHERE ep.user_id = ? AND p.module_id = ?",
            (user_id, module_id),
        ).fetchall()
        return [row["path_id"] for row in rows]
