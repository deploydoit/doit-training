"""Testes unitários para a página de boas-vindas.

Testa a lógica de identificação de usuário e verificação de primeira visita.

Requirements: 1.1, 1.2
"""

import pytest
from datetime import datetime
from uuid import uuid4

from models.database import Database
from pages.welcome import (
    _get_or_create_user,
    _mark_first_visit_complete,
    is_first_visit,
)


@pytest.fixture
def db():
    """Cria banco de dados em memória para testes."""
    database = Database(":memory:")
    database.initialize()
    return database


class TestIsFirstVisit:
    """Testes para a função is_first_visit."""

    def test_returns_true_for_new_user(self, db):
        """Novo usuário deve ter is_first_visit=True."""
        user = _get_or_create_user(db, "João", "joao@test.com")
        assert is_first_visit(db, user.id) is True

    def test_returns_false_after_marking_complete(self, db):
        """Após marcar visita completa, is_first_visit deve ser False."""
        user = _get_or_create_user(db, "Maria", "maria@test.com")
        _mark_first_visit_complete(db, user.id)
        assert is_first_visit(db, user.id) is False

    def test_returns_true_for_nonexistent_user(self, db):
        """Usuário inexistente deve retornar True (primeira visita)."""
        assert is_first_visit(db, "nonexistent-id") is True


class TestGetOrCreateUser:
    """Testes para a função _get_or_create_user."""

    def test_creates_new_user(self, db):
        """Deve criar novo usuário quando email não existe."""
        user = _get_or_create_user(db, "Ana", "ana@test.com")
        assert user.name == "Ana"
        assert user.email == "ana@test.com"
        assert user.is_first_visit is True
        assert user.is_admin is False
        assert user.id is not None

    def test_returns_existing_user(self, db):
        """Deve retornar usuário existente quando email já existe."""
        user1 = _get_or_create_user(db, "Carlos", "carlos@test.com")
        user2 = _get_or_create_user(db, "Carlos S.", "carlos@test.com")
        assert user1.id == user2.id
        assert user2.name == "Carlos S."  # Nome atualizado

    def test_preserves_first_visit_flag(self, db):
        """Deve preservar is_first_visit ao retornar usuário existente."""
        user = _get_or_create_user(db, "Pedro", "pedro@test.com")
        _mark_first_visit_complete(db, user.id)

        user_again = _get_or_create_user(db, "Pedro", "pedro@test.com")
        assert user_again.is_first_visit is False

    def test_updates_last_login(self, db):
        """Deve atualizar last_login ao retornar usuário existente."""
        user1 = _get_or_create_user(db, "Lucia", "lucia@test.com")
        # Simular que o primeiro login foi antes
        first_login = user1.last_login

        user2 = _get_or_create_user(db, "Lucia", "lucia@test.com")
        # last_login deve ser atualizado (ou pelo menos não ser anterior)
        assert user2.last_login >= first_login


class TestMarkFirstVisitComplete:
    """Testes para a função _mark_first_visit_complete."""

    def test_marks_visit_complete(self, db):
        """Deve marcar is_first_visit como False."""
        user = _get_or_create_user(db, "Marcos", "marcos@test.com")
        assert is_first_visit(db, user.id) is True

        _mark_first_visit_complete(db, user.id)
        assert is_first_visit(db, user.id) is False

    def test_idempotent(self, db):
        """Chamar múltiplas vezes não deve causar erro."""
        user = _get_or_create_user(db, "Fernanda", "fernanda@test.com")
        _mark_first_visit_complete(db, user.id)
        _mark_first_visit_complete(db, user.id)
        assert is_first_visit(db, user.id) is False
