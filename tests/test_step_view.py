"""Testes unitários para pages/step_view.py.

Valida a lógica da página de visualização de etapa:
- Indicador "Etapa X de Y"
- Desabilitação do botão retroceder na primeira etapa
- Substituição por "Concluir Módulo" na última etapa
- Salvamento automático de progresso ao avançar
- Navegação entre etapas (avançar/retroceder)

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.1
"""

import pytest

from managers.training_manager import TrainingManager
from managers.progress_manager import ProgressManager
from models.database import Database
from pages.step_view import (
    _get_total_steps_in_path,
    _on_next_click,
    _on_previous_click,
    _on_complete_click,
)


@pytest.fixture
def db():
    """Banco de dados em memória para testes."""
    database = Database(":memory:")
    database.initialize()
    yield database
    database.close()


@pytest.fixture
def training_manager(db):
    """Instância de TrainingManager para testes."""
    return TrainingManager(db)


@pytest.fixture
def progress_manager(db):
    """Instância de ProgressManager para testes."""
    return ProgressManager(db)


@pytest.fixture
def setup_module_3_steps(db):
    """Configura módulo com 3 etapas sequenciais para testes de navegação.

    Estrutura:
    - Módulo: mod1 (published)
    - Path principal: path_main (is_main=True)
      - Step 0: step_1 (content)
      - Step 1: step_2 (content)
      - Step 2: step_3 (content)
    - User: user1
    """
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        ("mod1", "Módulo Teste", "Descrição", "published"),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        ("path_main", "mod1", "Principal", True),
    )
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_1", "mod1", "path_main", 0, "content", "2024-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_2", "mod1", "path_main", 1, "content", "2024-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_3", "mod1", "path_main", 2, "content", "2024-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c1", "step_1", "text", "Conteúdo 1", None, 0),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c2", "step_2", "text", "Conteúdo 2", None, 0),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c3", "step_3", "text", "Conteúdo 3", None, 0),
    )
    db.execute(
        "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
        ("user1", "Teste User", "teste@example.com"),
    )
    db.commit()


class TestGetTotalStepsInPath:
    """Testes para _get_total_steps_in_path."""

    def test_returns_correct_count(self, training_manager, setup_module_3_steps):
        """Deve retornar o total correto de etapas no caminho."""
        total = _get_total_steps_in_path(training_manager, "mod1", "path_main")
        assert total == 3

    def test_returns_zero_for_nonexistent_path(self, training_manager, setup_module_3_steps):
        """Deve retornar 0 para caminho inexistente."""
        total = _get_total_steps_in_path(training_manager, "mod1", "nonexistent")
        assert total == 0


class TestNavigationState:
    """Testes para o estado de navegação (first/last step)."""

    def test_first_step_detected(self, training_manager, setup_module_3_steps):
        """A primeira etapa (position=0) deve ser detectada como primeira."""
        assert training_manager.is_first_step("mod1", "step_1") is True

    def test_middle_step_not_first(self, training_manager, setup_module_3_steps):
        """Uma etapa intermediária não é a primeira."""
        assert training_manager.is_first_step("mod1", "step_2") is False

    def test_last_step_detected(self, training_manager, setup_module_3_steps):
        """A última etapa deve ser detectada como última."""
        assert training_manager.is_last_step("mod1", "step_3") is True

    def test_middle_step_not_last(self, training_manager, setup_module_3_steps):
        """Uma etapa intermediária não é a última."""
        assert training_manager.is_last_step("mod1", "step_2") is False

    def test_first_step_not_last(self, training_manager, setup_module_3_steps):
        """A primeira etapa não é a última."""
        assert training_manager.is_last_step("mod1", "step_1") is False


class TestOnPreviousClick:
    """Testes para _on_previous_click callback."""

    def test_navigates_to_previous_step(self, training_manager, setup_module_3_steps, monkeypatch):
        """Deve atualizar session_state com o step anterior."""
        import streamlit as st

        # Mock session_state
        session_state = {}
        monkeypatch.setattr(st, "session_state", session_state)

        step = training_manager.get_step("mod1", "step_2")
        _on_previous_click(
            step=step,
            training_manager=training_manager,
            module_id="mod1",
        )
        assert session_state["current_step_id"] == "step_1"
        assert session_state["current_path_id"] == "path_main"

    def test_does_not_navigate_from_first_step(self, training_manager, setup_module_3_steps, monkeypatch):
        """Não deve atualizar session_state quando já está na primeira etapa."""
        import streamlit as st

        session_state = {}
        monkeypatch.setattr(st, "session_state", session_state)

        step = training_manager.get_step("mod1", "step_1")
        _on_previous_click(
            step=step,
            training_manager=training_manager,
            module_id="mod1",
        )
        # session_state não é atualizado pois get_previous_step retorna None
        assert "current_step_id" not in session_state


class TestOnNextClick:
    """Testes para _on_next_click callback."""

    def test_navigates_to_next_step(self, training_manager, progress_manager, setup_module_3_steps, monkeypatch):
        """Deve atualizar session_state com o próximo step."""
        import streamlit as st

        session_state = {}
        monkeypatch.setattr(st, "session_state", session_state)

        step = training_manager.get_step("mod1", "step_1")
        _on_next_click(
            step=step,
            training_manager=training_manager,
            progress_manager=progress_manager,
            user_id="user1",
            module_id="mod1",
        )
        assert session_state["current_step_id"] == "step_2"
        assert session_state["current_path_id"] == "path_main"

    def test_saves_progress_on_advance(self, training_manager, progress_manager, setup_module_3_steps, monkeypatch):
        """Deve salvar progresso automaticamente ao avançar (Requirement 5.1)."""
        import streamlit as st

        session_state = {}
        monkeypatch.setattr(st, "session_state", session_state)

        step = training_manager.get_step("mod1", "step_1")
        _on_next_click(
            step=step,
            training_manager=training_manager,
            progress_manager=progress_manager,
            user_id="user1",
            module_id="mod1",
        )

        # Verificar que progresso foi salvo
        progress = progress_manager.get_progress("user1", "mod1")
        assert progress is not None
        assert progress.current_step_id == "step_2"

    def test_does_not_navigate_from_last_step(self, training_manager, progress_manager, setup_module_3_steps, monkeypatch):
        """Não deve atualizar session_state quando já está na última etapa."""
        import streamlit as st

        session_state = {}
        monkeypatch.setattr(st, "session_state", session_state)

        step = training_manager.get_step("mod1", "step_3")
        _on_next_click(
            step=step,
            training_manager=training_manager,
            progress_manager=progress_manager,
            user_id="user1",
            module_id="mod1",
        )
        assert "current_step_id" not in session_state


class TestOnCompleteClick:
    """Testes para _on_complete_click callback."""

    def test_saves_progress_and_completes_module(
        self, db, training_manager, progress_manager, setup_module_3_steps, monkeypatch
    ):
        """Deve salvar progresso e concluir o módulo quando todas etapas foram completadas."""
        import streamlit as st

        session_state = {}
        monkeypatch.setattr(st, "session_state", session_state)

        # Simular que o usuário já completou as duas primeiras etapas
        db.execute(
            "INSERT OR IGNORE INTO completed_steps (user_id, step_id, completed_at) VALUES (?, ?, ?)",
            ("user1", "step_1", "2024-01-01T00:00:00"),
        )
        db.execute(
            "INSERT OR IGNORE INTO completed_steps (user_id, step_id, completed_at) VALUES (?, ?, ?)",
            ("user1", "step_2", "2024-01-01T00:00:00"),
        )
        db.commit()

        step = training_manager.get_step("mod1", "step_3")
        _on_complete_click(
            step=step,
            training_manager=training_manager,
            progress_manager=progress_manager,
            user_id="user1",
            module_id="mod1",
        )

        assert session_state["module_completed"] is True
        assert session_state["current_step_id"] is None

    def test_does_not_complete_when_steps_missing(
        self, training_manager, progress_manager, setup_module_3_steps, monkeypatch
    ):
        """Não deve marcar como concluído se nem todas as etapas foram completadas."""
        import streamlit as st

        session_state = {}
        monkeypatch.setattr(st, "session_state", session_state)

        # Apenas step_3 será marcado pelo save_progress no callback
        step = training_manager.get_step("mod1", "step_3")
        _on_complete_click(
            step=step,
            training_manager=training_manager,
            progress_manager=progress_manager,
            user_id="user1",
            module_id="mod1",
        )

        assert session_state["module_completed"] is False
        assert session_state["current_step_id"] is None


class TestProgressIndicator:
    """Testes para o indicador 'Etapa X de Y' (Requirement 2.6)."""

    def test_step_1_of_3(self, training_manager, setup_module_3_steps):
        """Primeira etapa: posição 0 → 'Etapa 1 de 3'."""
        step = training_manager.get_step("mod1", "step_1")
        total = _get_total_steps_in_path(training_manager, "mod1", step.path_id)
        current = step.position + 1
        assert current == 1
        assert total == 3

    def test_step_2_of_3(self, training_manager, setup_module_3_steps):
        """Segunda etapa: posição 1 → 'Etapa 2 de 3'."""
        step = training_manager.get_step("mod1", "step_2")
        total = _get_total_steps_in_path(training_manager, "mod1", step.path_id)
        current = step.position + 1
        assert current == 2
        assert total == 3

    def test_step_3_of_3(self, training_manager, setup_module_3_steps):
        """Última etapa: posição 2 → 'Etapa 3 de 3'."""
        step = training_manager.get_step("mod1", "step_3")
        total = _get_total_steps_in_path(training_manager, "mod1", step.path_id)
        current = step.position + 1
        assert current == 3
        assert total == 3
