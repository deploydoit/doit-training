"""Testes unitários para o TrainingManager.

Valida:
- get_modules: retorna módulos publicados com progresso do usuário
- get_step: retorna etapa com conteúdo completo
- get_next_step: retorna próxima etapa no caminho
- get_previous_step: retorna etapa anterior no caminho
- is_first_step: verifica se é primeira etapa
- is_last_step: verifica se é última etapa
- complete_module: marca módulo como concluído
- get_first_step: retorna primeira etapa do caminho principal

Requirements: 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5
"""

import pytest

from managers.training_manager import ModuleInfo, TrainingManager
from managers.errors import ModuleNotFoundError
from models.database import Database
from models.enums import ModuleStatus, ProgressStatus, StepType


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
def setup_basic_module(db):
    """Configura um módulo básico com 3 etapas sequenciais.

    Estrutura criada:
    - Módulo: mod1 (published)
    - Path principal: path_main (is_main=True)
      - Step 0: step_1 (content)
      - Step 1: step_2 (content)
      - Step 2: step_3 (content)
    - User: user1
    """
    # Módulo publicado
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        ("mod1", "Módulo Básico", "Descrição do módulo básico", "published"),
    )

    # Path principal
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        ("path_main", "mod1", "Principal", True),
    )

    # Steps
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

    # Conteúdo das etapas
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("content_1", "step_1", "text", "Conteúdo da etapa 1", None, 0),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("content_2", "step_2", "text", "Conteúdo da etapa 2", None, 0),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("content_3", "step_3", "text", "Conteúdo da etapa 3", None, 0),
    )

    # User
    db.execute(
        "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
        ("user1", "Teste User", "teste@example.com"),
    )

    db.commit()


@pytest.fixture
def setup_module_with_branch(db):
    """Configura um módulo com ramificação para testes de completude.

    Estrutura:
    - Módulo: mod_branch (published)
    - Path principal: path_main_b (is_main=True)
      - Step 0: step_intro (content)
      - Step 1: step_branch (branch)
    - Path A: path_a (parent_branch_id=branch1)
      - Step 0: step_a1 (content)
    - Path B: path_b (parent_branch_id=branch1)
      - Step 0: step_b1 (content)
    - User: user1
    """
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        ("mod_branch", "Módulo com Branch", "Descrição módulo branch", "published"),
    )

    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        ("path_main_b", "mod_branch", "Principal", True),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) VALUES (?, ?, ?, ?, ?)",
        ("path_a", "mod_branch", "branch1", "Caminho A", False),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) VALUES (?, ?, ?, ?, ?)",
        ("path_b", "mod_branch", "branch1", "Caminho B", False),
    )

    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_intro", "mod_branch", "path_main_b", 0, "content", "2024-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_branch", "mod_branch", "path_main_b", 1, "branch", "2024-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_a1", "mod_branch", "path_a", 0, "content", "2024-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_b1", "mod_branch", "path_b", 0, "content", "2024-01-01T00:00:00"),
    )

    db.execute(
        "INSERT INTO branches (id, step_id) VALUES (?, ?)",
        ("branch1", "step_branch"),
    )
    db.execute(
        "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
        ("opt1", "branch1", "Caminho A", "path_a", 0),
    )
    db.execute(
        "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
        ("opt2", "branch1", "Caminho B", "path_b", 1),
    )

    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c_intro", "step_intro", "text", "Introdução", None, 0),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c_a1", "step_a1", "text", "Conteúdo A1", None, 0),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c_b1", "step_b1", "text", "Conteúdo B1", None, 0),
    )

    db.execute(
        "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
        ("user1", "Teste User", "teste@example.com"),
    )

    db.commit()


class TestGetModules:
    """Testes para get_modules."""

    def test_returns_published_modules(self, training_manager, db, setup_basic_module):
        """Retorna apenas módulos publicados."""
        # Adicionar módulo draft (não deve aparecer)
        db.execute(
            "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
            ("mod_draft", "Módulo Draft", "Draft desc", "draft"),
        )
        db.commit()

        modules = training_manager.get_modules("user1")

        assert len(modules) == 1
        assert modules[0].id == "mod1"
        assert modules[0].title == "Módulo Básico"

    def test_returns_correct_step_count(self, training_manager, setup_basic_module):
        """Retorna contagem correta de etapas."""
        modules = training_manager.get_modules("user1")

        assert modules[0].total_steps == 3

    def test_returns_not_started_status_for_new_user(
        self, training_manager, setup_basic_module
    ):
        """Retorna NOT_STARTED para usuário sem progresso."""
        modules = training_manager.get_modules("user1")

        assert modules[0].progress_status == ProgressStatus.NOT_STARTED
        assert modules[0].progress_percentage == 0.0

    def test_returns_in_progress_status(self, training_manager, db, setup_basic_module):
        """Retorna IN_PROGRESS para usuário com progresso parcial."""
        # Salvar progresso
        training_manager.progress_manager.save_progress("user1", "mod1", "step_1", "path_main")

        modules = training_manager.get_modules("user1")

        assert modules[0].progress_status == ProgressStatus.IN_PROGRESS
        assert modules[0].progress_percentage > 0.0

    def test_returns_empty_list_when_no_published_modules(self, training_manager, db):
        """Retorna lista vazia quando não há módulos publicados."""
        db.execute(
            "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
            ("user1", "Teste", "teste@example.com"),
        )
        db.commit()

        modules = training_manager.get_modules("user1")
        assert modules == []

    def test_returns_module_info_instances(self, training_manager, setup_basic_module):
        """Verifica que retorna instâncias de ModuleInfo."""
        modules = training_manager.get_modules("user1")

        for module in modules:
            assert isinstance(module, ModuleInfo)

    def test_description_within_limit(self, training_manager, setup_basic_module):
        """Descrição não excede 150 caracteres."""
        modules = training_manager.get_modules("user1")

        for module in modules:
            assert len(module.description) <= 150


class TestGetStep:
    """Testes para get_step."""

    def test_returns_step_with_content(self, training_manager, setup_basic_module):
        """Retorna etapa com conteúdo carregado."""
        step = training_manager.get_step("mod1", "step_1")

        assert step.id == "step_1"
        assert step.module_id == "mod1"
        assert step.position == 0
        assert step.step_type == StepType.CONTENT
        assert len(step.content) == 1
        assert step.content[0].content_data == "Conteúdo da etapa 1"

    def test_raises_for_nonexistent_step(self, training_manager, setup_basic_module):
        """Levanta ModuleNotFoundError para etapa inexistente."""
        with pytest.raises(ModuleNotFoundError):
            training_manager.get_step("mod1", "nonexistent_step")

    def test_raises_for_wrong_module(self, training_manager, setup_basic_module):
        """Levanta ModuleNotFoundError se etapa não pertence ao módulo."""
        with pytest.raises(ModuleNotFoundError):
            training_manager.get_step("nonexistent_module", "step_1")


class TestGetNextStep:
    """Testes para get_next_step."""

    def test_returns_next_step(self, training_manager, setup_basic_module):
        """Retorna próxima etapa no caminho."""
        next_step = training_manager.get_next_step("mod1", "step_1")

        assert next_step is not None
        assert next_step.id == "step_2"
        assert next_step.position == 1

    def test_returns_none_at_last_step(self, training_manager, setup_basic_module):
        """Retorna None na última etapa do caminho."""
        next_step = training_manager.get_next_step("mod1", "step_3")

        assert next_step is None

    def test_returns_none_for_nonexistent_step(
        self, training_manager, setup_basic_module
    ):
        """Retorna None para etapa inexistente."""
        next_step = training_manager.get_next_step("mod1", "nonexistent")

        assert next_step is None

    def test_navigates_within_same_path(self, training_manager, setup_basic_module):
        """Navegação se mantém no mesmo caminho."""
        next_step = training_manager.get_next_step("mod1", "step_1", "path_main")

        assert next_step is not None
        assert next_step.path_id == "path_main"

    def test_sequential_navigation(self, training_manager, setup_basic_module):
        """Navegar sequencialmente percorre todas as etapas."""
        step1 = training_manager.get_next_step("mod1", "step_1")
        step2 = training_manager.get_next_step("mod1", step1.id)
        step3 = training_manager.get_next_step("mod1", step2.id)

        assert step1.id == "step_2"
        assert step2.id == "step_3"
        assert step3 is None


class TestGetPreviousStep:
    """Testes para get_previous_step."""

    def test_returns_previous_step(self, training_manager, setup_basic_module):
        """Retorna etapa anterior no caminho."""
        prev_step = training_manager.get_previous_step("mod1", "step_2")

        assert prev_step is not None
        assert prev_step.id == "step_1"
        assert prev_step.position == 0

    def test_returns_none_at_first_step(self, training_manager, setup_basic_module):
        """Retorna None na primeira etapa do caminho."""
        prev_step = training_manager.get_previous_step("mod1", "step_1")

        assert prev_step is None

    def test_returns_none_for_nonexistent_step(
        self, training_manager, setup_basic_module
    ):
        """Retorna None para etapa inexistente."""
        prev_step = training_manager.get_previous_step("mod1", "nonexistent")

        assert prev_step is None

    def test_round_trip_navigation(self, training_manager, setup_basic_module):
        """Avançar e retroceder retorna à etapa original."""
        next_step = training_manager.get_next_step("mod1", "step_1")
        prev_step = training_manager.get_previous_step("mod1", next_step.id)

        assert prev_step.id == "step_1"


class TestIsFirstStep:
    """Testes para is_first_step."""

    def test_first_step_returns_true(self, training_manager, setup_basic_module):
        """Primeira etapa (position=0) retorna True."""
        assert training_manager.is_first_step("mod1", "step_1") is True

    def test_non_first_step_returns_false(self, training_manager, setup_basic_module):
        """Etapa não-primeira retorna False."""
        assert training_manager.is_first_step("mod1", "step_2") is False
        assert training_manager.is_first_step("mod1", "step_3") is False

    def test_nonexistent_step_returns_false(self, training_manager, setup_basic_module):
        """Etapa inexistente retorna False."""
        assert training_manager.is_first_step("mod1", "nonexistent") is False


class TestIsLastStep:
    """Testes para is_last_step."""

    def test_last_step_returns_true(self, training_manager, setup_basic_module):
        """Última etapa (posição máxima) retorna True."""
        assert training_manager.is_last_step("mod1", "step_3") is True

    def test_non_last_step_returns_false(self, training_manager, setup_basic_module):
        """Etapa não-última retorna False."""
        assert training_manager.is_last_step("mod1", "step_1") is False
        assert training_manager.is_last_step("mod1", "step_2") is False

    def test_nonexistent_step_returns_false(self, training_manager, setup_basic_module):
        """Etapa inexistente retorna False."""
        assert training_manager.is_last_step("mod1", "nonexistent") is False


class TestCompleteModule:
    """Testes para complete_module."""

    def test_completes_when_all_main_steps_done(
        self, training_manager, db, setup_basic_module
    ):
        """Completa módulo quando todas etapas do caminho principal foram feitas."""
        # Marcar todas as etapas como concluídas
        training_manager.progress_manager.save_progress("user1", "mod1", "step_1", "path_main")
        training_manager.progress_manager.save_progress("user1", "mod1", "step_2", "path_main")
        training_manager.progress_manager.save_progress("user1", "mod1", "step_3", "path_main")

        result = training_manager.complete_module("user1", "mod1")

        assert result is True

    def test_does_not_complete_with_missing_steps(
        self, training_manager, db, setup_basic_module
    ):
        """Não completa módulo se há etapas faltando."""
        training_manager.progress_manager.save_progress("user1", "mod1", "step_1", "path_main")

        result = training_manager.complete_module("user1", "mod1")

        assert result is False

    def test_raises_for_nonexistent_module(self, training_manager, db, setup_basic_module):
        """Levanta ModuleNotFoundError para módulo inexistente."""
        with pytest.raises(ModuleNotFoundError):
            training_manager.complete_module("user1", "nonexistent_module")

    def test_updates_progress_status_to_completed(
        self, training_manager, db, setup_basic_module
    ):
        """Atualiza status do progresso para COMPLETED."""
        training_manager.progress_manager.save_progress("user1", "mod1", "step_1", "path_main")
        training_manager.progress_manager.save_progress("user1", "mod1", "step_2", "path_main")
        training_manager.progress_manager.save_progress("user1", "mod1", "step_3", "path_main")

        training_manager.complete_module("user1", "mod1")

        progress = training_manager.progress_manager.get_progress("user1", "mod1")
        assert progress.status == ProgressStatus.COMPLETED
        assert progress.percentage == 100.0

    def test_requires_branch_path_completion(
        self, training_manager, db, setup_module_with_branch
    ):
        """Requer pelo menos um caminho completo em cada ramificação."""
        # Completar apenas etapas do caminho principal
        training_manager.progress_manager.save_progress(
            "user1", "mod_branch", "step_intro", "path_main_b"
        )
        training_manager.progress_manager.save_progress(
            "user1", "mod_branch", "step_branch", "path_main_b"
        )

        result = training_manager.complete_module("user1", "mod_branch")
        assert result is False

        # Agora completar um caminho de ramificação
        training_manager.progress_manager.save_progress(
            "user1", "mod_branch", "step_a1", "path_a"
        )

        result = training_manager.complete_module("user1", "mod_branch")
        assert result is True


class TestGetFirstStep:
    """Testes para get_first_step."""

    def test_returns_first_step_of_main_path(
        self, training_manager, setup_basic_module
    ):
        """Retorna primeira etapa do caminho principal."""
        step = training_manager.get_first_step("mod1")

        assert step is not None
        assert step.id == "step_1"
        assert step.position == 0
        assert step.path_id == "path_main"

    def test_returns_none_for_module_without_main_path(self, training_manager, db):
        """Retorna None para módulo sem caminho principal."""
        db.execute(
            "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
            ("mod_empty", "Módulo Vazio", "Sem caminho principal", "published"),
        )
        db.commit()

        step = training_manager.get_first_step("mod_empty")
        assert step is None

    def test_returns_none_for_nonexistent_module(self, training_manager, db):
        """Retorna None para módulo que não existe."""
        step = training_manager.get_first_step("nonexistent")
        assert step is None
