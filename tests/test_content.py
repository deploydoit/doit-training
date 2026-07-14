"""Testes unitários para o ContentManager.

Valida:
- create_module: criação de módulo com validação
- update_module: atualização preservando progresso
- delete_module: exclusão com confirmação e contagem de afetados
- create_step: criação de etapa com conteúdo
- publish_module: publicação com validação de completude
- validate_module: validação de etapas e ramificações
- Versionamento: migração de progresso dos usuários

Requirements: 6.1, 6.3, 6.4, 6.5, 6.6
"""

import pytest

from managers.content_manager import (
    ContentManager,
    DeleteResult,
    PublishResult,
    ValidationErrorItem,
)
from managers.errors import ModuleNotFoundError, ValidationError
from models.data_models import StepContent
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
def sample_module(content_manager):
    """Cria um módulo de exemplo para testes."""
    return content_manager.create_module(
        title="Módulo de Teste",
        description="Descrição do módulo de teste",
    )


class TestCreateModule:
    """Testes para ContentManager.create_module."""

    def test_create_module_success(self, content_manager):
        """Cria módulo com dados válidos."""
        module = content_manager.create_module(
            title="Novo Módulo",
            description="Descrição curta",
        )

        assert module.id is not None
        assert module.title == "Novo Módulo"
        assert module.description == "Descrição curta"
        assert module.status == ModuleStatus.DRAFT
        assert module.version == 1

    def test_create_module_trims_title(self, content_manager):
        """Cria módulo com título com espaços extras."""
        module = content_manager.create_module(
            title="  Título com Espaços  ",
            description="Descrição",
        )
        assert module.title == "Título com Espaços"

    def test_create_module_creates_main_path(self, content_manager, db):
        """Verifica que caminho principal é criado automaticamente."""
        module = content_manager.create_module(
            title="Módulo", description="Desc"
        )

        cursor = db.execute(
            "SELECT * FROM paths WHERE module_id = ? AND is_main = TRUE",
            (module.id,),
        )
        path = cursor.fetchone()
        assert path is not None
        assert path["name"] == "Caminho Principal"

    def test_create_module_empty_title_raises(self, content_manager):
        """Título vazio levanta ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            content_manager.create_module(title="", description="Descrição")
        assert "Título" in exc_info.value.errors[0]

    def test_create_module_description_over_150_raises(self, content_manager):
        """Descrição com mais de 150 caracteres levanta ValidationError."""
        long_desc = "A" * 151
        with pytest.raises(ValidationError) as exc_info:
            content_manager.create_module(title="Módulo", description=long_desc)
        assert "150 caracteres" in exc_info.value.errors[0]

    def test_create_module_description_exactly_150(self, content_manager):
        """Descrição com exatamente 150 caracteres é aceita."""
        desc = "A" * 150
        module = content_manager.create_module(title="Módulo", description=desc)
        assert module.description == desc


class TestUpdateModule:
    """Testes para ContentManager.update_module."""

    def test_update_title(self, content_manager, sample_module):
        """Atualiza título do módulo."""
        updated = content_manager.update_module(
            sample_module.id, title="Título Atualizado"
        )
        assert updated.title == "Título Atualizado"

    def test_update_description(self, content_manager, sample_module):
        """Atualiza descrição do módulo."""
        updated = content_manager.update_module(
            sample_module.id, description="Nova descrição"
        )
        assert updated.description == "Nova descrição"

    def test_update_nonexistent_module_raises(self, content_manager):
        """Atualizar módulo inexistente levanta ModuleNotFoundError."""
        with pytest.raises(ModuleNotFoundError):
            content_manager.update_module("inexistente", title="X")

    def test_update_empty_title_raises(self, content_manager, sample_module):
        """Atualizar com título vazio levanta ValidationError."""
        with pytest.raises(ValidationError):
            content_manager.update_module(sample_module.id, title="")

    def test_update_description_over_150_raises(self, content_manager, sample_module):
        """Atualizar com descrição > 150 levanta ValidationError."""
        with pytest.raises(ValidationError):
            content_manager.update_module(
                sample_module.id, description="B" * 151
            )

    def test_update_updates_timestamp(self, content_manager, sample_module):
        """Atualizar módulo altera updated_at."""
        updated = content_manager.update_module(
            sample_module.id, title="Novo Título"
        )
        assert updated.updated_at >= sample_module.updated_at


class TestDeleteModule:
    """Testes para ContentManager.delete_module."""

    def test_delete_module_without_users(self, content_manager, sample_module, db):
        """Exclui módulo sem usuários afetados."""
        result = content_manager.delete_module(sample_module.id)

        assert result.deleted is True
        assert result.affected_users == 0

        # Verificar que foi removido do banco
        cursor = db.execute(
            "SELECT id FROM modules WHERE id = ?", (sample_module.id,)
        )
        assert cursor.fetchone() is None

    def test_delete_module_with_users_requires_confirmation(
        self, content_manager, sample_module, db
    ):
        """Módulo com usuários requer confirmação antes de excluir."""
        # Criar um usuário com progresso
        _create_user_with_progress(db, sample_module.id)

        result = content_manager.delete_module(sample_module.id)

        assert result.deleted is False
        assert result.affected_users == 1
        assert result.requires_confirmation is True

    def test_delete_module_with_users_confirmed(
        self, content_manager, sample_module, db
    ):
        """Módulo com usuários é excluído quando confirmado."""
        _create_user_with_progress(db, sample_module.id)

        result = content_manager.delete_module(sample_module.id, confirm=True)

        assert result.deleted is True
        assert result.affected_users == 1

    def test_delete_nonexistent_module_raises(self, content_manager):
        """Excluir módulo inexistente levanta ModuleNotFoundError."""
        with pytest.raises(ModuleNotFoundError):
            content_manager.delete_module("inexistente")

    def test_delete_counts_distinct_users(self, content_manager, sample_module, db):
        """Conta corretamente usuários distintos afetados."""
        # Criar uma etapa para referenciar
        main_path_id = content_manager._get_main_path_id(sample_module.id)
        import uuid
        step_id = f"shared-step-{uuid.uuid4()}"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, sample_module.id, main_path_id, 0, "content"),
        )
        db.commit()

        # Criar 3 usuários com progresso, todos apontando para a mesma etapa
        for i in range(3):
            _create_user_with_progress(
                db, sample_module.id,
                user_suffix=str(i),
                step_id=step_id,
                path_id=main_path_id,
            )

        result = content_manager.delete_module(sample_module.id)

        assert result.affected_users == 3
        assert result.requires_confirmation is True


class TestCreateStep:
    """Testes para ContentManager.create_step."""

    def test_create_step_on_main_path(self, content_manager, sample_module):
        """Cria etapa no caminho principal."""
        content = StepContent(
            id="temp",
            step_id="temp",
            content_type=ContentType.TEXT,
            content_data="Conteúdo de teste",
            alt_text=None,
            order=0,
        )

        step = content_manager.create_step(
            module_id=sample_module.id,
            content=content,
            position=0,
        )

        assert step.id is not None
        assert step.module_id == sample_module.id
        assert step.position == 0
        assert step.step_type == StepType.CONTENT
        assert len(step.content) == 1
        assert step.content[0].content_data == "Conteúdo de teste"

    def test_create_step_specific_path(self, content_manager, sample_module, db):
        """Cria etapa em caminho específico."""
        # Criar caminho secundário
        path_id = "path-secundario"
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, NULL, ?, FALSE)",
            (path_id, sample_module.id, "Caminho Secundário"),
        )
        db.commit()

        content = StepContent(
            id="temp",
            step_id="temp",
            content_type=ContentType.IMAGE,
            content_data="https://example.com/image.png",
            alt_text="Uma imagem",
            order=0,
        )

        step = content_manager.create_step(
            module_id=sample_module.id,
            content=content,
            position=0,
            path_id=path_id,
        )

        assert step.path_id == path_id
        assert step.content[0].content_type == ContentType.IMAGE

    def test_create_step_duplicate_position_raises(
        self, content_manager, sample_module
    ):
        """Posição duplicada levanta ValidationError."""
        content = StepContent(
            id="temp",
            step_id="temp",
            content_type=ContentType.TEXT,
            content_data="Conteúdo 1",
            alt_text=None,
            order=0,
        )

        content_manager.create_step(
            module_id=sample_module.id, content=content, position=0
        )

        with pytest.raises(ValidationError) as exc_info:
            content_manager.create_step(
                module_id=sample_module.id, content=content, position=0
            )
        assert "posição" in exc_info.value.errors[0].lower() or "Posição" in exc_info.value.errors[0]

    def test_create_step_nonexistent_module_raises(self, content_manager):
        """Criar etapa em módulo inexistente levanta ModuleNotFoundError."""
        content = StepContent(
            id="temp",
            step_id="temp",
            content_type=ContentType.TEXT,
            content_data="Conteúdo",
            alt_text=None,
            order=0,
        )

        with pytest.raises(ModuleNotFoundError):
            content_manager.create_step(
                module_id="inexistente", content=content, position=0
            )


class TestValidateModule:
    """Testes para ContentManager.validate_module."""

    def test_validate_module_with_content_is_valid(
        self, content_manager, sample_module
    ):
        """Módulo com todas etapas tendo conteúdo é válido."""
        content = StepContent(
            id="temp",
            step_id="temp",
            content_type=ContentType.TEXT,
            content_data="Conteúdo",
            alt_text=None,
            order=0,
        )
        content_manager.create_step(
            module_id=sample_module.id, content=content, position=0
        )

        errors = content_manager.validate_module(sample_module.id)
        assert errors == []

    def test_validate_module_step_without_content(
        self, content_manager, sample_module, db
    ):
        """Etapa sem conteúdo gera erro de validação."""
        # Criar etapa diretamente sem conteúdo
        main_path_id = content_manager._get_main_path_id(sample_module.id)
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            ("step-vazio", sample_module.id, main_path_id, 0, "content"),
        )
        db.commit()

        errors = content_manager.validate_module(sample_module.id)
        assert len(errors) == 1
        assert errors[0].element_type == "step"
        assert "conteúdo" in errors[0].message.lower()

    def test_validate_module_branch_with_one_option(
        self, content_manager, sample_module, db
    ):
        """Ramificação com apenas 1 opção gera erro."""
        main_path_id = content_manager._get_main_path_id(sample_module.id)

        # Criar etapa do tipo branch com conteúdo
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            ("step-branch", sample_module.id, main_path_id, 0, "branch"),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            ("sc-1", "step-branch", "text", "Escolha um caminho", 0),
        )

        # Criar branch com apenas 1 opção
        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            ("branch-1", "step-branch"),
        )

        # Criar caminho para opção
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, ?, ?, FALSE)",
            ("path-opt-1", sample_module.id, "branch-1", "Opção 1"),
        )

        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
            "VALUES (?, ?, ?, ?, ?)",
            ("opt-1", "branch-1", "Opção Única", "path-opt-1", 0),
        )
        db.commit()

        errors = content_manager.validate_module(sample_module.id)
        branch_errors = [e for e in errors if e.element_type == "branch"]
        assert len(branch_errors) >= 1
        assert "mínimo 2" in branch_errors[0].message

    def test_validate_module_branch_label_too_long(
        self, content_manager, sample_module, db
    ):
        """Rótulo de opção com mais de 80 caracteres gera erro de validação."""
        main_path_id = content_manager._get_main_path_id(sample_module.id)

        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            ("step-branch2", sample_module.id, main_path_id, 0, "branch"),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            ("sc-2", "step-branch2", "text", "Escolha", 0),
        )
        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            ("branch-2", "step-branch2"),
        )

        # Criar 2 caminhos com label válido e inválido (> 80 chars)
        for i in range(2):
            path_id = f"path-b2-{i}"
            db.execute(
                "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
                "VALUES (?, ?, ?, ?, FALSE)",
                (path_id, sample_module.id, "branch-2", f"Path {i}"),
            )
            # First label > 80 chars (but DB allows up to 150)
            label = "A" * 81 if i == 0 else "Opção Válida"
            db.execute(
                "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"opt-b2-{i}", "branch-2", label, path_id, i),
            )
        db.commit()

        errors = content_manager.validate_module(sample_module.id)
        branch_errors = [e for e in errors if e.element_type == "branch"]
        assert any("máximo 80 caracteres" in e.message for e in branch_errors)

    def test_validate_nonexistent_module_raises(self, content_manager):
        """Validar módulo inexistente levanta ModuleNotFoundError."""
        with pytest.raises(ModuleNotFoundError):
            content_manager.validate_module("inexistente")


class TestPublishModule:
    """Testes para ContentManager.publish_module."""

    def test_publish_valid_module(self, content_manager, sample_module):
        """Publica módulo válido com sucesso."""
        # Criar etapa com conteúdo
        content = StepContent(
            id="temp",
            step_id="temp",
            content_type=ContentType.TEXT,
            content_data="Conteúdo da etapa",
            alt_text=None,
            order=0,
        )
        content_manager.create_step(
            module_id=sample_module.id, content=content, position=0
        )

        result = content_manager.publish_module(sample_module.id)

        assert result.published is True
        assert result.version == 2  # Incrementado de 1 para 2
        assert result.errors == []

    def test_publish_invalid_module_blocked(self, content_manager, sample_module, db):
        """Publicação bloqueada se módulo tem etapa sem conteúdo."""
        # Criar etapa sem conteúdo
        main_path_id = content_manager._get_main_path_id(sample_module.id)
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            ("step-empty", sample_module.id, main_path_id, 0, "content"),
        )
        db.commit()

        result = content_manager.publish_module(sample_module.id)

        assert result.published is False
        assert len(result.errors) > 0

    def test_publish_increments_version(self, content_manager, sample_module):
        """Cada publicação incrementa a versão."""
        content = StepContent(
            id="temp",
            step_id="temp",
            content_type=ContentType.TEXT,
            content_data="Conteúdo",
            alt_text=None,
            order=0,
        )
        content_manager.create_step(
            module_id=sample_module.id, content=content, position=0
        )

        result1 = content_manager.publish_module(sample_module.id)
        assert result1.version == 2

        result2 = content_manager.publish_module(sample_module.id)
        assert result2.version == 3

    def test_publish_nonexistent_module_raises(self, content_manager):
        """Publicar módulo inexistente levanta ModuleNotFoundError."""
        with pytest.raises(ModuleNotFoundError):
            content_manager.publish_module("inexistente")


class TestVersionMigration:
    """Testes para migração de progresso durante versionamento."""

    def test_migrate_preserves_valid_steps(self, content_manager, sample_module, db):
        """Migração preserva etapas concluídas que ainda existem."""
        # Criar etapa e conteúdo
        content = StepContent(
            id="temp",
            step_id="temp",
            content_type=ContentType.TEXT,
            content_data="Conteúdo",
            alt_text=None,
            order=0,
        )
        step = content_manager.create_step(
            module_id=sample_module.id, content=content, position=0
        )

        # Criar usuário com progresso na etapa
        _create_user_with_progress(
            db, sample_module.id, step_id=step.id, path_id=step.path_id
        )

        # Publicar (migra progresso)
        result = content_manager.publish_module(sample_module.id)

        assert result.published is True
        assert result.migrated_users == 1

        # Verificar que progresso mantém a mesma etapa (ainda válida)
        cursor = db.execute(
            "SELECT current_step_id FROM user_progress WHERE module_id = ?",
            (sample_module.id,),
        )
        progress = cursor.fetchone()
        assert progress["current_step_id"] == step.id


# --- Helpers ---


def _create_user_with_progress(
    db: Database,
    module_id: str,
    user_suffix: str = "0",
    step_id: str = None,
    path_id: str = None,
):
    """Helper para criar usuário com progresso em um módulo."""
    import uuid

    user_id = f"user-{user_suffix}"

    # Criar usuário (IGNORE se já existe)
    db.execute(
        "INSERT OR IGNORE INTO users (id, name, email) VALUES (?, ?, ?)",
        (user_id, f"User {user_suffix}", f"user{user_suffix}@test.com"),
    )

    # Se não temos step_id, criar uma etapa mínima
    if step_id is None:
        # Buscar main path
        cursor = db.execute(
            "SELECT id FROM paths WHERE module_id = ? AND is_main = TRUE",
            (module_id,),
        )
        path_row = cursor.fetchone()
        if path_row:
            path_id = path_row["id"]
        else:
            path_id = f"path-{uuid.uuid4()}"
            db.execute(
                "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
                "VALUES (?, ?, NULL, ?, TRUE)",
                (path_id, module_id, "Main"),
            )

        step_id = f"step-{uuid.uuid4()}"
        db.execute(
            "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, 0, "content"),
        )
        # Add content to step so it's valid
        db.execute(
            "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"sc-{uuid.uuid4()}", step_id, "text", "Content", 0),
        )

    # Criar progresso
    progress_id = f"progress-{uuid.uuid4()}"
    db.execute(
        "INSERT OR IGNORE INTO user_progress "
        "(id, user_id, module_id, current_step_id, current_path_id, status, percentage) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (progress_id, user_id, module_id, step_id, path_id, "in_progress", 50.0),
    )

    db.commit()
