"""Testes unitários para a página de publicação de módulos (admin_publish.py).

Valida:
- Validação prévia bloqueia publicação com erros
- Publicação bem-sucedida incrementa versão
- Migração de progresso dos usuários na publicação
- Exibição correta de erros de validação por tipo

Requirements: 6.4, 6.5
"""

import uuid

import pytest

from managers.content_manager import ContentManager, PublishResult, ValidationErrorItem
from models.database import Database
from models.enums import ContentType, ModuleStatus, StepType


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
def valid_module(content_manager, db):
    """Cria um módulo válido pronto para publicação (com etapa e conteúdo)."""
    from models.data_models import StepContent

    module = content_manager.create_module(
        title="Módulo Publicável",
        description="Módulo pronto para ser publicado",
    )
    # Criar uma etapa com conteúdo no caminho principal
    main_path_id = content_manager._get_main_path_id(module.id)
    step_content = StepContent(
        id="",
        step_id="",
        content_type=ContentType.TEXT,
        content_data="Conteúdo de exemplo",
        alt_text=None,
        order=0,
    )
    content_manager.create_step(
        module_id=module.id,
        content=step_content,
        position=0,
        path_id=main_path_id,
        step_type=StepType.CONTENT,
    )
    return module


@pytest.fixture
def invalid_module_no_content(content_manager, db):
    """Cria um módulo inválido: etapa sem conteúdo."""
    module = content_manager.create_module(
        title="Módulo Inválido",
        description="Módulo com etapa sem conteúdo",
    )
    # Criar etapa diretamente no banco sem conteúdo
    main_path_id = content_manager._get_main_path_id(module.id)
    step_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        (step_id, module.id, main_path_id, 0, "content"),
    )
    db.commit()
    return module


class TestPublishValidation:
    """Testes de validação prévia à publicação.

    Requirements: 6.5
    """

    def test_validate_valid_module_returns_no_errors(self, content_manager, valid_module):
        """Módulo válido passa na validação sem erros."""
        errors = content_manager.validate_module(valid_module.id)
        assert errors == []

    def test_validate_module_step_without_content(
        self, content_manager, invalid_module_no_content
    ):
        """Módulo com etapa sem conteúdo retorna erro de validação."""
        errors = content_manager.validate_module(invalid_module_no_content.id)
        assert len(errors) > 0
        assert any(e.element_type == "step" for e in errors)
        assert any("conteúdo" in e.message.lower() for e in errors)

    def test_validate_module_branch_with_fewer_than_2_options(
        self, content_manager, db
    ):
        """Ramificação com menos de 2 opções bloqueia publicação."""
        module = content_manager.create_module(
            title="Módulo Branch Inválido",
            description="Teste de branch inválido",
        )
        main_path_id = content_manager._get_main_path_id(module.id)

        # Criar etapa do tipo branch
        step_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module.id, main_path_id, 0, "branch"),
        )
        # Criar conteúdo para a etapa
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), step_id, "text", "Branch content", 0),
        )
        # Criar branch com apenas 1 opção
        branch_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            (branch_id, step_id),
        )
        option_path_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, ?, ?, FALSE)",
            (option_path_id, module.id, branch_id, "Caminho Único"),
        )
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), branch_id, "Opção única", option_path_id, 0),
        )
        db.commit()

        errors = content_manager.validate_module(module.id)
        assert len(errors) > 0
        assert any(e.element_type == "branch" for e in errors)
        assert any("2" in e.message for e in errors)


class TestPublishModule:
    """Testes de publicação de módulo.

    Requirements: 6.4, 6.5
    """

    def test_publish_valid_module_succeeds(self, content_manager, valid_module):
        """Módulo válido é publicado com sucesso."""
        result = content_manager.publish_module(valid_module.id)
        assert result.published is True
        assert result.version == 2  # Incrementa de 1 para 2
        assert result.errors == []

    def test_publish_increments_version(self, content_manager, valid_module, db):
        """Publicação incrementa a versão no banco de dados."""
        content_manager.publish_module(valid_module.id)

        cursor = db.execute(
            "SELECT version, status FROM modules WHERE id = ?",
            (valid_module.id,),
        )
        row = cursor.fetchone()
        assert row["version"] == 2
        assert row["status"] == ModuleStatus.PUBLISHED.value

    def test_publish_invalid_module_blocked(
        self, content_manager, invalid_module_no_content
    ):
        """Publicação de módulo inválido é bloqueada com erros."""
        result = content_manager.publish_module(invalid_module_no_content.id)
        assert result.published is False
        assert len(result.errors) > 0

    def test_publish_nonexistent_module_raises(self, content_manager):
        """Publicação de módulo inexistente levanta exceção."""
        from managers.errors import ModuleNotFoundError

        with pytest.raises(ModuleNotFoundError):
            content_manager.publish_module("inexistente")

    def test_publish_migrates_user_progress(self, content_manager, valid_module, db):
        """Publicação migra progresso dos usuários existentes."""
        # Criar um usuário com progresso
        main_path_id = content_manager._get_main_path_id(valid_module.id)
        cursor = db.execute(
            "SELECT id FROM steps WHERE module_id = ? AND path_id = ? LIMIT 1",
            (valid_module.id, main_path_id),
        )
        step_row = cursor.fetchone()
        step_id = step_row["id"]

        user_id = f"user-{uuid.uuid4()}"
        db.execute(
            "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
            (user_id, "Test User", f"test_{uuid.uuid4()}@test.com"),
        )
        progress_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO user_progress "
            "(id, user_id, module_id, current_step_id, current_path_id, status, percentage) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (progress_id, user_id, valid_module.id, step_id, main_path_id, "in_progress", 50.0),
        )
        db.commit()

        result = content_manager.publish_module(valid_module.id)
        assert result.published is True
        assert result.migrated_users == 1


class TestAdminPublishHelpers:
    """Testes para funções auxiliares de admin_publish.py."""

    def test_get_status_label_draft(self):
        """Status draft exibe rótulo correto."""
        from pages.admin_publish import _get_status_label

        label = _get_status_label("draft")
        assert "Rascunho" in label

    def test_get_status_label_published(self):
        """Status published exibe rótulo correto."""
        from pages.admin_publish import _get_status_label

        label = _get_status_label("published")
        assert "Publicado" in label

    def test_get_status_label_archived(self):
        """Status archived exibe rótulo correto."""
        from pages.admin_publish import _get_status_label

        label = _get_status_label("archived")
        assert "Arquivado" in label

    def test_get_status_label_unknown(self):
        """Status desconhecido retorna o valor original."""
        from pages.admin_publish import _get_status_label

        label = _get_status_label("unknown_status")
        assert label == "unknown_status"
