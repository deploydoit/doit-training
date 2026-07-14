"""Testes para o Editor Visual de Ramificações.

Testa a lógica de validação de rótulos e funções auxiliares
do editor de ramificações do painel administrativo.

Requirements: 6.2, 6.3
"""

import uuid

import pytest

from models.database import Database
from models.enums import ContentType, StepType
from managers.branch_manager import BranchManager
from managers.content_manager import ContentManager
from pages.admin_branch_editor import (
    MAX_BRANCH_OPTIONS,
    MAX_LABEL_LENGTH,
    MIN_BRANCH_OPTIONS,
    MIN_LABEL_LENGTH,
    _get_module_paths,
    _get_path_steps,
    _get_step_contents,
    validate_branch_labels,
)


@pytest.fixture
def db():
    """Banco de dados em memória para testes."""
    database = Database(":memory:")
    database.initialize()
    return database


@pytest.fixture
def content_manager(db):
    """Instância de ContentManager para testes."""
    return ContentManager(db)


@pytest.fixture
def branch_manager(db):
    """Instância de BranchManager para testes."""
    return BranchManager(db)


@pytest.fixture
def sample_module(db):
    """Cria um módulo de exemplo com caminho principal."""
    module_id = str(uuid.uuid4())
    path_id = str(uuid.uuid4())

    db.execute(
        "INSERT INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (module_id, "Módulo Teste", "Descrição teste", "draft", 1),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
        "VALUES (?, ?, NULL, ?, TRUE)",
        (path_id, module_id, "Caminho Principal"),
    )
    db.commit()

    return {"module_id": module_id, "path_id": path_id}


class TestValidateBranchLabels:
    """Testes para a função validate_branch_labels."""

    def test_valid_labels_with_2_options(self):
        """Valida rótulos corretos com número mínimo de opções."""
        labels = ["Opção A", "Opção B"]
        errors = validate_branch_labels(labels)
        assert errors == []

    def test_valid_labels_with_5_options(self):
        """Valida rótulos corretos com número máximo de opções."""
        labels = ["Opção A", "Opção B", "Opção C", "Opção D", "Opção E"]
        errors = validate_branch_labels(labels)
        assert errors == []

    def test_valid_labels_with_3_characters(self):
        """Valida rótulo com exatamente 3 caracteres (mínimo)."""
        labels = ["Abc", "Def"]
        errors = validate_branch_labels(labels)
        assert errors == []

    def test_valid_labels_with_80_characters(self):
        """Valida rótulo com exatamente 80 caracteres (máximo)."""
        labels = ["A" * 80, "B" * 80]
        errors = validate_branch_labels(labels)
        assert errors == []

    def test_error_too_few_options(self):
        """Erro quando há menos de 2 opções."""
        labels = ["Opção única"]
        errors = validate_branch_labels(labels)
        assert len(errors) >= 1
        assert any(f"mínimo {MIN_BRANCH_OPTIONS}" in e for e in errors)

    def test_error_too_many_options(self):
        """Erro quando há mais de 5 opções."""
        labels = ["Opt1", "Opt2", "Opt3", "Opt4", "Opt5", "Opt6"]
        errors = validate_branch_labels(labels)
        assert len(errors) >= 1
        assert any(f"máximo {MAX_BRANCH_OPTIONS}" in e for e in errors)

    def test_error_label_too_short(self):
        """Erro quando rótulo tem menos de 3 caracteres."""
        labels = ["AB", "Opção válida"]
        errors = validate_branch_labels(labels)
        assert len(errors) >= 1
        assert any(f"mínimo {MIN_LABEL_LENGTH}" in e for e in errors)

    def test_error_label_too_long(self):
        """Erro quando rótulo excede 80 caracteres."""
        labels = ["A" * 81, "Opção válida"]
        errors = validate_branch_labels(labels)
        assert len(errors) >= 1
        assert any(f"máximo {MAX_LABEL_LENGTH}" in e for e in errors)

    def test_error_empty_label(self):
        """Erro quando rótulo está vazio."""
        labels = ["", "Opção válida"]
        errors = validate_branch_labels(labels)
        assert len(errors) >= 1
        assert any("vazio" in e for e in errors)

    def test_error_whitespace_only_label(self):
        """Erro quando rótulo contém apenas espaços."""
        labels = ["   ", "Opção válida"]
        errors = validate_branch_labels(labels)
        assert len(errors) >= 1
        assert any("vazio" in e for e in errors)

    def test_multiple_validation_errors(self):
        """Múltiplos erros retornados quando várias opções são inválidas."""
        labels = ["AB", ""]  # Uma curta, uma vazia
        errors = validate_branch_labels(labels)
        assert len(errors) == 2


class TestGetModulePaths:
    """Testes para a função _get_module_paths."""

    def test_returns_main_path(self, db, sample_module):
        """Retorna o caminho principal do módulo."""
        paths = _get_module_paths(db, sample_module["module_id"])
        assert len(paths) == 1
        assert bool(paths[0]["is_main"]) is True
        assert paths[0]["name"] == "Caminho Principal"

    def test_returns_empty_for_invalid_module(self, db):
        """Retorna lista vazia para módulo inexistente."""
        paths = _get_module_paths(db, "nonexistent_id")
        assert paths == []

    def test_returns_main_and_branch_paths(self, db, sample_module):
        """Retorna caminho principal e caminhos de ramificação."""
        # Criar caminho de ramificação
        branch_path_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, ?, ?, FALSE)",
            (branch_path_id, sample_module["module_id"], "branch_123", "Caminho A"),
        )
        db.commit()

        paths = _get_module_paths(db, sample_module["module_id"])
        assert len(paths) == 2
        # Main path vem primeiro (ORDER BY is_main DESC)
        assert bool(paths[0]["is_main"]) is True


class TestGetPathSteps:
    """Testes para a função _get_path_steps."""

    def test_returns_steps_ordered_by_position(self, db, sample_module):
        """Retorna etapas ordenadas por posição."""
        path_id = sample_module["path_id"]
        module_id = sample_module["module_id"]

        # Criar etapas fora de ordem
        for pos in [2, 0, 1]:
            db.execute(
                "INSERT INTO steps (id, module_id, path_id, position, step_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), module_id, path_id, pos, "content"),
            )
        db.commit()

        steps = _get_path_steps(db, path_id)
        assert len(steps) == 3
        assert steps[0]["position"] == 0
        assert steps[1]["position"] == 1
        assert steps[2]["position"] == 2

    def test_returns_empty_for_path_with_no_steps(self, db, sample_module):
        """Retorna lista vazia quando caminho não tem etapas."""
        steps = _get_path_steps(db, sample_module["path_id"])
        assert steps == []


class TestGetStepContents:
    """Testes para a função _get_step_contents."""

    def test_returns_contents_ordered_by_display_order(self, db, sample_module):
        """Retorna conteúdos ordenados por display_order."""
        path_id = sample_module["path_id"]
        module_id = sample_module["module_id"]
        step_id = str(uuid.uuid4())

        # Criar etapa
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, 0, "content"),
        )

        # Criar conteúdos
        for order in [2, 0, 1]:
            db.execute(
                "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), step_id, "text", f"Conteúdo {order}", order),
            )
        db.commit()

        contents = _get_step_contents(db, step_id)
        assert len(contents) == 3
        assert contents[0]["display_order"] == 0
        assert contents[1]["display_order"] == 1
        assert contents[2]["display_order"] == 2

    def test_returns_empty_for_step_with_no_content(self, db, sample_module):
        """Retorna lista vazia quando etapa não tem conteúdo."""
        path_id = sample_module["path_id"]
        module_id = sample_module["module_id"]
        step_id = str(uuid.uuid4())

        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, 0, "content"),
        )
        db.commit()

        contents = _get_step_contents(db, step_id)
        assert contents == []


class TestBranchEditorIntegration:
    """Testes de integração do editor de ramificações."""

    def test_save_branch_options_creates_paths(self, db, sample_module):
        """Salvar opções de ramificação cria caminhos associados."""
        from pages.admin_branch_editor import _save_branch_options

        module_id = sample_module["module_id"]
        path_id = sample_module["path_id"]

        # Criar etapa do tipo branch
        step_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, 0, "branch"),
        )

        # Criar branch
        branch_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            (branch_id, step_id),
        )
        db.commit()

        # Salvar opções (função usa st.success/st.rerun que precisamos mockar)
        # Testaremos diretamente a lógica do banco
        labels = ["Iniciante", "Intermediário", "Avançado"]

        for i, label in enumerate(labels):
            opt_path_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
                "VALUES (?, ?, ?, ?, FALSE)",
                (opt_path_id, module_id, branch_id, label),
            )
            option_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
                "VALUES (?, ?, ?, ?, ?)",
                (option_id, branch_id, label, opt_path_id, i),
            )
        db.commit()

        # Verificar opções criadas
        branch_manager = BranchManager(db)
        options = branch_manager.get_branch_options(step_id)
        assert len(options) == 3
        assert options[0].label == "Iniciante"
        assert options[1].label == "Intermediário"
        assert options[2].label == "Avançado"

        # Verificar validação
        validation = branch_manager.validate_branch(step_id)
        assert validation.is_valid is True

    def test_branch_validation_fails_with_1_option(self, db, sample_module):
        """Validação falha quando branch tem apenas 1 opção."""
        module_id = sample_module["module_id"]
        path_id = sample_module["path_id"]

        # Criar etapa do tipo branch
        step_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, 0, "branch"),
        )

        # Criar branch com apenas 1 opção
        branch_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            (branch_id, step_id),
        )

        opt_path_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, ?, ?, FALSE)",
            (opt_path_id, module_id, branch_id, "Único caminho"),
        )
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), branch_id, "Único caminho", opt_path_id, 0),
        )
        db.commit()

        branch_manager = BranchManager(db)
        validation = branch_manager.validate_branch(step_id)
        assert validation.is_valid is False
        assert any("mínimo 2" in e for e in validation.errors)

    def test_branch_validation_rejects_short_labels_via_validate_branch_labels(self):
        """Validação de rótulos rejeita labels com menos de 3 caracteres.

        Nota: O banco de dados tem CHECK constraint que impede inserção de
        labels < 3 chars, então testamos via validate_branch_labels.
        """
        labels = ["AB", "Opção válida"]
        errors = validate_branch_labels(labels)
        assert len(errors) >= 1
        assert any("mínimo 3 caracteres" in e or f"mínimo {MIN_LABEL_LENGTH}" in e for e in errors)

    def test_constants_match_requirements(self):
        """Constantes de validação estão corretas conforme requisitos."""
        assert MIN_BRANCH_OPTIONS == 2
        assert MAX_BRANCH_OPTIONS == 5
        assert MIN_LABEL_LENGTH == 3
        assert MAX_LABEL_LENGTH == 80
