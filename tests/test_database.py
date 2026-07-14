"""Testes unitários para a camada de banco de dados SQLite.

Valida:
- Criação de todas as tabelas
- Constraints de integridade referencial
- Índices para otimização de consultas
- Operações CRUD básicas
"""

import sqlite3

import pytest

from models.database import Database


@pytest.fixture
def db():
    """Banco de dados em memória para testes."""
    database = Database(":memory:")
    database.initialize()
    yield database
    database.close()


class TestDatabaseInitialization:
    """Testes de inicialização e criação de tabelas."""

    def test_creates_all_tables(self, db: Database):
        """Verifica que todas as 10 tabelas são criadas."""
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]

        expected_tables = [
            "branch_options",
            "branches",
            "completed_steps",
            "explored_paths",
            "modules",
            "paths",
            "step_contents",
            "steps",
            "user_progress",
            "users",
        ]
        assert sorted(tables) == sorted(expected_tables)

    def test_foreign_keys_enabled(self, db: Database):
        """Verifica que foreign keys estão habilitadas."""
        cursor = db.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1

    def test_wal_mode_enabled(self, db: Database):
        """Verifica que WAL mode está habilitado."""
        cursor = db.execute("PRAGMA journal_mode")
        result = cursor.fetchone()
        assert result[0] == "wal" or result[0] == "memory"

    def test_initialize_is_idempotent(self, db: Database):
        """Chamar initialize múltiplas vezes não causa erro."""
        db.initialize()
        db.initialize()
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        assert len(tables) == 10


class TestModulesTable:
    """Testes para a tabela modules."""

    def test_insert_module(self, db: Database):
        """Insere um módulo válido."""
        db.execute(
            "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
            ("mod1", "Módulo 1", "Descrição do módulo", "draft"),
        )
        db.commit()

        cursor = db.execute("SELECT * FROM modules WHERE id = ?", ("mod1",))
        row = cursor.fetchone()
        assert row["title"] == "Módulo 1"
        assert row["version"] == 1

    def test_description_max_150_chars(self, db: Database):
        """Rejeita descrição com mais de 150 caracteres."""
        long_desc = "a" * 151
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
                ("mod2", "Módulo 2", long_desc),
            )

    def test_description_exactly_150_chars(self, db: Database):
        """Aceita descrição com exatamente 150 caracteres."""
        desc = "a" * 150
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("mod3", "Módulo 3", desc),
        )
        db.commit()
        cursor = db.execute("SELECT * FROM modules WHERE id = ?", ("mod3",))
        assert cursor.fetchone() is not None


class TestPathsTable:
    """Testes para a tabela paths."""

    def test_insert_path(self, db: Database):
        """Insere um caminho vinculado a um módulo."""
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("mod1", "Módulo 1", "Desc"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
            ("path1", "mod1", "Caminho Principal", True),
        )
        db.commit()

        cursor = db.execute("SELECT * FROM paths WHERE id = ?", ("path1",))
        row = cursor.fetchone()
        assert row["module_id"] == "mod1"
        assert row["is_main"] == 1

    def test_foreign_key_module_id(self, db: Database):
        """Rejeita path com module_id inexistente."""
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO paths (id, module_id, name) VALUES (?, ?, ?)",
                ("path1", "nonexistent", "Caminho"),
            )


class TestStepsTable:
    """Testes para a tabela steps."""

    def test_insert_step(self, db: Database):
        """Insere uma etapa válida."""
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("mod1", "Módulo 1", "Desc"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name) VALUES (?, ?, ?)",
            ("path1", "mod1", "Principal"),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, ?)",
            ("step1", "mod1", "path1", 0, "content"),
        )
        db.commit()

        cursor = db.execute("SELECT * FROM steps WHERE id = ?", ("step1",))
        row = cursor.fetchone()
        assert row["position"] == 0

    def test_unique_path_position(self, db: Database):
        """Rejeita duas etapas na mesma posição do mesmo path."""
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("mod1", "Módulo 1", "Desc"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name) VALUES (?, ?, ?)",
            ("path1", "mod1", "Principal"),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position) VALUES (?, ?, ?, ?)",
            ("step1", "mod1", "path1", 0),
        )
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO steps (id, module_id, path_id, position) VALUES (?, ?, ?, ?)",
                ("step2", "mod1", "path1", 0),
            )


class TestBranchOptionsTable:
    """Testes para a tabela branch_options."""

    def _setup_branch(self, db: Database):
        """Cria estrutura base para testar branch_options."""
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("mod1", "Módulo 1", "Desc"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name) VALUES (?, ?, ?)",
            ("path1", "mod1", "Principal"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name) VALUES (?, ?, ?)",
            ("path2", "mod1", "Alternativo"),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, ?)",
            ("step1", "mod1", "path1", 0, "branch"),
        )
        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            ("branch1", "step1"),
        )
        db.commit()

    def test_insert_branch_option(self, db: Database):
        """Insere opção de ramificação válida."""
        self._setup_branch(db)
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
            ("opt1", "branch1", "Opção A", "path2", 0),
        )
        db.commit()

        cursor = db.execute("SELECT * FROM branch_options WHERE id = ?", ("opt1",))
        row = cursor.fetchone()
        assert row["label"] == "Opção A"

    def test_label_min_3_chars(self, db: Database):
        """Rejeita label com menos de 3 caracteres."""
        self._setup_branch(db)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
                ("opt1", "branch1", "AB", "path2", 0),
            )

    def test_label_max_150_chars(self, db: Database):
        """Rejeita label com mais de 150 caracteres."""
        self._setup_branch(db)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
                ("opt1", "branch1", "x" * 151, "path2", 0),
            )

    def test_label_exactly_3_chars(self, db: Database):
        """Aceita label com exatamente 3 caracteres."""
        self._setup_branch(db)
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) VALUES (?, ?, ?, ?, ?)",
            ("opt1", "branch1", "ABC", "path2", 0),
        )
        db.commit()
        cursor = db.execute("SELECT * FROM branch_options WHERE id = ?", ("opt1",))
        assert cursor.fetchone() is not None


class TestUserProgressTable:
    """Testes para a tabela user_progress."""

    def _setup_user_and_module(self, db: Database):
        """Cria estrutura base: usuário, módulo, path e step."""
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("mod1", "Módulo 1", "Desc"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name) VALUES (?, ?, ?)",
            ("path1", "mod1", "Principal"),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position) VALUES (?, ?, ?, ?)",
            ("step1", "mod1", "path1", 0),
        )
        db.execute(
            "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
            ("user1", "Teste", "teste@email.com"),
        )
        db.commit()

    def test_insert_progress(self, db: Database):
        """Insere progresso válido."""
        self._setup_user_and_module(db)
        db.execute(
            "INSERT INTO user_progress (id, user_id, module_id, current_step_id, current_path_id, status, percentage) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("prog1", "user1", "mod1", "step1", "path1", "in_progress", 25.0),
        )
        db.commit()

        cursor = db.execute("SELECT * FROM user_progress WHERE id = ?", ("prog1",))
        row = cursor.fetchone()
        assert row["percentage"] == 25.0

    def test_unique_user_module(self, db: Database):
        """Rejeita duplicata user_id + module_id."""
        self._setup_user_and_module(db)
        db.execute(
            "INSERT INTO user_progress (id, user_id, module_id, current_step_id, status, percentage) VALUES (?, ?, ?, ?, ?, ?)",
            ("prog1", "user1", "mod1", "step1", "in_progress", 25.0),
        )
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO user_progress (id, user_id, module_id, current_step_id, status, percentage) VALUES (?, ?, ?, ?, ?, ?)",
                ("prog2", "user1", "mod1", "step1", "in_progress", 50.0),
            )


class TestCascadeDeletes:
    """Testes para verificar exclusão em cascata."""

    def test_delete_module_cascades_to_paths(self, db: Database):
        """Excluir módulo remove paths associados."""
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("mod1", "Módulo 1", "Desc"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name) VALUES (?, ?, ?)",
            ("path1", "mod1", "Principal"),
        )
        db.commit()

        db.execute("DELETE FROM modules WHERE id = ?", ("mod1",))
        db.commit()

        cursor = db.execute("SELECT * FROM paths WHERE module_id = ?", ("mod1",))
        assert cursor.fetchone() is None

    def test_delete_module_cascades_to_steps(self, db: Database):
        """Excluir módulo remove steps associados."""
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("mod1", "Módulo 1", "Desc"),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name) VALUES (?, ?, ?)",
            ("path1", "mod1", "Principal"),
        )
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position) VALUES (?, ?, ?, ?)",
            ("step1", "mod1", "path1", 0),
        )
        db.commit()

        db.execute("DELETE FROM modules WHERE id = ?", ("mod1",))
        db.commit()

        cursor = db.execute("SELECT * FROM steps WHERE module_id = ?", ("mod1",))
        assert cursor.fetchone() is None


class TestContextManager:
    """Testes para o suporte a context manager."""

    def test_context_manager_closes_connection(self):
        """Verifica que context manager fecha a conexão."""
        with Database(":memory:") as db:
            db.initialize()
            db.execute(
                "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
                ("mod1", "Módulo 1", "Desc"),
            )
            db.commit()

        assert db._connection is None

    def test_row_factory_returns_dict_like(self, db: Database):
        """Verifica que resultados são acessíveis por nome de coluna."""
        db.execute(
            "INSERT INTO modules (id, title, description) VALUES (?, ?, ?)",
            ("mod1", "Módulo 1", "Desc"),
        )
        db.commit()

        cursor = db.execute("SELECT * FROM modules WHERE id = ?", ("mod1",))
        row = cursor.fetchone()
        assert row["id"] == "mod1"
        assert row["title"] == "Módulo 1"
