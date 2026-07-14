"""Testes unitários para a página de ramificações (branch_view).

Valida:
- should_show_return_button: lógica para exibir botão de retorno
- _render_path_unavailable_error: tratamento de erro de caminho indisponível
- Integração entre branch_view e BranchManager

Requirements: 3.1, 3.2, 3.4, 3.5, 3.6
"""

import pytest

from managers.branch_manager import BranchManager
from managers.training_manager import TrainingManager
from models.database import Database
from pages.branch_view import should_show_return_button


@pytest.fixture
def db():
    """Banco de dados em memória para testes."""
    database = Database(":memory:")
    database.initialize()
    yield database
    database.close()


@pytest.fixture
def branch_manager(db):
    """Instância de BranchManager para testes."""
    return BranchManager(db)


@pytest.fixture
def training_manager(db):
    """Instância de TrainingManager para testes."""
    return TrainingManager(db)


@pytest.fixture
def setup_branch_scenario(db):
    """Configura cenário com módulo, branch e paths para testes.

    Estrutura:
    - Módulo: mod1
    - path_main (is_main=True): step_0 (content), step_branch (branch)
    - path_a (parent_branch_id=branch1): step_a1, step_a2 (última)
    - path_b (parent_branch_id=branch1): step_b1 (única e última)
    - branch1 em step_branch com opções opt1->path_a, opt2->path_b
    """
    # Módulo
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        ("mod1", "Módulo Teste", "Desc do módulo", "published"),
    )

    # Paths
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        ("path_main", "mod1", "Principal", True),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) VALUES (?, ?, ?, ?, ?)",
        ("path_a", "mod1", "branch1", "Caminho A", False),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) VALUES (?, ?, ?, ?, ?)",
        ("path_b", "mod1", "branch1", "Caminho B", False),
    )

    # Steps no caminho principal
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_0", "mod1", "path_main", 0, "content", "2024-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_branch", "mod1", "path_main", 1, "branch", "2024-01-01T00:00:00"),
    )

    # Steps no caminho A (2 etapas)
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_a1", "mod1", "path_a", 0, "content", "2024-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_a2", "mod1", "path_a", 1, "content", "2024-01-01T00:00:00"),
    )

    # Steps no caminho B (1 etapa)
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("step_b1", "mod1", "path_b", 0, "content", "2024-01-01T00:00:00"),
    )

    # Branch
    db.execute(
        "INSERT INTO branches (id, step_id) VALUES (?, ?)",
        ("branch1", "step_branch"),
    )

    # Branch options
    db.execute(
        "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
        ("opt1", "branch1", "Explorar Caminho A detalhado", "path_a", 0),
    )
    db.execute(
        "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
        ("opt2", "branch1", "Explorar Caminho B resumido", "path_b", 1),
    )

    # Step contents
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c_a1", "step_a1", "text", "Conteúdo A1", None, 0),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c_a2", "step_a2", "text", "Conteúdo A2", None, 0),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c_b1", "step_b1", "text", "Conteúdo B1", None, 0),
    )

    # User
    db.execute(
        "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
        ("user1", "Teste User", "teste@example.com"),
    )

    db.commit()


class TestShouldShowReturnButton:
    """Testes para should_show_return_button."""

    def test_shows_button_at_last_step_of_branch_path(
        self, branch_manager, training_manager, setup_branch_scenario
    ):
        """Exibe botão na última etapa de um caminho de ramificação."""
        result = should_show_return_button(
            branch_manager=branch_manager,
            training_manager=training_manager,
            step_id="step_a2",
            module_id="mod1",
            path_id="path_a",
        )
        assert result is True

    def test_shows_button_at_single_step_branch_path(
        self, branch_manager, training_manager, setup_branch_scenario
    ):
        """Exibe botão quando caminho de branch tem apenas 1 etapa (é a última)."""
        result = should_show_return_button(
            branch_manager=branch_manager,
            training_manager=training_manager,
            step_id="step_b1",
            module_id="mod1",
            path_id="path_b",
        )
        assert result is True

    def test_hides_button_at_non_last_step(
        self, branch_manager, training_manager, setup_branch_scenario
    ):
        """Não exibe botão em etapa intermediária de caminho de branch."""
        result = should_show_return_button(
            branch_manager=branch_manager,
            training_manager=training_manager,
            step_id="step_a1",
            module_id="mod1",
            path_id="path_a",
        )
        assert result is False

    def test_hides_button_on_main_path(
        self, branch_manager, training_manager, setup_branch_scenario
    ):
        """Não exibe botão no caminho principal (sem parent_branch_id)."""
        result = should_show_return_button(
            branch_manager=branch_manager,
            training_manager=training_manager,
            step_id="step_branch",
            module_id="mod1",
            path_id="path_main",
        )
        assert result is False

    def test_hides_button_when_path_id_is_none(
        self, branch_manager, training_manager, setup_branch_scenario
    ):
        """Não exibe botão se path_id é None."""
        result = should_show_return_button(
            branch_manager=branch_manager,
            training_manager=training_manager,
            step_id="step_0",
            module_id="mod1",
            path_id=None,
        )
        assert result is False

    def test_hides_button_for_nonexistent_path(
        self, branch_manager, training_manager, setup_branch_scenario
    ):
        """Não exibe botão para caminho inexistente."""
        result = should_show_return_button(
            branch_manager=branch_manager,
            training_manager=training_manager,
            step_id="step_a2",
            module_id="mod1",
            path_id="nonexistent_path",
        )
        assert result is False
