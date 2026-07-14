"""Camada de banco de dados SQLite para o Sistema de Treinamento.

Implementa a classe Database responsável por:
- Conexão e inicialização do banco SQLite
- Criação de todas as tabelas conforme esquema do design
- Constraints e índices para integridade referencial

Requirements: 5.1, 5.2
"""

import sqlite3
from pathlib import Path
from typing import Optional


class Database:
    """Gerencia conexão e operações com o banco de dados SQLite.

    Attributes:
        db_path: Caminho para o arquivo do banco de dados.
                 Use ':memory:' para banco em memória (testes).
    """

    def __init__(self, db_path: str = "training.db"):
        """Inicializa a conexão com o banco de dados.

        Args:
            db_path: Caminho para o arquivo SQLite.
                     Padrão: 'training.db' no diretório atual.
                     Use ':memory:' para testes.
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Retorna a conexão ativa, criando uma se necessário."""
        if self._connection is None:
            self._connection = self._create_connection()
        return self._connection

    def _create_connection(self) -> sqlite3.Connection:
        """Cria uma nova conexão SQLite com configurações adequadas."""
        # Garantir que o diretório existe (exceto para :memory:)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Habilitar foreign keys (desabilitadas por padrão no SQLite)
        conn.execute("PRAGMA foreign_keys = ON")
        # WAL mode para melhor concorrência
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def initialize(self) -> None:
        """Cria todas as tabelas e índices do banco de dados.

        Deve ser chamado na inicialização da aplicação para garantir
        que o esquema existe.
        """
        self._create_tables()
        self._create_indexes()

    def _create_tables(self) -> None:
        """Cria todas as tabelas conforme esquema do design."""
        conn = self.connection
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS modules (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL CHECK(length(description) <= 150),
                status TEXT NOT NULL DEFAULT 'draft',
                version INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS paths (
                id TEXT PRIMARY KEY,
                module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                parent_branch_id TEXT,
                name TEXT NOT NULL,
                is_main BOOLEAN DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY,
                module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                path_id TEXT NOT NULL REFERENCES paths(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                step_type TEXT NOT NULL DEFAULT 'content',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(path_id, position)
            );

            CREATE TABLE IF NOT EXISTS step_contents (
                id TEXT PRIMARY KEY,
                step_id TEXT NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
                content_type TEXT NOT NULL,
                content_data TEXT NOT NULL,
                alt_text TEXT,
                display_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS branches (
                id TEXT PRIMARY KEY,
                step_id TEXT NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
                UNIQUE(step_id)
            );

            CREATE TABLE IF NOT EXISTS branch_options (
                id TEXT PRIMARY KEY,
                branch_id TEXT NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
                label TEXT NOT NULL CHECK(length(label) >= 3 AND length(label) <= 150),
                path_id TEXT NOT NULL REFERENCES paths(id) ON DELETE CASCADE,
                position INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                is_first_visit BOOLEAN DEFAULT TRUE,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_progress (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                current_step_id TEXT NOT NULL REFERENCES steps(id),
                current_path_id TEXT REFERENCES paths(id),
                status TEXT NOT NULL DEFAULT 'not_started',
                percentage REAL NOT NULL DEFAULT 0.0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, module_id)
            );

            CREATE TABLE IF NOT EXISTS completed_steps (
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                step_id TEXT NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(user_id, step_id)
            );

            CREATE TABLE IF NOT EXISTS explored_paths (
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                path_id TEXT NOT NULL REFERENCES paths(id) ON DELETE CASCADE,
                branch_id TEXT NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
                explored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(user_id, path_id)
            );
        """)

        # Adicionar foreign key de paths.parent_branch_id após branches existir
        # (SQLite não suporta ALTER TABLE ADD CONSTRAINT, mas a referência é
        # tratada via lógica de aplicação e os índices abaixo)

    def _create_indexes(self) -> None:
        """Cria índices para otimizar consultas frequentes."""
        conn = self.connection
        conn.executescript("""
            -- Índices para navegação em módulos
            CREATE INDEX IF NOT EXISTS idx_paths_module_id
                ON paths(module_id);

            CREATE INDEX IF NOT EXISTS idx_paths_parent_branch_id
                ON paths(parent_branch_id);

            -- Índices para navegação em etapas
            CREATE INDEX IF NOT EXISTS idx_steps_module_id
                ON steps(module_id);

            CREATE INDEX IF NOT EXISTS idx_steps_path_id
                ON steps(path_id);

            CREATE INDEX IF NOT EXISTS idx_steps_path_position
                ON steps(path_id, position);

            -- Índices para conteúdo
            CREATE INDEX IF NOT EXISTS idx_step_contents_step_id
                ON step_contents(step_id);

            -- Índices para ramificações
            CREATE INDEX IF NOT EXISTS idx_branches_step_id
                ON branches(step_id);

            CREATE INDEX IF NOT EXISTS idx_branch_options_branch_id
                ON branch_options(branch_id);

            CREATE INDEX IF NOT EXISTS idx_branch_options_path_id
                ON branch_options(path_id);

            -- Índices para progresso do usuário
            CREATE INDEX IF NOT EXISTS idx_user_progress_user_id
                ON user_progress(user_id);

            CREATE INDEX IF NOT EXISTS idx_user_progress_module_id
                ON user_progress(module_id);

            CREATE INDEX IF NOT EXISTS idx_user_progress_last_accessed
                ON user_progress(last_accessed);

            -- Índices para etapas concluídas
            CREATE INDEX IF NOT EXISTS idx_completed_steps_user_id
                ON completed_steps(user_id);

            CREATE INDEX IF NOT EXISTS idx_completed_steps_step_id
                ON completed_steps(step_id);

            -- Índices para caminhos explorados
            CREATE INDEX IF NOT EXISTS idx_explored_paths_user_id
                ON explored_paths(user_id);

            CREATE INDEX IF NOT EXISTS idx_explored_paths_branch_id
                ON explored_paths(branch_id);

            -- Índice para busca de usuários por email
            CREATE INDEX IF NOT EXISTS idx_users_email
                ON users(email);
        """)

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Executa uma query SQL com parâmetros.

        Args:
            query: Query SQL parametrizada.
            params: Tupla de parâmetros para a query.

        Returns:
            Cursor com o resultado da execução.
        """
        return self.connection.execute(query, params)

    def executemany(self, query: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """Executa uma query SQL para múltiplos conjuntos de parâmetros.

        Args:
            query: Query SQL parametrizada.
            params_list: Lista de tuplas de parâmetros.

        Returns:
            Cursor com o resultado da execução.
        """
        return self.connection.executemany(query, params_list)

    def commit(self) -> None:
        """Confirma a transação atual."""
        self.connection.commit()

    def rollback(self) -> None:
        """Desfaz a transação atual."""
        self.connection.rollback()

    def close(self) -> None:
        """Fecha a conexão com o banco de dados."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "Database":
        """Suporte a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Fecha conexão ao sair do context manager."""
        self.close()
