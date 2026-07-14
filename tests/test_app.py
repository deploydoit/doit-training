"""Testes para app.py e SessionManager.

Verifica:
- Inicialização do session_state com valores padrão
- Roteamento entre páginas
- Controle de estado (get/set/clear)
- Integração dos managers com o banco de dados
- Layout responsivo (CSS injetado)

Requirements: 1.1, 1.2, 7.1, 7.2, 7.3
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from managers.session_manager import SessionManager, _DEFAULT_STATE
from models.data_models import UserProfile
from models.database import Database


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session_state():
    """Mock do st.session_state como dicionário."""
    state = {}
    with patch("managers.session_manager.st") as mock_st:
        mock_st.session_state = state
        yield state, mock_st


@pytest.fixture
def db():
    """Banco de dados em memória para testes."""
    database = Database(":memory:")
    database.initialize()
    return database


@pytest.fixture
def sample_user_profile():
    """Perfil de usuário de exemplo para testes."""
    return UserProfile(
        id="user-1",
        name="João Silva",
        email="joao@test.com",
        is_first_visit=False,
        is_admin=False,
        created_at=datetime.now(),
        last_login=datetime.now(),
    )


@pytest.fixture
def admin_user_profile():
    """Perfil de administrador para testes."""
    return UserProfile(
        id="admin-1",
        name="Admin User",
        email="admin@test.com",
        is_first_visit=False,
        is_admin=True,
        created_at=datetime.now(),
        last_login=datetime.now(),
    )


# ---------------------------------------------------------------------------
# Testes do SessionManager
# ---------------------------------------------------------------------------


class TestSessionManagerInitialize:
    """Testes de inicialização do session_state."""

    def test_initialize_creates_default_keys(self, mock_session_state):
        """Deve criar todas as chaves padrão no session_state."""
        state, _ = mock_session_state
        SessionManager.initialize()

        for key, value in _DEFAULT_STATE.items():
            assert key in state
            assert state[key] == value

    def test_initialize_preserves_existing_values(self, mock_session_state):
        """Deve preservar valores já existentes no session_state."""
        state, _ = mock_session_state
        state["current_page"] = "module_list"
        state["user_id"] = "existing-user"

        SessionManager.initialize()

        assert state["current_page"] == "module_list"
        assert state["user_id"] == "existing-user"

    def test_initialize_fills_missing_keys_only(self, mock_session_state):
        """Deve preencher apenas as chaves que faltam."""
        state, _ = mock_session_state
        state["current_page"] = "admin"

        SessionManager.initialize()

        assert state["current_page"] == "admin"
        assert state["user_profile"] is None
        assert state["selected_module_id"] is None


class TestSessionManagerPageRouting:
    """Testes de roteamento entre páginas."""

    def test_get_current_page_default(self, mock_session_state):
        """Deve retornar 'welcome' quando não há página definida."""
        state, _ = mock_session_state
        page = SessionManager.get_current_page()
        assert page == "welcome"

    def test_get_current_page_with_value(self, mock_session_state):
        """Deve retornar a página definida no state."""
        state, _ = mock_session_state
        state["current_page"] = "module_list"
        assert SessionManager.get_current_page() == "module_list"

    def test_set_current_page(self, mock_session_state):
        """Deve atualizar a página no state."""
        state, _ = mock_session_state
        SessionManager.set_current_page("step_view")
        assert state["current_page"] == "step_view"


class TestSessionManagerAuthentication:
    """Testes de autenticação e perfil do usuário."""

    def test_is_authenticated_false_when_no_profile(self, mock_session_state):
        """Deve retornar False quando não há perfil na sessão."""
        state, _ = mock_session_state
        assert SessionManager.is_authenticated() is False

    def test_is_authenticated_true_with_profile(
        self, mock_session_state, sample_user_profile
    ):
        """Deve retornar True quando há perfil na sessão."""
        state, _ = mock_session_state
        state["user_profile"] = sample_user_profile
        assert SessionManager.is_authenticated() is True

    def test_get_user_profile_none(self, mock_session_state):
        """Deve retornar None quando não há perfil."""
        state, _ = mock_session_state
        assert SessionManager.get_user_profile() is None

    def test_get_user_profile(self, mock_session_state, sample_user_profile):
        """Deve retornar o perfil correto."""
        state, _ = mock_session_state
        state["user_profile"] = sample_user_profile
        profile = SessionManager.get_user_profile()
        assert profile.id == "user-1"
        assert profile.name == "João Silva"

    def test_is_admin_false_for_regular_user(
        self, mock_session_state, sample_user_profile
    ):
        """Deve retornar False para usuário não-admin."""
        state, _ = mock_session_state
        state["user_profile"] = sample_user_profile
        assert SessionManager.is_admin() is False

    def test_is_admin_true_for_admin(
        self, mock_session_state, admin_user_profile
    ):
        """Deve retornar True para administrador."""
        state, _ = mock_session_state
        state["user_profile"] = admin_user_profile
        assert SessionManager.is_admin() is True

    def test_is_admin_false_when_no_profile(self, mock_session_state):
        """Deve retornar False quando não há perfil."""
        state, _ = mock_session_state
        assert SessionManager.is_admin() is False

    def test_get_user_id(self, mock_session_state):
        """Deve retornar o ID do usuário."""
        state, _ = mock_session_state
        state["user_id"] = "user-123"
        assert SessionManager.get_user_id() == "user-123"


class TestSessionManagerNavigationState:
    """Testes de estado de navegação (módulo, etapa, caminho)."""

    def test_get_selected_module_id(self, mock_session_state):
        """Deve retornar o ID do módulo selecionado."""
        state, _ = mock_session_state
        state["selected_module_id"] = "module-1"
        assert SessionManager.get_selected_module_id() == "module-1"

    def test_get_current_step_id(self, mock_session_state):
        """Deve retornar o ID da etapa atual."""
        state, _ = mock_session_state
        state["current_step_id"] = "step-5"
        assert SessionManager.get_current_step_id() == "step-5"

    def test_get_current_path_id(self, mock_session_state):
        """Deve retornar o ID do caminho atual."""
        state, _ = mock_session_state
        state["current_path_id"] = "path-2"
        assert SessionManager.get_current_path_id() == "path-2"

    def test_should_resume_module_default_false(self, mock_session_state):
        """Deve retornar False por padrão."""
        state, _ = mock_session_state
        assert SessionManager.should_resume_module() is False

    def test_should_resume_module_true(self, mock_session_state):
        """Deve retornar True quando flag está ativa."""
        state, _ = mock_session_state
        state["resume_module"] = True
        assert SessionManager.should_resume_module() is True

    def test_clear_navigation_state(self, mock_session_state):
        """Deve limpar todo o estado de navegação."""
        state, _ = mock_session_state
        state["selected_module_id"] = "module-1"
        state["current_step_id"] = "step-5"
        state["current_path_id"] = "path-2"
        state["branch_source_step_id"] = "branch-step"
        state["resume_module"] = True
        state["module_completed"] = True

        SessionManager.clear_navigation_state()

        assert state["selected_module_id"] is None
        assert state["current_step_id"] is None
        assert state["current_path_id"] is None
        assert state["branch_source_step_id"] is None
        assert state["resume_module"] is False
        assert state["module_completed"] is False

    def test_logout_resets_all_state(self, mock_session_state, sample_user_profile):
        """Deve resetar todo o estado ao fazer logout."""
        state, _ = mock_session_state
        state["user_profile"] = sample_user_profile
        state["user_id"] = "user-1"
        state["current_page"] = "module_list"
        state["selected_module_id"] = "module-1"

        SessionManager.logout()

        assert state["user_profile"] is None
        assert state["user_id"] is None
        assert state["current_page"] == "welcome"
        assert state["selected_module_id"] is None


# ---------------------------------------------------------------------------
# Testes de integração dos managers
# ---------------------------------------------------------------------------


class TestManagersIntegration:
    """Testes de integração dos managers com o banco de dados."""

    def test_all_managers_connect_to_same_db(self, db):
        """Todos os managers devem compartilhar a mesma instância do DB."""
        from managers.branch_manager import BranchManager
        from managers.content_manager import ContentManager
        from managers.progress_manager import ProgressManager
        from managers.training_manager import TrainingManager

        progress_mgr = ProgressManager(db)
        branch_mgr = BranchManager(db)
        training_mgr = TrainingManager(db)
        content_mgr = ContentManager(db, media_path="media")

        assert progress_mgr.db is db
        assert branch_mgr.db is db
        assert training_mgr.db is db
        assert content_mgr.db is db

    def test_training_manager_returns_empty_for_no_modules(self, db):
        """TrainingManager deve retornar lista vazia sem módulos."""
        from managers.training_manager import TrainingManager

        tm = TrainingManager(db)
        modules = tm.get_modules("user-1")
        assert modules == []


# ---------------------------------------------------------------------------
# Testes de roteamento de app.py
# ---------------------------------------------------------------------------


class TestAppRouting:
    """Testes de roteamento da aplicação principal."""

    def test_app_imports_correctly(self):
        """O módulo app deve ser importável sem erros de sintaxe."""
        import ast

        with open("/Users/IsaSoares/Desktop/Kiro/doit-training/app.py") as f:
            tree = ast.parse(f.read())
        assert len(tree.body) > 0

    def test_responsive_css_contains_breakpoints(self):
        """O CSS responsivo deve conter os breakpoints corretos."""
        import ast

        with open("/Users/IsaSoares/Desktop/Kiro/doit-training/app.py") as f:
            source = f.read()

        # Verificar breakpoints
        assert "1025px" in source or "1024px" in source  # Desktop
        assert "601px" in source  # Tablet lower bound
        assert "1024px" in source  # Tablet upper bound
        assert "600px" in source  # Mobile

    def test_responsive_css_contains_min_button_size(self):
        """O CSS responsivo deve definir tamanho mínimo de 44px para botões."""
        with open("/Users/IsaSoares/Desktop/Kiro/doit-training/app.py") as f:
            source = f.read()

        assert "min-height: 44px" in source
        assert "min-width: 44px" in source

    def test_responsive_css_contains_spacing(self):
        """O CSS responsivo deve definir espaçamento de 8px entre elementos."""
        with open("/Users/IsaSoares/Desktop/Kiro/doit-training/app.py") as f:
            source = f.read()

        assert "8px" in source
