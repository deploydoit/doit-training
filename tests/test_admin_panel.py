"""Testes unitários para o painel administrativo (admin_panel.py).

Valida:
- Listagem de módulos existentes
- Criação de módulos via interface
- Edição de módulos existentes
- Exclusão com confirmação explícita e contagem de usuários afetados

Requirements: 6.1, 6.6
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from managers.content_manager import ContentManager
from models.database import Database


@pytest.fixture
def db():
    """Banco de dados em memória para testes."""
    database = Database(":memory:")
    database.initialize()
    yield database
    database.close()


@pytest.fixture
def content_manager(db):
    """Instância de ContentManager para testes."""
    return ContentManager(db, media_path="media")


@pytest.fixture
def sample_module(content_manager):
    """Cria um módulo de exemplo."""
    return content_manager.create_module(
        title="Módulo Admin Teste",
        description="Descrição do módulo para teste admin",
    )


class TestAdminPanelHelpers:
    """Testes para funções auxiliares do admin_panel."""

    def test_get_all_modules_empty(self, db):
        """Retorna lista vazia quando não há módulos."""
        from pages.admin_panel import _get_all_modules

        modules = _get_all_modules(db)
        assert modules == []

    def test_get_all_modules_returns_existing(self, db, content_manager):
        """Retorna módulos existentes no banco."""
        from pages.admin_panel import _get_all_modules

        content_manager.create_module(title="Mod 1", description="Desc 1")
        content_manager.create_module(title="Mod 2", description="Desc 2")

        modules = _get_all_modules(db)
        assert len(modules) == 2
        titles = {m["title"] for m in modules}
        assert "Mod 1" in titles
        assert "Mod 2" in titles

    def test_get_all_modules_includes_all_fields(self, db, content_manager):
        """Retorna todos os campos necessários de cada módulo."""
        from pages.admin_panel import _get_all_modules

        content_manager.create_module(title="Completo", description="Desc completa")

        modules = _get_all_modules(db)
        module = modules[0]
        assert "id" in module
        assert "title" in module
        assert "description" in module
        assert "status" in module
        assert "version" in module
        assert "created_at" in module
        assert "updated_at" in module

    def test_get_status_icon_draft(self):
        """Ícone correto para status draft."""
        from pages.admin_panel import _get_status_icon

        assert _get_status_icon("draft") == "📝"

    def test_get_status_icon_published(self):
        """Ícone correto para status published."""
        from pages.admin_panel import _get_status_icon

        assert _get_status_icon("published") == "✅"

    def test_get_status_icon_archived(self):
        """Ícone correto para status archived."""
        from pages.admin_panel import _get_status_icon

        assert _get_status_icon("archived") == "📦"

    def test_get_status_icon_unknown(self):
        """Ícone padrão para status desconhecido."""
        from pages.admin_panel import _get_status_icon

        assert _get_status_icon("unknown") == "❓"


class TestAdminCreateModule:
    """Testes para a lógica de criação de módulos no admin panel."""

    def test_create_module_success(self, content_manager):
        """Cria módulo com dados válidos via ContentManager."""
        module = content_manager.create_module(
            title="Módulo Criado",
            description="Criado pelo admin",
        )
        assert module.title == "Módulo Criado"
        assert module.description == "Criado pelo admin"

    def test_create_module_empty_title_fails(self, content_manager):
        """Falha ao criar módulo sem título."""
        from managers.errors import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            content_manager.create_module(title="", description="Desc")
        assert "Título" in exc_info.value.errors[0]

    def test_create_module_description_too_long_fails(self, content_manager):
        """Falha ao criar módulo com descrição > 150 caracteres."""
        from managers.errors import ValidationError

        with pytest.raises(ValidationError):
            content_manager.create_module(
                title="Módulo", description="X" * 151
            )


class TestAdminEditModule:
    """Testes para a lógica de edição de módulos no admin panel."""

    def test_edit_module_title(self, content_manager, sample_module):
        """Edita título do módulo com sucesso."""
        updated = content_manager.update_module(
            sample_module.id, title="Título Editado"
        )
        assert updated.title == "Título Editado"

    def test_edit_module_description(self, content_manager, sample_module):
        """Edita descrição do módulo com sucesso."""
        updated = content_manager.update_module(
            sample_module.id, description="Nova desc"
        )
        assert updated.description == "Nova desc"

    def test_edit_preserves_unmodified_fields(self, content_manager, sample_module):
        """Editar um campo não altera outros campos."""
        updated = content_manager.update_module(
            sample_module.id, title="Só Título"
        )
        assert updated.description == sample_module.description


class TestAdminDeleteModule:
    """Testes para a lógica de exclusão de módulos no admin panel.

    Requirements: 6.1, 6.6
    """

    def test_delete_module_without_progress(self, content_manager, sample_module, db):
        """Exclusão de módulo sem usuários afetados procede diretamente."""
        # Primeiro check: sem confirmação retorna info
        result = content_manager.delete_module(sample_module.id, confirm=False)
        assert result.deleted is True  # Sem usuários, exclui direto
        assert result.affected_users == 0

    def test_delete_module_with_progress_requires_confirmation(
        self, content_manager, sample_module, db
    ):
        """Módulo com progresso exige confirmação antes de excluir (Req 6.6)."""
        _create_user_with_progress(db, sample_module.id)

        result = content_manager.delete_module(sample_module.id, confirm=False)
        assert result.deleted is False
        assert result.requires_confirmation is True
        assert result.affected_users == 1

    def test_delete_module_shows_affected_user_count(
        self, content_manager, sample_module, db
    ):
        """Exibe quantidade correta de usuários afetados (Req 6.6)."""
        # Criar 3 usuários com progresso
        for i in range(3):
            _create_user_with_progress(db, sample_module.id, user_suffix=str(i))

        result = content_manager.delete_module(sample_module.id, confirm=False)
        assert result.affected_users == 3
        assert result.requires_confirmation is True

    def test_delete_module_confirmed_succeeds(
        self, content_manager, sample_module, db
    ):
        """Exclusão com confirmação explícita remove o módulo (Req 6.1)."""
        _create_user_with_progress(db, sample_module.id)

        result = content_manager.delete_module(sample_module.id, confirm=True)
        assert result.deleted is True
        assert result.affected_users == 1

        # Verificar que módulo foi removido
        cursor = db.execute(
            "SELECT id FROM modules WHERE id = ?", (sample_module.id,)
        )
        assert cursor.fetchone() is None

    def test_delete_nonexistent_module_raises(self, content_manager):
        """Exclusão de módulo inexistente levanta erro."""
        from managers.errors import ModuleNotFoundError

        with pytest.raises(ModuleNotFoundError):
            content_manager.delete_module("inexistente")


# --- Helpers ---


def _create_user_with_progress(
    db: Database,
    module_id: str,
    user_suffix: str = "0",
):
    """Helper para criar usuário com progresso em um módulo."""
    user_id = f"admin-test-user-{user_suffix}"

    # Criar usuário
    db.execute(
        "INSERT OR IGNORE INTO users (id, name, email) VALUES (?, ?, ?)",
        (user_id, f"User {user_suffix}", f"admin_test_{user_suffix}@test.com"),
    )

    # Buscar main path
    cursor = db.execute(
        "SELECT id FROM paths WHERE module_id = ? AND is_main = TRUE",
        (module_id,),
    )
    path_row = cursor.fetchone()
    path_id = path_row["id"] if path_row else f"path-{uuid.uuid4()}"

    if not path_row:
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, NULL, ?, TRUE)",
            (path_id, module_id, "Main"),
        )

    # Buscar etapa existente no caminho, ou criar uma nova com posição única
    cursor = db.execute(
        "SELECT id FROM steps WHERE path_id = ? LIMIT 1",
        (path_id,),
    )
    existing_step = cursor.fetchone()

    if existing_step:
        step_id = existing_step["id"]
    else:
        step_id = f"step-admin-{uuid.uuid4()}"
        # Encontrar próxima posição disponível
        cursor = db.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM steps WHERE path_id = ?",
            (path_id,),
        )
        next_pos = cursor.fetchone()["next_pos"]
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, next_pos, "content"),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"sc-{uuid.uuid4()}", step_id, "text", "Content", 0),
        )

    # Criar progresso
    progress_id = f"progress-admin-{uuid.uuid4()}"
    db.execute(
        "INSERT OR IGNORE INTO user_progress "
        "(id, user_id, module_id, current_step_id, current_path_id, status, percentage) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (progress_id, user_id, module_id, step_id, path_id, "in_progress", 50.0),
    )

    db.commit()
