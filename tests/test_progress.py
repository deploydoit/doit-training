"""Testes unitários para o ProgressManager.

Valida:
- save_progress com retry automático (Req 5.1, 5.5)
- get_progress (Req 5.2)
- get_module_completion_percentage (Req 5.3)
- is_module_complete (Req 5.4)
- get_all_progress (Req 5.2)
- cleanup_expired (Req 5.2)
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from managers.progress_manager import ProgressManager
from models.database import Database
from models.enums import ProgressStatus


@pytest.fixture
def db():
    """Banco de dados em memória para testes."""
    database = Database(":memory:")
    database.initialize()
    yield database
    database.close()


@pytest.fixture
def pm(db):
    """ProgressManager com retry_interval=0 para testes rápidos."""
    return ProgressManager(db, max_retries=3, retry_interval=0)


@pytest.fixture
def setup_module_with_steps(db):
    """Cria um módulo com caminho principal e etapas."""

    def _setup(module_id="mod1", num_steps=3):
        db.execute(
            "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
            (module_id, "Módulo Teste", "Descrição teste", "published"),
        )
        path_id = f"{module_id}_main_path"
        db.execute(
            "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
            (path_id, module_id, "Principal", True),
        )
        step_ids = []
        for i in range(num_steps):
            step_id = f"{module_id}_step_{i}"
            db.execute(
                "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, ?)",
                (step_id, module_id, path_id, i, "content"),
            )
            step_ids.append(step_id)
        db.commit()
        return path_id, step_ids

    return _setup


@pytest.fixture
def setup_user(db):
    """Cria um usuário para testes."""

    def _setup(user_id="user1", name="Teste", email="teste@email.com"):
        db.execute(
            "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
            (user_id, name, email),
        )
        db.commit()
        return user_id

    return _setup


class TestSaveProgress:
    """Testes para save_progress com retry automático."""

    def test_save_progress_creates_new_record(self, pm, setup_module_with_steps, setup_user):
        """Salva progresso para um módulo não iniciado."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        result = pm.save_progress(user_id, "mod1", step_ids[0], path_id)

        assert result is True

    def test_save_progress_updates_existing_record(self, pm, setup_module_with_steps, setup_user):
        """Atualiza progresso existente ao avançar etapa."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        pm.save_progress(user_id, "mod1", step_ids[0], path_id)
        pm.save_progress(user_id, "mod1", step_ids[1], path_id)

        progress = pm.get_progress(user_id, "mod1")
        assert progress is not None
        assert progress.current_step_id == step_ids[1]

    def test_save_progress_marks_step_completed(self, pm, setup_module_with_steps, setup_user):
        """Salvar progresso marca a etapa como concluída."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        pm.save_progress(user_id, "mod1", step_ids[0], path_id)

        progress = pm.get_progress(user_id, "mod1")
        assert step_ids[0] in progress.completed_steps

    def test_save_progress_retry_on_failure(self, db, setup_module_with_steps, setup_user):
        """Retenta até 3x em caso de falha."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        pm = ProgressManager(db, max_retries=3, retry_interval=0)

        call_count = 0
        original_do_save = pm._do_save_progress

        def failing_save(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("DB Error simulado")
            return original_do_save(*args, **kwargs)

        with patch.object(pm, "_do_save_progress", side_effect=failing_save):
            result = pm.save_progress(user_id, "mod1", step_ids[0], path_id)

        assert result is True
        assert call_count == 3

    def test_save_progress_returns_false_after_all_retries_fail(self, db, setup_module_with_steps, setup_user):
        """Retorna False se todas as tentativas falharem."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        pm = ProgressManager(db, max_retries=3, retry_interval=0)

        with patch.object(pm, "_do_save_progress", side_effect=Exception("DB Error")):
            result = pm.save_progress(user_id, "mod1", step_ids[0], path_id)

        assert result is False

    def test_save_progress_idempotent_completed_steps(self, pm, setup_module_with_steps, setup_user):
        """Salvar progresso na mesma etapa duas vezes não duplica completed_steps."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        pm.save_progress(user_id, "mod1", step_ids[0], path_id)
        pm.save_progress(user_id, "mod1", step_ids[0], path_id)

        progress = pm.get_progress(user_id, "mod1")
        assert progress.completed_steps.count(step_ids[0]) == 1


class TestGetProgress:
    """Testes para get_progress."""

    def test_get_progress_returns_none_for_no_progress(self, pm, setup_module_with_steps, setup_user):
        """Retorna None se não existe progresso."""
        setup_module_with_steps()
        user_id = setup_user()

        result = pm.get_progress(user_id, "mod1")
        assert result is None

    def test_get_progress_returns_user_progress(self, pm, setup_module_with_steps, setup_user):
        """Retorna UserProgress com dados corretos."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        pm.save_progress(user_id, "mod1", step_ids[1], path_id)

        progress = pm.get_progress(user_id, "mod1")
        assert progress is not None
        assert progress.user_id == user_id
        assert progress.module_id == "mod1"
        assert progress.current_step_id == step_ids[1]
        assert progress.current_path_id == path_id
        assert progress.status == ProgressStatus.IN_PROGRESS

    def test_get_progress_includes_completed_steps(self, pm, setup_module_with_steps, setup_user):
        """Progresso inclui lista de etapas concluídas."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        pm.save_progress(user_id, "mod1", step_ids[0], path_id)
        pm.save_progress(user_id, "mod1", step_ids[1], path_id)

        progress = pm.get_progress(user_id, "mod1")
        assert step_ids[0] in progress.completed_steps
        assert step_ids[1] in progress.completed_steps


class TestGetModuleCompletionPercentage:
    """Testes para get_module_completion_percentage."""

    def test_zero_percent_when_no_progress(self, pm, setup_module_with_steps, setup_user):
        """0% quando não há progresso."""
        setup_module_with_steps(num_steps=5)
        user_id = setup_user()

        result = pm.get_module_completion_percentage(user_id, "mod1")
        assert result == 0.0

    def test_percentage_after_completing_some_steps(self, pm, setup_module_with_steps, setup_user):
        """Percentual correto após completar algumas etapas."""
        path_id, step_ids = setup_module_with_steps(num_steps=4)
        user_id = setup_user()

        pm.save_progress(user_id, "mod1", step_ids[0], path_id)
        pm.save_progress(user_id, "mod1", step_ids[1], path_id)

        result = pm.get_module_completion_percentage(user_id, "mod1")
        assert result == 50.0

    def test_hundred_percent_when_all_complete(self, pm, setup_module_with_steps, setup_user):
        """100% quando todas as etapas estão concluídas."""
        path_id, step_ids = setup_module_with_steps(num_steps=3)
        user_id = setup_user()

        for step_id in step_ids:
            pm.save_progress(user_id, "mod1", step_id, path_id)

        result = pm.get_module_completion_percentage(user_id, "mod1")
        assert result == 100.0

    def test_zero_percent_for_module_with_no_steps(self, pm, db, setup_user):
        """0% para módulo sem etapas."""
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("empty_mod", "Vazio", "Módulo sem etapas"),
        )
        db.commit()
        user_id = setup_user()

        result = pm.get_module_completion_percentage(user_id, "empty_mod")
        assert result == 0.0


class TestIsModuleComplete:
    """Testes para is_module_complete."""

    def test_not_complete_when_no_progress(self, pm, setup_module_with_steps, setup_user):
        """Módulo não completo sem progresso."""
        setup_module_with_steps()
        user_id = setup_user()

        assert pm.is_module_complete(user_id, "mod1") is False

    def test_not_complete_when_partially_done(self, pm, setup_module_with_steps, setup_user):
        """Módulo não completo com progresso parcial."""
        path_id, step_ids = setup_module_with_steps(num_steps=3)
        user_id = setup_user()

        pm.save_progress(user_id, "mod1", step_ids[0], path_id)

        assert pm.is_module_complete(user_id, "mod1") is False

    def test_complete_when_all_main_steps_done(self, pm, setup_module_with_steps, setup_user):
        """Módulo completo quando todas etapas do caminho principal foram concluídas."""
        path_id, step_ids = setup_module_with_steps(num_steps=3)
        user_id = setup_user()

        for step_id in step_ids:
            pm.save_progress(user_id, "mod1", step_id, path_id)

        assert pm.is_module_complete(user_id, "mod1") is True

    def test_not_complete_without_branch_path(self, pm, db, setup_user):
        """Módulo com ramificação não completo se nenhum caminho da branch foi percorrido."""
        # Setup: módulo com caminho principal e uma ramificação
        db.execute(
            "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
            ("mod_branch", "Módulo Branch", "Com ramificação", "published"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
            ("main_path", "mod_branch", "Principal", True),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, ?)",
            ("main_step_0", "mod_branch", "main_path", 0, "content"),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, ?)",
            ("branch_step", "mod_branch", "main_path", 1, "branch"),
        )
        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            ("branch1", "branch_step"),
        )
        # Caminhos da ramificação
        db.execute(
            "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
            ("branch_path_a", "mod_branch", "Caminho A", False),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
            ("branch_path_b", "mod_branch", "Caminho B", False),
        )
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
            ("opt_a", "branch1", "Opção A", "branch_path_a", 0),
        )
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
            ("opt_b", "branch1", "Opção B", "branch_path_b", 1),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, ?)",
            ("ba_step_0", "mod_branch", "branch_path_a", 0, "content"),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, ?)",
            ("bb_step_0", "mod_branch", "branch_path_b", 0, "content"),
        )
        db.commit()

        user_id = setup_user()

        # Completar apenas caminho principal (sem branch paths)
        pm = ProgressManager(db, retry_interval=0)
        pm.save_progress(user_id, "mod_branch", "main_step_0", "main_path")
        pm.save_progress(user_id, "mod_branch", "branch_step", "main_path")

        assert pm.is_module_complete(user_id, "mod_branch") is False

    def test_complete_with_one_branch_path_done(self, pm, db, setup_user):
        """Módulo completo quando pelo menos um caminho da ramificação foi percorrido."""
        db.execute(
            "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
            ("mod_branch", "Módulo Branch", "Com ramificação", "published"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
            ("main_path", "mod_branch", "Principal", True),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, ?)",
            ("main_step_0", "mod_branch", "main_path", 0, "branch"),
        )
        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            ("branch1", "main_step_0"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
            ("branch_path_a", "mod_branch", "Caminho A", False),
        )
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
            ("opt_a", "branch1", "Opção A", "branch_path_a", 0),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, ?)",
            ("ba_step_0", "mod_branch", "branch_path_a", 0, "content"),
        )
        db.commit()

        user_id = setup_user()
        pm_local = ProgressManager(db, retry_interval=0)

        # Completar caminho principal + um caminho da ramificação
        pm_local.save_progress(user_id, "mod_branch", "main_step_0", "main_path")
        pm_local.save_progress(user_id, "mod_branch", "ba_step_0", "branch_path_a")

        assert pm_local.is_module_complete(user_id, "mod_branch") is True


class TestGetAllProgress:
    """Testes para get_all_progress."""

    def test_empty_when_no_progress(self, pm, setup_user):
        """Retorna dicionário vazio sem progresso."""
        user_id = setup_user()

        result = pm.get_all_progress(user_id)
        assert result == {}

    def test_returns_progress_for_all_modules(self, pm, db, setup_user):
        """Retorna progresso de todos os módulos do usuário."""
        user_id = setup_user()

        # Criar dois módulos
        for mod_id in ["mod1", "mod2"]:
            db.execute(
                "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
                (mod_id, f"Módulo {mod_id}", "Desc"),
            )
            path_id = f"{mod_id}_path"
            db.execute(
                "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
                (path_id, mod_id, "Principal", True),
            )
            db.execute(
                "INSERT INTO steps (id, module_id, path_id, position) VALUES (?, ?, ?, ?)",
                (f"{mod_id}_step_0", mod_id, path_id, 0),
            )
        db.commit()

        pm.save_progress(user_id, "mod1", "mod1_step_0", "mod1_path")
        pm.save_progress(user_id, "mod2", "mod2_step_0", "mod2_path")

        result = pm.get_all_progress(user_id)
        assert "mod1" in result
        assert "mod2" in result
        assert len(result) == 2


class TestCleanupExpired:
    """Testes para cleanup_expired."""

    def test_removes_old_progress(self, pm, db, setup_module_with_steps, setup_user):
        """Remove progresso com mais de 90 dias."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        # Salvar progresso e manualmente atrasar o last_accessed
        pm.save_progress(user_id, "mod1", step_ids[0], path_id)

        old_date = (datetime.now() - timedelta(days=91)).isoformat()
        db.execute(
            "UPDATE user_progress SET last_accessed = ? WHERE user_id = ? AND module_id = ?",
            (old_date, user_id, "mod1"),
        )
        db.commit()

        removed = pm.cleanup_expired(days=90)
        assert removed == 1

        # Verificar que o progresso foi removido
        progress = pm.get_progress(user_id, "mod1")
        assert progress is None

    def test_keeps_recent_progress(self, pm, db, setup_module_with_steps, setup_user):
        """Mantém progresso recente (menos de 90 dias)."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        pm.save_progress(user_id, "mod1", step_ids[0], path_id)

        removed = pm.cleanup_expired(days=90)
        assert removed == 0

        progress = pm.get_progress(user_id, "mod1")
        assert progress is not None

    def test_returns_zero_when_nothing_to_clean(self, pm, setup_user):
        """Retorna 0 se não há nada para limpar."""
        setup_user()
        removed = pm.cleanup_expired(days=90)
        assert removed == 0

    def test_custom_days_parameter(self, pm, db, setup_module_with_steps, setup_user):
        """Aceita parâmetro customizado de dias."""
        path_id, step_ids = setup_module_with_steps()
        user_id = setup_user()

        pm.save_progress(user_id, "mod1", step_ids[0], path_id)

        old_date = (datetime.now() - timedelta(days=31)).isoformat()
        db.execute(
            "UPDATE user_progress SET last_accessed = ? WHERE user_id = ? AND module_id = ?",
            (old_date, user_id, "mod1"),
        )
        db.commit()

        removed = pm.cleanup_expired(days=30)
        assert removed == 1
