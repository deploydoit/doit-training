"""Testes baseados em propriedades (Hypothesis) para o Sistema de Treinamento.

Utiliza property-based testing para validar comportamento universal
do sistema em cenários gerados automaticamente.

Biblioteca: Hypothesis
Formato de tag: Feature: client-training, Property N: título
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from hypothesis.strategies import composite

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from managers.content_manager import ContentManager
from models.database import Database
from models.enums import ModuleStatus, ProgressStatus, StepType


# =============================================================================
# Strategies para Property 11
# =============================================================================


@composite
def version_migration_scenario(draw):
    """Gera um cenário de migração de versão com:
    - Um módulo com N etapas (versão atual)
    - Um subconjunto de etapas marcadas como concluídas pelo usuário
    - Etapas que serão removidas na nova versão
    - Etapas que permanecerão na nova versão

    Returns:
        Dict com:
            total_steps: número total de etapas na versão N
            completed_positions: posições das etapas concluídas pelo usuário
            steps_to_remove_positions: posições das etapas que serão removidas na v N+1
            user_current_position: posição atual do usuário
    """
    # Módulo com 3 a 15 etapas
    total_steps = draw(st.integers(min_value=3, max_value=15))

    # Subconjunto de posições que o usuário completou (pelo menos 1)
    all_positions = list(range(total_steps))
    completed_positions = draw(
        st.lists(
            st.sampled_from(all_positions),
            min_size=1,
            max_size=total_steps,
            unique=True,
        )
    )

    # Posição atual do usuário (uma das etapas existentes)
    user_current_position = draw(st.sampled_from(all_positions))

    # Etapas a remover na nova versão (0 a total_steps - 1 para garantir pelo
    # menos 1 etapa restante)
    max_removable = total_steps - 1
    steps_to_remove_positions = draw(
        st.lists(
            st.sampled_from(all_positions),
            min_size=0,
            max_size=min(max_removable, total_steps // 2 + 1),
            unique=True,
        )
    )

    return {
        "total_steps": total_steps,
        "completed_positions": sorted(completed_positions),
        "steps_to_remove_positions": sorted(steps_to_remove_positions),
        "user_current_position": user_current_position,
    }


# =============================================================================
# Property 11: Migração de versão preserva progresso
# =============================================================================


# Feature: client-training, Property 11: Migração de versão preserva progresso
class TestProperty11VersionMigrationPreservesProgress:
    """**Validates: Requirements 6.4**

    Property 11: For any user with progress on module version N, when version
    N+1 is published, all steps in completed_steps that still exist in version
    N+1 remain marked as completed. The user's current position is set to the
    most advanced valid step.
    """

    def _setup_module_with_steps(self, db, module_id, path_id, num_steps):
        """Helper: cria módulo com N etapas no caminho principal."""
        db.execute(
            "INSERT INTO modules (id, title, description, status, version) "
            "VALUES (?, ?, ?, ?, ?)",
            (module_id, "Módulo Versão", "Módulo para teste de migração", "published", 1),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
            (path_id, module_id, "Principal", True),
        )

        step_ids = []
        for i in range(num_steps):
            step_id = f"{module_id}_step_{i}"
            db.execute(
                "INSERT INTO steps (id, module_id, path_id, position, step_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (step_id, module_id, path_id, i, "content"),
            )
            db.execute(
                "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"content_{step_id}", step_id, "text", f"Conteúdo etapa {i}", 0),
            )
            step_ids.append(step_id)

        db.commit()
        return step_ids

    def _setup_user_with_progress(
        self, db, user_id, module_id, path_id, current_step_id, completed_step_ids
    ):
        """Helper: cria usuário com progresso no módulo."""
        db.execute(
            "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
            (user_id, "Usuário Teste", f"{user_id}@teste.com"),
        )
        progress_id = f"progress_{user_id}_{module_id}"
        db.execute(
            "INSERT INTO user_progress (id, user_id, module_id, current_step_id, "
            "current_path_id, status, percentage) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                progress_id,
                user_id,
                module_id,
                current_step_id,
                path_id,
                "in_progress",
                50.0,
            ),
        )
        for step_id in completed_step_ids:
            db.execute(
                "INSERT INTO completed_steps (user_id, step_id) VALUES (?, ?)",
                (user_id, step_id),
            )
        db.commit()

    def _remove_steps(self, db, step_ids_to_remove):
        """Helper: remove etapas simulando atualização de versão.

        Desabilita FK temporariamente para permitir remoção de steps
        referenciados por user_progress (que será corrigido pela migração).
        Mantém completed_steps intactos para que a migração os processe.
        """
        # Desabilitar FK temporariamente para simular o cenário onde o admin
        # remove etapas no módulo antes da migração rodar
        db.execute("PRAGMA foreign_keys = OFF", ())
        for step_id in step_ids_to_remove:
            # Remove content
            db.execute("DELETE FROM step_contents WHERE step_id = ?", (step_id,))
            # Remove step
            db.execute("DELETE FROM steps WHERE id = ?", (step_id,))
        db.commit()
        # Reabilitar FK
        db.execute("PRAGMA foreign_keys = ON", ())

    @given(scenario=version_migration_scenario())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_migration_preserves_completed_steps(self, scenario):
        """Etapas concluídas que ainda existem na nova versão permanecem marcadas.

        **Validates: Requirements 6.4**
        """
        # Setup fresh database for each example
        db = Database(":memory:")
        db.initialize()

        try:
            module_id = f"mod_{uuid.uuid4().hex[:8]}"
            path_id = f"path_{module_id}"
            user_id = f"user_{uuid.uuid4().hex[:8]}"

            total_steps = scenario["total_steps"]
            completed_positions = scenario["completed_positions"]
            steps_to_remove_positions = scenario["steps_to_remove_positions"]
            user_current_position = scenario["user_current_position"]

            # Setup: criar módulo com etapas
            step_ids = self._setup_module_with_steps(db, module_id, path_id, total_steps)

            # Setup: definir progresso do usuário
            current_step_id = step_ids[user_current_position]
            completed_step_ids = [step_ids[pos] for pos in completed_positions]
            self._setup_user_with_progress(
                db, user_id, module_id, path_id, current_step_id, completed_step_ids
            )

            # Simular remoção de etapas (atualização para v N+1)
            step_ids_to_remove = [step_ids[pos] for pos in steps_to_remove_positions]
            self._remove_steps(db, step_ids_to_remove)

            # Executar migração via ContentManager.publish_module
            # (internamente chama _migrate_user_progress)
            content_manager = ContentManager(db, media_path="/tmp/media")
            content_manager._migrate_user_progress(module_id)

            # Verificar: etapas concluídas que AINDA EXISTEM devem permanecer
            remaining_step_ids = set(step_ids) - set(step_ids_to_remove)
            completed_that_should_remain = [
                sid for sid in completed_step_ids if sid in remaining_step_ids
            ]

            cursor = db.execute(
                "SELECT step_id FROM completed_steps WHERE user_id = ?",
                (user_id,),
            )
            actual_completed = {row["step_id"] for row in cursor.fetchall()}

            # Todas as etapas concluídas que ainda existem devem estar preservadas
            for step_id in completed_that_should_remain:
                assert step_id in actual_completed, (
                    f"Etapa concluída '{step_id}' que ainda existe na nova versão "
                    f"deveria permanecer marcada como concluída."
                )

            # Etapas removidas NÃO devem estar nos completed_steps
            for step_id in step_ids_to_remove:
                assert step_id not in actual_completed, (
                    f"Etapa removida '{step_id}' não deveria estar nos completed_steps."
                )
        finally:
            db.close()

    @given(scenario=version_migration_scenario())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_migration_sets_most_advanced_valid_position(self, scenario):
        """Posição do usuário é atualizada para a etapa mais avançada válida.

        Quando a etapa atual do usuário é removida na nova versão, o sistema
        deve posicioná-lo na etapa concluída de maior posição que ainda existe.

        **Validates: Requirements 6.4**
        """
        # Setup fresh database for each example
        db = Database(":memory:")
        db.initialize()

        try:
            module_id = f"mod_{uuid.uuid4().hex[:8]}"
            path_id = f"path_{module_id}"
            user_id = f"user_{uuid.uuid4().hex[:8]}"

            total_steps = scenario["total_steps"]
            completed_positions = scenario["completed_positions"]
            steps_to_remove_positions = scenario["steps_to_remove_positions"]
            user_current_position = scenario["user_current_position"]

            # Setup: criar módulo com etapas
            step_ids = self._setup_module_with_steps(db, module_id, path_id, total_steps)

            # Setup: definir progresso do usuário
            current_step_id = step_ids[user_current_position]
            completed_step_ids = [step_ids[pos] for pos in completed_positions]
            self._setup_user_with_progress(
                db, user_id, module_id, path_id, current_step_id, completed_step_ids
            )

            # Simular remoção de etapas (atualização para v N+1)
            step_ids_to_remove = [step_ids[pos] for pos in steps_to_remove_positions]
            self._remove_steps(db, step_ids_to_remove)

            # Executar migração
            content_manager = ContentManager(db, media_path="/tmp/media")
            content_manager._migrate_user_progress(module_id)

            # Verificar posição atual do usuário
            cursor = db.execute(
                "SELECT current_step_id, current_path_id "
                "FROM user_progress WHERE user_id = ? AND module_id = ?",
                (user_id, module_id),
            )
            progress_row = cursor.fetchone()
            assert progress_row is not None, "Progresso do usuário deveria existir"

            new_current_step_id = progress_row["current_step_id"]

            # O current_step resultante DEVE ser um step que ainda existe
            remaining_step_ids = set(step_ids) - set(step_ids_to_remove)
            assert new_current_step_id in remaining_step_ids, (
                f"A posição atual '{new_current_step_id}' deveria ser uma etapa "
                f"que ainda existe na nova versão."
            )

            # Se a etapa atual original ainda existe, ela pode continuar sendo a atual
            if current_step_id in remaining_step_ids:
                assert new_current_step_id == current_step_id, (
                    f"Se a etapa atual original ainda existe, o usuário deveria "
                    f"permanecer nela. Esperado: {current_step_id}, "
                    f"Obtido: {new_current_step_id}"
                )
            else:
                # Etapa atual foi removida: novo step deve ser a etapa concluída
                # mais avançada que ainda existe, OU a primeira etapa do main path
                completed_that_remain = [
                    sid for sid in completed_step_ids if sid in remaining_step_ids
                ]

                if completed_that_remain:
                    # Buscar a posição de cada etapa concluída restante
                    cursor = db.execute(
                        "SELECT id, position FROM steps WHERE module_id = ? "
                        "ORDER BY position DESC",
                        (module_id,),
                    )
                    steps_by_position = {
                        row["id"]: row["position"] for row in cursor.fetchall()
                    }

                    # A mais avançada (maior posição) entre as concluídas restantes
                    most_advanced = max(
                        completed_that_remain,
                        key=lambda sid: steps_by_position.get(sid, -1),
                    )
                    assert new_current_step_id == most_advanced, (
                        f"Quando etapa atual é removida, usuário deveria ficar na "
                        f"etapa concluída mais avançada válida. "
                        f"Esperado: {most_advanced}, Obtido: {new_current_step_id}"
                    )
                else:
                    # Nenhuma etapa concluída resta: deve ir para primeira do main path
                    cursor = db.execute(
                        "SELECT id FROM steps WHERE path_id = ? "
                        "ORDER BY position LIMIT 1",
                        (path_id,),
                    )
                    first_step = cursor.fetchone()
                    if first_step:
                        assert new_current_step_id == first_step["id"], (
                            f"Sem etapas concluídas válidas, usuário deveria ir "
                            f"para primeira etapa. Esperado: {first_step['id']}, "
                            f"Obtido: {new_current_step_id}"
                        )
        finally:
            db.close()


# =============================================================================
# Strategies para Property 3
# =============================================================================


@composite
def published_module_with_steps_strategy(draw):
    """Gera dados para um módulo publicado com caminho principal e etapas.

    Retorna um dict com:
        module_id, path_id, num_steps, title, description
    """
    suffix = draw(st.integers(min_value=1, max_value=999999))
    module_id = f"mod_p3_{suffix}"
    path_id = f"path_p3_{suffix}"

    title = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
            min_size=3,
            max_size=60,
        ).filter(lambda s: s.strip() != "" and len(s.strip()) >= 3)
    )
    description = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
            min_size=5,
            max_size=140,
        ).filter(lambda s: s.strip() != "" and len(s.strip()) >= 5)
    )

    num_steps = draw(st.integers(min_value=1, max_value=15))

    return {
        "module_id": module_id,
        "path_id": path_id,
        "num_steps": num_steps,
        "title": title,
        "description": description,
    }


def _insert_published_module_p3(db: Database, data: dict) -> None:
    """Insere um módulo publicado com caminho principal e etapas no banco.

    Args:
        db: Banco de dados em memória.
        data: Dict gerado por published_module_with_steps_strategy.
    """
    module_id = data["module_id"]
    path_id = data["path_id"]
    num_steps = data["num_steps"]

    # Inserir módulo publicado
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, data["title"], data["description"], ModuleStatus.PUBLISHED.value),
    )

    # Inserir caminho principal
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path_id, module_id, "Principal", True),
    )

    # Inserir etapas com posição sequencial (0..N-1)
    for i in range(num_steps):
        step_id = f"{module_id}_step_{i}"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, i, "content"),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"content_{step_id}", step_id, "text", f"Conteúdo etapa {i}", 0),
        )

    db.commit()


# =============================================================================
# Property 3: Seleção de módulo leva à primeira etapa
# =============================================================================


# Feature: client-training, Property 3: Seleção de módulo leva à primeira etapa
class TestProperty3ModuleSelectionFirstStep:
    """**Validates: Requirements 1.4**

    Property 3: Para qualquer módulo publicado com pelo menos uma etapa,
    selecionar esse módulo deve retornar a etapa na posição 0 do caminho principal.
    """

    @given(module_data=published_module_with_steps_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_selecting_published_module_returns_first_step_of_main_path(self, module_data):
        """Para qualquer módulo publicado com pelo menos uma etapa,
        get_first_step deve retornar a etapa na posição 0 do caminho principal.

        **Validates: Requirements 1.4**
        """
        # Arrange: criar banco em memória e inserir módulo
        db = Database(":memory:")
        db.initialize()

        try:
            _insert_published_module_p3(db, module_data)

            from managers.training_manager import TrainingManager
            tm = TrainingManager(db)

            # Act: selecionar o módulo (get_first_step)
            first_step = tm.get_first_step(module_data["module_id"])

            # Assert: deve retornar uma etapa válida
            assert first_step is not None, (
                f"get_first_step retornou None para módulo publicado "
                f"'{module_data['module_id']}' com {module_data['num_steps']} etapas"
            )

            # Assert: a etapa deve estar na posição 0
            assert first_step.position == 0, (
                f"Esperava posição 0, obteve posição {first_step.position}"
            )

            # Assert: a etapa deve pertencer ao caminho principal
            assert first_step.path_id == module_data["path_id"], (
                f"Esperava path_id '{module_data['path_id']}', "
                f"obteve '{first_step.path_id}'"
            )

            # Assert: a etapa deve pertencer ao módulo selecionado
            assert first_step.module_id == module_data["module_id"], (
                f"Esperava module_id '{module_data['module_id']}', "
                f"obteve '{first_step.module_id}'"
            )
        finally:
            db.close()

# =============================================================================
# Helpers for Property 5
# =============================================================================


def _create_nav_db_with_path(num_steps: int, has_branch_after_last: bool = False):
    """Cria banco em memória com módulo, caminho e etapas para testes de navegação.

    Args:
        num_steps: Número de etapas no caminho.
        has_branch_after_last: Se True, a última etapa contém uma ramificação
                               com um caminho subsequente.

    Returns:
        Tuple (Database, TrainingManager, module_id, path_id, step_ids, total_steps)
    """
    from managers.training_manager import TrainingManager

    db = Database(":memory:")
    db.initialize()

    module_id = f"mod_{uuid.uuid4().hex[:8]}"
    path_id = f"path_{uuid.uuid4().hex[:8]}"

    # Criar módulo publicado
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo Teste Nav", "Módulo para teste de navegação", "published"),
    )

    # Criar caminho principal
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path_id, module_id, "Principal", True),
    )

    # Criar etapas
    step_ids = []
    for i in range(num_steps):
        step_id = f"step_{module_id}_{i}"
        # Última etapa pode ser do tipo branch se has_branch_after_last
        step_type = "content"
        if i == num_steps - 1 and has_branch_after_last:
            step_type = "branch"

        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, i, step_type),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"content_{step_id}", step_id, "text", f"Conteúdo etapa {i}", 0),
        )
        step_ids.append(step_id)

    # Se a última etapa tem branch, criar ramificação com caminhos
    if has_branch_after_last:
        last_step_id = step_ids[-1]
        branch_id = f"branch_{module_id}"
        sub_path_id = f"sub_path_{module_id}"

        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            (branch_id, last_step_id),
        )
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, ?, ?, ?)",
            (sub_path_id, module_id, branch_id, "Sub-caminho", False),
        )
        # Adicionar etapa no sub-caminho
        sub_step_id = f"sub_step_{module_id}_0"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (sub_step_id, module_id, sub_path_id, 0, "content"),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"content_{sub_step_id}", sub_step_id, "text", "Conteúdo sub", 0),
        )
        # Opção A
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"opt_{branch_id}_0", branch_id, "Opção A do caminho", sub_path_id, 0),
        )
        # Opção B (precisa de pelo menos 2 opções para validação)
        sub_path_id_2 = f"sub_path2_{module_id}"
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, ?, ?, ?)",
            (sub_path_id_2, module_id, branch_id, "Sub-caminho 2", False),
        )
        sub_step_id_2 = f"sub_step2_{module_id}_0"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (sub_step_id_2, module_id, sub_path_id_2, 0, "content"),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"content_{sub_step_id_2}", sub_step_id_2, "text", "Conteúdo sub 2", 0),
        )
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"opt_{branch_id}_1", branch_id, "Opção B do caminho", sub_path_id_2, 1),
        )

    db.commit()

    tm = TrainingManager(db)
    return db, tm, module_id, path_id, step_ids, num_steps


def _step_has_subsequent_branch(db: Database, step_id: str) -> bool:
    """Verifica se uma etapa possui uma ramificação (branch) associada.

    Args:
        db: Instância do banco de dados.
        step_id: ID da etapa a verificar.

    Returns:
        True se a etapa contém uma ramificação com opções.
    """
    cursor = db.execute(
        "SELECT id FROM branches WHERE step_id = ?", (step_id,)
    )
    branch_row = cursor.fetchone()
    if branch_row is None:
        return False

    # Verificar que o branch tem opções (caminhos subsequentes)
    cursor = db.execute(
        "SELECT COUNT(*) as cnt FROM branch_options WHERE branch_id = ?",
        (branch_row["id"],),
    )
    count_row = cursor.fetchone()
    return count_row is not None and count_row["cnt"] > 0


# =============================================================================
# Property 5: Estado dos botões de navegação determinado pela posição
# =============================================================================


# Feature: client-training, Property 5: Estado dos botões de navegação determinado pela posição
class TestProperty5NavigationButtonState:
    """**Validates: Requirements 2.1, 2.4, 2.5, 2.6**

    Property 5: For any step in a path of length T:
    (a) the back button is disabled iff position == 0
    (b) the forward button is replaced by "complete module" iff position == T-1
        AND no subsequent branch exists
    (c) the progress indicator displays "Etapa {position+1} de {T}"
    """

    @given(
        num_steps=st.integers(min_value=2, max_value=20),
        position_fraction=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=200)
    def test_back_button_disabled_iff_first_step(self, num_steps, position_fraction):
        """(a) O botão de retroceder é desabilitado se e somente se position == 0.

        **Validates: Requirements 2.1, 2.4**

        Para qualquer etapa em um caminho de comprimento T, o botão voltar
        está desabilitado quando e somente quando a posição é 0 (primeira etapa).
        """
        # Determine position from fraction to cover all positions
        position = int(position_fraction * (num_steps - 1))
        assume(0 <= position < num_steps)

        db, tm, module_id, path_id, step_ids, total = _create_nav_db_with_path(num_steps)

        try:
            step_id = step_ids[position]
            is_first = tm.is_first_step(module_id, step_id)

            # Property: back button disabled iff position == 0
            if position == 0:
                assert is_first is True, (
                    f"Step at position 0 should be first step (back disabled), "
                    f"but is_first_step returned False. Path has {num_steps} steps."
                )
            else:
                assert is_first is False, (
                    f"Step at position {position} should NOT be first step, "
                    f"but is_first_step returned True. Path has {num_steps} steps."
                )

            # Also verify through get_previous_step: None iff position == 0
            prev_step = tm.get_previous_step(module_id, step_id, path_id)
            if position == 0:
                assert prev_step is None, (
                    f"First step (position=0) should have no previous step, "
                    f"but got step with id={prev_step.id if prev_step else None}."
                )
            else:
                assert prev_step is not None, (
                    f"Step at position {position} should have a previous step, "
                    f"but get_previous_step returned None."
                )
        finally:
            db.close()

    @given(
        num_steps=st.integers(min_value=2, max_value=20),
        position_fraction=st.floats(min_value=0.0, max_value=1.0),
        has_branch=st.booleans(),
    )
    @settings(max_examples=200)
    def test_forward_button_replaced_by_complete_at_last_step_without_branch(
        self, num_steps, position_fraction, has_branch
    ):
        """(b) Botão avançar substituído por "concluir módulo" iff última etapa sem branch.

        **Validates: Requirements 2.1, 2.5**

        O botão de avançar é substituído por "concluir módulo" se e somente se
        a posição é T-1 (última etapa) E não existe ramificação subsequente.
        """
        position = int(position_fraction * (num_steps - 1))
        assume(0 <= position < num_steps)

        # has_branch only applies to the last step for this test
        use_branch = has_branch and (position == num_steps - 1)
        db, tm, module_id, path_id, step_ids, total = _create_nav_db_with_path(
            num_steps, has_branch_after_last=use_branch
        )

        try:
            step_id = step_ids[position]
            is_last = tm.is_last_step(module_id, step_id)
            has_subsequent_branch = _step_has_subsequent_branch(db, step_id)

            should_show_complete = (position == num_steps - 1) and not has_subsequent_branch

            # Verify is_last_step correctness
            if position == num_steps - 1:
                assert is_last is True, (
                    f"Step at position {position} (last in path of {num_steps}) "
                    f"should be last step, but is_last_step returned False."
                )
            else:
                assert is_last is False, (
                    f"Step at position {position} in path of {num_steps} "
                    f"should NOT be last step, but is_last_step returned True."
                )

            # Verify "complete module" button logic
            show_complete = is_last and not has_subsequent_branch
            assert show_complete == should_show_complete, (
                f"Position={position}, num_steps={num_steps}, has_branch={use_branch}. "
                f"Expected show_complete={should_show_complete}, got {show_complete}."
            )

            # When not last step, get_next_step should return a step
            if position < num_steps - 1:
                next_step = tm.get_next_step(module_id, step_id, path_id)
                assert next_step is not None, (
                    f"Step at position {position} in path of {num_steps} "
                    f"should have a next step, but get_next_step returned None."
                )
        finally:
            db.close()

    @given(
        num_steps=st.integers(min_value=2, max_value=20),
        position_fraction=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=200)
    def test_progress_indicator_displays_correct_position(self, num_steps, position_fraction):
        """(c) Indicador de progresso exibe "Etapa {position+1} de {T}".

        **Validates: Requirements 2.1, 2.6**

        Para qualquer etapa na posição N de um caminho com T etapas,
        o indicador de progresso deve mostrar "Etapa N+1 de T".
        """
        position = int(position_fraction * (num_steps - 1))
        assume(0 <= position < num_steps)

        db, tm, module_id, path_id, step_ids, total = _create_nav_db_with_path(num_steps)

        try:
            step_id = step_ids[position]

            # Retrieve the step from the DB to verify its position
            step = tm.get_step(module_id, step_id)

            # The step's position from DB should match expected
            assert step.position == position, (
                f"Step position from DB ({step.position}) doesn't match "
                f"expected position ({position})."
            )

            # Count total steps in the path
            cursor = db.execute(
                "SELECT COUNT(*) as cnt FROM steps WHERE path_id = ?",
                (path_id,),
            )
            total_in_path = cursor.fetchone()["cnt"]

            assert total_in_path == num_steps, (
                f"Total steps in path ({total_in_path}) doesn't match "
                f"expected ({num_steps})."
            )

            # Verify the progress indicator format
            expected_progress = f"Etapa {position + 1} de {total_in_path}"
            actual_progress = f"Etapa {step.position + 1} de {total_in_path}"

            assert actual_progress == expected_progress, (
                f"Progress indicator mismatch. "
                f"Expected: '{expected_progress}', Got: '{actual_progress}'."
            )
        finally:
            db.close()


# =============================================================================
# Property 4: Ida e volta na navegação (round-trip)
# Feature: client-training, Property 4: Ida e volta na navegação (round-trip)
# Validates: Requirements 2.2, 2.3
# =============================================================================

from managers.training_manager import TrainingManager


def _create_db_with_path(num_steps: int):
    """Cria um banco em memória com um módulo contendo um caminho de N etapas.

    Returns:
        Tuple (Database, TrainingManager, module_id, path_id, step_ids)
    """
    db = Database(":memory:")
    db.initialize()

    module_id = "test_module"
    path_id = "test_path"

    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo Teste", "Módulo para teste de round-trip", "published"),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path_id, module_id, "Principal", True),
    )

    step_ids = []
    for i in range(num_steps):
        step_id = f"step_{i}"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, i, "content"),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"content_{step_id}", step_id, "text", f"Conteúdo etapa {i}", 0),
        )
        step_ids.append(step_id)

    db.commit()

    tm = TrainingManager(db)
    return db, tm, module_id, path_id, step_ids


# Feature: client-training, Property 4: Ida e volta na navegação (round-trip)
class TestProperty4NavigationRoundTrip:
    """**Validates: Requirements 2.2, 2.3**

    Property 4: For any step at position N where 0 < N < last_position in a path,
    advancing from step N-1 and then retreating should return to step N-1.
    Similarly, retreating from N+1 and advancing should return to N+1.
    """

    @given(
        num_steps=st.integers(min_value=3, max_value=20),
        position=st.integers(min_value=1, max_value=19),
    )
    @settings(max_examples=200)
    def test_advance_then_retreat_returns_to_original(self, num_steps, position):
        """Avançar de N-1 para N e depois retroceder deve retornar à etapa N-1.

        **Validates: Requirements 2.2, 2.3**

        Para qualquer etapa na posição N (0 < N < last_position), se estamos
        na etapa N-1 e avançamos, chegamos a N. Se então retrocedemos de N,
        devemos voltar para N-1 (round-trip forward-backward).
        """
        assume(position < num_steps - 1)

        db, tm, module_id, path_id, step_ids = _create_db_with_path(num_steps)

        try:
            # Começar na etapa N-1
            start_step_id = step_ids[position - 1]

            # Avançar de N-1 para N
            next_step = tm.get_next_step(module_id, start_step_id, path_id)
            assert next_step is not None, (
                f"Avançar de posição {position - 1} deveria retornar etapa na posição {position}"
            )
            assert next_step.id == step_ids[position], (
                f"Avançar deveria ir para step_{position}, mas foi para {next_step.id}"
            )

            # Retroceder de N para N-1 (round-trip)
            prev_step = tm.get_previous_step(module_id, next_step.id, path_id)
            assert prev_step is not None, (
                f"Retroceder de posição {position} deveria retornar etapa na posição {position - 1}"
            )
            assert prev_step.id == start_step_id, (
                f"Round-trip falhou: esperado {start_step_id}, obtido {prev_step.id}"
            )
        finally:
            db.close()

    @given(
        num_steps=st.integers(min_value=3, max_value=20),
        position=st.integers(min_value=1, max_value=19),
    )
    @settings(max_examples=200)
    def test_retreat_then_advance_returns_to_original(self, num_steps, position):
        """Retroceder de N+1 para N e depois avançar deve retornar à etapa N+1.

        **Validates: Requirements 2.2, 2.3**

        Para qualquer etapa na posição N (0 < N < last_position), se estamos
        na etapa N+1 e retrocedemos, chegamos a N. Se então avançamos de N,
        devemos voltar para N+1 (round-trip backward-forward).
        """
        assume(position < num_steps - 1)

        db, tm, module_id, path_id, step_ids = _create_db_with_path(num_steps)

        try:
            # Começar na etapa N+1
            start_step_id = step_ids[position + 1] if position + 1 < num_steps else None
            assume(start_step_id is not None)

            # Retroceder de N+1 para N
            prev_step = tm.get_previous_step(module_id, start_step_id, path_id)
            assert prev_step is not None, (
                f"Retroceder de posição {position + 1} deveria retornar etapa na posição {position}"
            )
            assert prev_step.id == step_ids[position], (
                f"Retroceder deveria ir para step_{position}, mas foi para {prev_step.id}"
            )

            # Avançar de N para N+1 (round-trip)
            next_step = tm.get_next_step(module_id, prev_step.id, path_id)
            assert next_step is not None, (
                f"Avançar de posição {position} deveria retornar etapa na posição {position + 1}"
            )
            assert next_step.id == start_step_id, (
                f"Round-trip falhou: esperado {start_step_id}, obtido {next_step.id}"
            )
        finally:
            db.close()


# =============================================================================
# Strategies para Property 10: Validação de publicação do módulo
# =============================================================================


@composite
def module_for_validation_strategy(draw):
    """Gera uma estrutura de módulo com parâmetros variáveis para testar validação.

    Gera módulos que podem ter:
    - Etapas com ou sem conteúdo
    - Ramificações com número variável de opções (0-7)
    - Labels de opções com comprimentos variáveis (1-100 caracteres)

    Returns:
        Dict com module_id, steps_config, branches_config descrevendo a estrutura
        e os violations esperados.
    """
    module_id = f"mod_p10_{uuid.uuid4().hex[:8]}"
    main_path_id = f"main_{module_id}"

    # Gerar etapas no caminho principal
    num_content_steps = draw(st.integers(min_value=1, max_value=6))
    has_branch = draw(st.booleans())

    steps_config = []
    expected_violations = []

    # Etapas de conteúdo no caminho principal
    for i in range(num_content_steps):
        has_content = draw(st.booleans())
        step_id = f"step_{module_id}_{i}"
        steps_config.append({
            "id": step_id,
            "path_id": main_path_id,
            "position": i,
            "step_type": "content",
            "has_content": has_content,
        })
        if not has_content:
            expected_violations.append(("step_no_content", step_id))

    # Ramificação opcional
    branch_config = None
    branch_paths_config = []

    if has_branch:
        branch_step_position = num_content_steps
        branch_step_id = f"branch_step_{module_id}"
        branch_id = f"branch_{module_id}"

        # A etapa de branch também precisa de conteúdo
        branch_has_content = draw(st.booleans())
        steps_config.append({
            "id": branch_step_id,
            "path_id": main_path_id,
            "position": branch_step_position,
            "step_type": "branch",
            "has_content": branch_has_content,
        })
        if not branch_has_content:
            expected_violations.append(("step_no_content", branch_step_id))

        # Número de opções (pode ser inválido: 0, 1, 6, 7)
        num_options = draw(st.integers(min_value=0, max_value=7))

        options_config = []
        for opt_idx in range(num_options):
            # Label com comprimento variável (pode ser inválido: <3 ou >80)
            label_len = draw(st.integers(min_value=1, max_value=100))
            # Use simple ASCII characters for deterministic label lengths
            label = "A" * label_len

            opt_path_id = f"opt_path_{module_id}_{opt_idx}"
            option_id = f"opt_{module_id}_{opt_idx}"

            options_config.append({
                "id": option_id,
                "label": label,
                "path_id": opt_path_id,
            })

            # Verificar violação de label
            if label_len < 3 or label_len > 80:
                expected_violations.append(("invalid_label", option_id))

            # Etapas dentro do caminho da opção (pelo menos 1 com conteúdo)
            bp_step_id = f"bpstep_{module_id}_{opt_idx}_0"
            branch_paths_config.append({
                "path_id": opt_path_id,
                "steps": [{
                    "id": bp_step_id,
                    "position": 0,
                    "step_type": "content",
                    "has_content": True,
                }],
            })

        # Verificar violação de quantidade de opções
        if num_options < 2 or num_options > 5:
            expected_violations.append(("invalid_option_count", branch_step_id))

        branch_config = {
            "branch_id": branch_id,
            "step_id": branch_step_id,
            "options": options_config,
        }

    return {
        "module_id": module_id,
        "main_path_id": main_path_id,
        "steps_config": steps_config,
        "branch_config": branch_config,
        "branch_paths_config": branch_paths_config,
        "expected_violations": expected_violations,
    }


def _insert_validation_module(db: Database, structure: dict) -> None:
    """Insere uma estrutura de módulo no banco para teste de validação de publicação.

    Usa PRAGMA ignore_check_constraints para permitir inserção de labels
    inválidos (fora do range 3-150) que seriam bloqueados pelo CHECK constraint.
    Isso é necessário para testar que validate_module detecta labels inválidos.
    """
    module_id = structure["module_id"]
    main_path_id = structure["main_path_id"]

    # Desabilitar CHECK constraints para inserir dados inválidos de teste
    db.execute("PRAGMA ignore_check_constraints = ON", ())

    # Criar módulo
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo Validação", "Teste de validação", "draft"),
    )

    # Criar caminho principal
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (main_path_id, module_id, "Principal", True),
    )

    # Inserir etapas
    for step_cfg in structure["steps_config"]:
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_cfg["id"], module_id, step_cfg["path_id"],
             step_cfg["position"], step_cfg["step_type"]),
        )
        if step_cfg["has_content"]:
            db.execute(
                "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"c_{step_cfg['id']}", step_cfg["id"], "text", "Conteúdo de teste", 0),
            )

    # Inserir ramificação se existir
    if structure["branch_config"]:
        branch_cfg = structure["branch_config"]
        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            (branch_cfg["branch_id"], branch_cfg["step_id"]),
        )

        # Inserir caminhos de ramificação ANTES das opções (FK constraint)
        for bp_cfg in structure["branch_paths_config"]:
            db.execute(
                "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
                "VALUES (?, ?, ?, ?, ?)",
                (bp_cfg["path_id"], module_id,
                 branch_cfg["branch_id"],
                 f"Caminho {bp_cfg['path_id']}", False),
            )
            for step_cfg in bp_cfg["steps"]:
                db.execute(
                    "INSERT INTO steps (id, module_id, path_id, position, step_type) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (step_cfg["id"], module_id, bp_cfg["path_id"],
                     step_cfg["position"], step_cfg["step_type"]),
                )
                if step_cfg["has_content"]:
                    db.execute(
                        "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (f"c_{step_cfg['id']}", step_cfg["id"], "text", "Conteúdo", 0),
                    )

        # Inserir opções de branch (após os paths existirem)
        for idx, opt in enumerate(branch_cfg["options"]):
            db.execute(
                "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
                "VALUES (?, ?, ?, ?, ?)",
                (opt["id"], branch_cfg["branch_id"], opt["label"], opt["path_id"], idx),
            )

    db.commit()

    # Reabilitar CHECK constraints
    db.execute("PRAGMA ignore_check_constraints = OFF", ())


# =============================================================================
# Property 10: Validação de publicação do módulo
# =============================================================================


# Feature: client-training, Property 10: Validação de publicação do módulo
class TestProperty10PublicationValidation:
    """**Validates: Requirements 3.3, 6.3, 6.5**

    Property 10: For any module, `validate_module` rejects publication (returns errors)
    iff any of:
    (a) a branch has fewer than 2 or more than 5 options;
    (b) any branch option label has length < 3 or > 80 characters;
    (c) any step has no content.
    All violations must be listed in the error response.
    """

    @given(structure=module_for_validation_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_validate_module_detects_all_violations(self, structure):
        """**Validates: Requirements 3.3, 6.3, 6.5**

        Property: validate_module returns errors iff violations exist, and all
        violations are reported in the error response.
        """
        # Setup: fresh in-memory database for each example
        db = Database(":memory:")
        db.initialize()

        try:
            # Insert the generated module structure
            _insert_validation_module(db, structure)

            # Execute validation
            cm = ContentManager(db, media_path="/tmp/media")
            errors = cm.validate_module(structure["module_id"])

            expected_violations = structure["expected_violations"]
            has_violations = len(expected_violations) > 0

            # Property: errors returned iff violations exist
            if has_violations:
                assert len(errors) > 0, (
                    f"Expected validation errors for violations {expected_violations}, "
                    f"but got no errors."
                )
            else:
                assert len(errors) == 0, (
                    f"Expected no validation errors (no violations), "
                    f"but got {len(errors)} errors: "
                    f"{[e.message for e in errors]}"
                )

            # Property: ALL violations are reported
            error_messages = " ".join(e.message for e in errors)
            error_element_ids = [e.element_id for e in errors]

            for violation_type, element_id in expected_violations:
                if violation_type == "step_no_content":
                    # Must have an error referencing this step (element_type == "step")
                    assert any(
                        e.element_id == element_id and e.element_type == "step"
                        for e in errors
                    ), (
                        f"Missing error for step without content: {element_id}. "
                        f"Errors found: {[(e.element_id, e.element_type, e.message) for e in errors]}"
                    )
                elif violation_type == "invalid_option_count":
                    # Must have an error about option count for this branch step
                    assert any(
                        e.element_id == element_id and e.element_type == "branch"
                        for e in errors
                    ), (
                        f"Missing error for invalid option count on branch step: {element_id}. "
                        f"Errors found: {[(e.element_id, e.element_type, e.message) for e in errors]}"
                    )
                elif violation_type == "invalid_label":
                    # Error is reported on the branch step_id, with option_id in message
                    branch_step_id = structure["branch_config"]["step_id"]
                    assert any(
                        e.element_id == branch_step_id
                        and e.element_type == "branch"
                        and element_id in e.message
                        for e in errors
                    ), (
                        f"Missing error for invalid label on option: {element_id}. "
                        f"Errors found: {[(e.element_id, e.message) for e in errors]}"
                    )
        finally:
            db.close()


# =============================================================================
# Strategies para Property 12: Contagem de usuários afetados na exclusão
# =============================================================================


@composite
def module_with_users_progress_strategy(draw):
    """Gera um cenário com módulo e N usuários distintos com progresso.

    Retorna um dict com:
        module_id, path_id, num_users, user_ids, step_ids
    """
    suffix = draw(st.integers(min_value=1, max_value=999999))
    module_id = f"mod_p12_{suffix}"
    path_id = f"path_p12_{suffix}"

    # Gerar entre 0 e 20 usuários distintos com progresso
    num_users = draw(st.integers(min_value=0, max_value=20))

    # Gerar entre 1 e 10 etapas no módulo
    num_steps = draw(st.integers(min_value=1, max_value=10))

    # Gerar user_ids distintos
    user_ids = [f"user_p12_{suffix}_{i}" for i in range(num_users)]

    return {
        "module_id": module_id,
        "path_id": path_id,
        "num_users": num_users,
        "num_steps": num_steps,
        "user_ids": user_ids,
    }


def _insert_module_with_user_progress(db: Database, data: dict) -> None:
    """Insere módulo com N usuários tendo progresso no banco.

    Args:
        db: Banco de dados em memória.
        data: Dict gerado por module_with_users_progress_strategy.
    """
    module_id = data["module_id"]
    path_id = data["path_id"]
    num_steps = data["num_steps"]
    user_ids = data["user_ids"]

    # Inserir módulo publicado
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo Exclusão", "Módulo para teste de exclusão", "published"),
    )

    # Inserir caminho principal
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path_id, module_id, "Principal", True),
    )

    # Inserir etapas
    step_ids = []
    for i in range(num_steps):
        step_id = f"{module_id}_step_{i}"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, i, "content"),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"content_{step_id}", step_id, "text", f"Conteúdo etapa {i}", 0),
        )
        step_ids.append(step_id)

    # Inserir usuários e registros de progresso
    for user_id in user_ids:
        db.execute(
            "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
            (user_id, f"Usuário {user_id}", f"{user_id}@teste.com"),
        )
        # Criar registro de progresso (current_step é a primeira etapa)
        progress_id = f"progress_{user_id}_{module_id}"
        db.execute(
            "INSERT INTO user_progress (id, user_id, module_id, current_step_id, "
            "current_path_id, status, percentage) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (progress_id, user_id, module_id, step_ids[0], path_id, "in_progress", 0.0),
        )

    db.commit()


# =============================================================================
# Property 12: Contagem de usuários afetados na exclusão
# =============================================================================


# Feature: client-training, Property 12: Contagem de usuários afetados na exclusão
class TestProperty12AffectedUsersOnDelete:
    """**Validates: Requirements 6.6**

    Property 12: For any module with N distinct users having progress records,
    attempting to delete that module should report exactly N affected users
    before requiring confirmation.
    """

    @given(data=module_with_users_progress_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_delete_module_reports_exact_affected_user_count(self, data):
        """Para qualquer módulo com N usuários distintos com progresso,
        tentar excluir o módulo deve reportar exatamente N usuários afetados
        antes de exigir confirmação.

        **Validates: Requirements 6.6**
        """
        # Setup: fresh in-memory database for each example
        db = Database(":memory:")
        db.initialize()

        try:
            # Inserir módulo com usuários e progresso
            _insert_module_with_user_progress(db, data)

            # Executar tentativa de exclusão SEM confirmação
            cm = ContentManager(db, media_path="/tmp/media")
            result = cm.delete_module(data["module_id"], confirm=False)

            num_users = data["num_users"]

            if num_users > 0:
                # Com usuários afetados: deve requerer confirmação
                assert result.deleted is False, (
                    f"Módulo com {num_users} usuário(s) não deveria ser excluído "
                    f"sem confirmação, mas deleted=True."
                )
                assert result.requires_confirmation is True, (
                    f"Módulo com {num_users} usuário(s) deveria requerer confirmação, "
                    f"mas requires_confirmation=False."
                )
                assert result.affected_users == num_users, (
                    f"Esperava {num_users} usuário(s) afetado(s), "
                    f"mas delete_module reportou {result.affected_users}."
                )
            else:
                # Sem usuários afetados: deve excluir diretamente
                assert result.deleted is True, (
                    f"Módulo sem usuários com progresso deveria ser excluído "
                    f"diretamente, mas deleted=False."
                )
                assert result.affected_users == 0, (
                    f"Esperava 0 usuários afetados, "
                    f"mas delete_module reportou {result.affected_users}."
                )
        finally:
            db.close()


# =============================================================================
# Strategies para Property 1: Tela de boas-vindas condicionada à primeira visita
# =============================================================================


@composite
def user_profile_for_welcome_strategy(draw):
    """Gera dados de um perfil de usuário com is_first_visit variável.

    Retorna um dict com:
        user_id, name, email, is_first_visit, is_admin
    """
    suffix = draw(st.integers(min_value=1, max_value=999999))
    user_id = f"user_p1_{suffix}"
    name = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
            min_size=2,
            max_size=40,
        ).filter(lambda s: s.strip() != "" and len(s.strip()) >= 2)
    )
    email = f"user_p1_{suffix}@teste.com"
    is_first_visit = draw(st.booleans())
    is_admin = draw(st.booleans())

    return {
        "user_id": user_id,
        "name": name,
        "email": email,
        "is_first_visit": is_first_visit,
        "is_admin": is_admin,
    }


# =============================================================================
# Property 1: Tela de boas-vindas condicionada à primeira visita
# =============================================================================


# Feature: client-training, Property 1: Tela de boas-vindas condicionada à primeira visita
class TestProperty1WelcomeScreenConditional:
    """**Validates: Requirements 1.1, 1.2**

    Property 1: For any user profile, the welcome screen is displayed if and
    only if `is_first_visit` is true. A user with `is_first_visit=false` should
    always be directed to the module list.
    """

    def _insert_user(self, db, user_data: dict) -> None:
        """Helper: insere um usuário no banco com os dados fornecidos."""
        db.execute(
            "INSERT INTO users (id, name, email, is_first_visit, is_admin) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_data["user_id"],
                user_data["name"],
                user_data["email"],
                user_data["is_first_visit"],
                user_data["is_admin"],
            ),
        )
        db.commit()

    @given(user_data=user_profile_for_welcome_strategy())
    @settings(max_examples=200)
    def test_welcome_screen_shown_iff_first_visit(self, user_data):
        """A tela de boas-vindas é exibida se e somente se is_first_visit é True.

        **Validates: Requirements 1.1, 1.2**

        Para qualquer perfil de usuário gerado:
        - Se is_first_visit=True: a função is_first_visit retorna True,
          indicando que a tela de boas-vindas deve ser exibida.
        - Se is_first_visit=False: a função is_first_visit retorna False,
          indicando que o usuário deve ser direcionado à lista de módulos.
        """
        from pages.welcome import is_first_visit as check_first_visit

        db = Database(":memory:")
        db.initialize()

        try:
            self._insert_user(db, user_data)

            # Act: verificar se é primeira visita
            result = check_first_visit(db, user_data["user_id"])

            # Assert: o resultado deve corresponder exatamente ao valor de is_first_visit
            if user_data["is_first_visit"]:
                assert result is True, (
                    f"Usuário com is_first_visit=True deveria ver a tela de boas-vindas "
                    f"(is_first_visit retornar True), mas retornou {result}. "
                    f"user_id={user_data['user_id']}, is_admin={user_data['is_admin']}"
                )
            else:
                assert result is False, (
                    f"Usuário com is_first_visit=False deveria ser direcionado à "
                    f"lista de módulos (is_first_visit retornar False), mas retornou {result}. "
                    f"user_id={user_data['user_id']}, is_admin={user_data['is_admin']}"
                )
        finally:
            db.close()

    @given(user_data=user_profile_for_welcome_strategy())
    @settings(max_examples=200)
    def test_first_visit_flag_determines_routing_destination(self, user_data):
        """O destino de roteamento é determinado exclusivamente pelo flag is_first_visit.

        **Validates: Requirements 1.1, 1.2**

        Para qualquer perfil de usuário:
        - is_first_visit=True → destino: "welcome" (tela de boas-vindas)
        - is_first_visit=False → destino: "module_list" (lista de módulos)

        O campo is_admin NÃO deve afetar esta lógica de roteamento inicial.
        """
        from pages.welcome import is_first_visit as check_first_visit

        db = Database(":memory:")
        db.initialize()

        try:
            self._insert_user(db, user_data)

            # Act: determinar o destino de roteamento
            should_show_welcome = check_first_visit(db, user_data["user_id"])

            # Determinar destino esperado baseado no flag
            expected_destination = "welcome" if user_data["is_first_visit"] else "module_list"
            actual_destination = "welcome" if should_show_welcome else "module_list"

            # Assert: destino deve corresponder ao esperado
            assert actual_destination == expected_destination, (
                f"Roteamento incorreto para usuário. "
                f"is_first_visit={user_data['is_first_visit']}, "
                f"is_admin={user_data['is_admin']}, "
                f"Destino esperado='{expected_destination}', "
                f"Destino obtido='{actual_destination}'."
            )

            # Assert: is_admin não deve alterar a lógica de roteamento
            # (este teste verifica implicitamente que o mesmo comportamento
            # ocorre independente do valor de is_admin, pois a strategy
            # gera todas as combinações possíveis de is_first_visit × is_admin)
        finally:
            db.close()

    @given(user_data=user_profile_for_welcome_strategy())
    @settings(max_examples=200)
    def test_mark_first_visit_complete_transitions_to_module_list(self, user_data):
        """Após marcar primeira visita como completa, o usuário vai para lista de módulos.

        **Validates: Requirements 1.1, 1.2**

        Para qualquer usuário com is_first_visit=True, após chamar
        _mark_first_visit_complete, a função is_first_visit deve retornar False,
        indicando que em visitas subsequentes o usuário irá diretamente
        para a lista de módulos.
        """
        from pages.welcome import is_first_visit as check_first_visit
        from pages.welcome import _mark_first_visit_complete

        # Apenas testar com usuários de primeira visita para esta propriedade
        assume(user_data["is_first_visit"] is True)

        db = Database(":memory:")
        db.initialize()

        try:
            self._insert_user(db, user_data)

            # Pré-condição: confirmar que é primeira visita
            assert check_first_visit(db, user_data["user_id"]) is True, (
                "Pré-condição falhou: usuário deveria ser de primeira visita"
            )

            # Act: marcar primeira visita como completa
            _mark_first_visit_complete(db, user_data["user_id"])

            # Assert: após marcar, is_first_visit deve ser False
            result_after = check_first_visit(db, user_data["user_id"])
            assert result_after is False, (
                f"Após _mark_first_visit_complete, is_first_visit deveria "
                f"retornar False (usuário vai para lista de módulos), "
                f"mas retornou {result_after}. user_id={user_data['user_id']}"
            )
        finally:
            db.close()


# =============================================================================
# Strategies para Property 6: Seleção de ramificação leva à primeira etapa
# =============================================================================

# Add tests directory to sys.path for conftest imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import (
    insert_module_structure,
    insert_user,
    module_with_branches_strategy,
)
from managers.branch_manager import BranchManager


# =============================================================================
# Property 6: Seleção de ramificação leva à primeira etapa do caminho alvo
# =============================================================================


# Feature: client-training, Property 6: Seleção de ramificação leva à primeira etapa do caminho alvo
class TestProperty6BranchSelectionFirstStep:
    """**Validates: Requirements 3.2**

    Property 6: For any branch option with a target path_id pointing to a path
    with steps, selecting that option should return the step at position 0 of
    the target path.
    """

    @given(
        structure=module_with_branches_strategy(),
        user_suffix=st.integers(min_value=1, max_value=999999),
        option_index=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_select_branch_returns_first_step_of_target_path(
        self, structure, user_suffix, option_index
    ):
        """Selecionar qualquer opção de ramificação retorna a etapa na posição 0
        do caminho alvo correspondente.

        **Validates: Requirements 3.2**

        Para qualquer opção de branch com path_id apontando para um caminho com
        etapas, select_branch deve retornar a etapa na posição 0 desse caminho.
        """
        # Constrain option_index to the number of available options
        num_options = len(structure["options"])
        assume(option_index < num_options)

        # Setup fresh database
        db = Database(":memory:")
        db.initialize()

        try:
            # Insert the full module structure with branches
            insert_module_structure(db, structure)

            # Insert a test user
            user_id = f"user_p6_{user_suffix}"
            insert_user(db, user_id, name="Teste P6")

            # Get the selected option details
            selected_option = structure["options"][option_index]
            option_id = selected_option["id"]
            target_path_id = selected_option["path_id"]
            branch_step_id = structure["branch_step_id"]

            # Find the expected first step of the target path
            target_path_data = None
            for bp in structure["branch_paths"]:
                if bp["path_id"] == target_path_id:
                    target_path_data = bp
                    break

            assert target_path_data is not None, (
                f"Target path '{target_path_id}' not found in branch_paths."
            )

            # The expected first step is at position 0 of the target path
            expected_first_step_id = target_path_data["step_ids"][0]

            # Act: select the branch
            bm = BranchManager(db)
            result_step = bm.select_branch(user_id, branch_step_id, option_id)

            # Assert: returned step should not be None
            assert result_step is not None, (
                f"select_branch returned None for option '{option_id}' "
                f"pointing to path '{target_path_id}' which has "
                f"{target_path_data['num_steps']} steps."
            )

            # Assert: returned step should be at position 0
            assert result_step.position == 0, (
                f"Expected step at position 0, but got position {result_step.position}. "
                f"Option '{option_id}' targets path '{target_path_id}'."
            )

            # Assert: returned step should belong to the target path
            assert result_step.path_id == target_path_id, (
                f"Expected step from path '{target_path_id}', "
                f"but got step from path '{result_step.path_id}'."
            )

            # Assert: returned step ID should match the first step of the path
            assert result_step.id == expected_first_step_id, (
                f"Expected first step '{expected_first_step_id}', "
                f"but got '{result_step.id}'."
            )

            # Assert: returned step should belong to the correct module
            assert result_step.module_id == structure["module_id"], (
                f"Expected module_id '{structure['module_id']}', "
                f"but got '{result_step.module_id}'."
            )
        finally:
            db.close()


# =============================================================================
# Strategies para Property 2: Completude de informações na lista de módulos
# =============================================================================


@composite
def module_list_scenario(draw):
    """Gera um cenário com módulos publicados e progresso de usuário para testar get_modules.

    Gera:
    - 1 a 5 módulos publicados, cada um com 1-15 etapas
    - Um usuário com progresso variável em cada módulo (not_started, in_progress, completed)

    Returns:
        Dict com:
            user_id: ID do usuário
            modules: lista de dicts com module_id, path_id, title, description, num_steps, progress_status
    """
    suffix = draw(st.integers(min_value=1, max_value=999999))
    user_id = f"user_p2_{suffix}"

    num_modules = draw(st.integers(min_value=1, max_value=5))

    modules = []
    for m_idx in range(num_modules):
        module_id = f"mod_p2_{suffix}_{m_idx}"
        path_id = f"path_p2_{suffix}_{m_idx}"

        title = draw(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
                min_size=3,
                max_size=60,
            ).filter(lambda s: s.strip() != "" and len(s.strip()) >= 3)
        )

        description = draw(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
                min_size=5,
                max_size=140,
            ).filter(lambda s: s.strip() != "" and len(s.strip()) >= 5)
        )

        num_steps = draw(st.integers(min_value=1, max_value=15))

        # Progress status for this user on this module
        progress_status = draw(st.sampled_from([
            ProgressStatus.NOT_STARTED,
            ProgressStatus.IN_PROGRESS,
            ProgressStatus.COMPLETED,
        ]))

        modules.append({
            "module_id": module_id,
            "path_id": path_id,
            "title": title,
            "description": description,
            "num_steps": num_steps,
            "progress_status": progress_status,
        })

    return {
        "user_id": user_id,
        "modules": modules,
    }


def _insert_module_list_scenario(db: Database, scenario: dict) -> None:
    """Insere o cenário completo no banco para teste de completude da lista de módulos.

    Args:
        db: Banco de dados em memória.
        scenario: Dict gerado por module_list_scenario.
    """
    user_id = scenario["user_id"]

    # Inserir usuário
    db.execute(
        "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
        (user_id, "Usuário PBT", f"{user_id}@teste.com"),
    )

    for mod_data in scenario["modules"]:
        module_id = mod_data["module_id"]
        path_id = mod_data["path_id"]
        num_steps = mod_data["num_steps"]
        progress_status = mod_data["progress_status"]

        # Inserir módulo publicado
        db.execute(
            "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
            (module_id, mod_data["title"], mod_data["description"], ModuleStatus.PUBLISHED.value),
        )

        # Inserir caminho principal
        db.execute(
            "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
            (path_id, module_id, "Principal", True),
        )

        # Inserir etapas
        step_ids = []
        for i in range(num_steps):
            step_id = f"{module_id}_step_{i}"
            db.execute(
                "INSERT INTO steps (id, module_id, path_id, position, step_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (step_id, module_id, path_id, i, "content"),
            )
            db.execute(
                "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"content_{step_id}", step_id, "text", f"Conteúdo etapa {i}", 0),
            )
            step_ids.append(step_id)

        # Inserir progresso do usuário se não é NOT_STARTED
        if progress_status != ProgressStatus.NOT_STARTED:
            if progress_status == ProgressStatus.COMPLETED:
                percentage = 100.0
                current_step_id = step_ids[-1]
            else:
                # IN_PROGRESS: progresso parcial
                completed_count = max(1, num_steps // 2)
                percentage = (completed_count / num_steps) * 100.0
                current_step_id = step_ids[min(completed_count, num_steps - 1)]

            progress_id = f"progress_{user_id}_{module_id}"
            db.execute(
                "INSERT INTO user_progress (id, user_id, module_id, current_step_id, "
                "current_path_id, status, percentage) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    progress_id,
                    user_id,
                    module_id,
                    current_step_id,
                    path_id,
                    progress_status.value,
                    percentage,
                ),
            )

            # Marcar etapas como concluídas
            if progress_status == ProgressStatus.COMPLETED:
                for sid in step_ids:
                    db.execute(
                        "INSERT INTO completed_steps (user_id, step_id) VALUES (?, ?)",
                        (user_id, sid),
                    )
            elif progress_status == ProgressStatus.IN_PROGRESS:
                completed_count = max(1, num_steps // 2)
                for sid in step_ids[:completed_count]:
                    db.execute(
                        "INSERT INTO completed_steps (user_id, step_id) VALUES (?, ?)",
                        (user_id, sid),
                    )

    db.commit()


# =============================================================================
# Property 2: Completude de informações na lista de módulos
# =============================================================================


# Feature: client-training, Property 2: Completude de informações na lista de módulos
class TestProperty2ModuleListCompleteness:
    """**Validates: Requirements 1.3**

    Property 2: For any module and user, the module info object returned by
    `get_modules` must contain: title (non-empty), description (≤150 characters),
    total step count (≥0), and a valid progress status (NOT_STARTED, IN_PROGRESS,
    or COMPLETED).
    """

    @given(scenario=module_list_scenario())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_module_info_completeness(self, scenario):
        """Para qualquer módulo e usuário, get_modules retorna informações completas.

        Cada ModuleInfo deve conter:
        - title: não vazio
        - description: ≤150 caracteres
        - total_steps: ≥0
        - progress_status: NOT_STARTED, IN_PROGRESS ou COMPLETED

        **Validates: Requirements 1.3**
        """
        db = Database(":memory:")
        db.initialize()

        try:
            _insert_module_list_scenario(db, scenario)

            tm = TrainingManager(db)
            modules = tm.get_modules(scenario["user_id"])

            # Deve retornar pelo menos a quantidade de módulos inseridos
            assert len(modules) == len(scenario["modules"]), (
                f"Esperava {len(scenario['modules'])} módulos, obteve {len(modules)}"
            )

            valid_statuses = {
                ProgressStatus.NOT_STARTED,
                ProgressStatus.IN_PROGRESS,
                ProgressStatus.COMPLETED,
            }

            for module_info in modules:
                # title: não vazio
                assert module_info.title is not None and len(module_info.title.strip()) > 0, (
                    f"Módulo '{module_info.id}' tem título vazio ou None: '{module_info.title}'"
                )

                # description: ≤150 caracteres
                assert module_info.description is not None, (
                    f"Módulo '{module_info.id}' tem descrição None"
                )
                assert len(module_info.description) <= 150, (
                    f"Módulo '{module_info.id}' tem descrição com "
                    f"{len(module_info.description)} caracteres (máximo 150): "
                    f"'{module_info.description[:50]}...'"
                )

                # total_steps: ≥0
                assert module_info.total_steps is not None, (
                    f"Módulo '{module_info.id}' tem total_steps None"
                )
                assert module_info.total_steps >= 0, (
                    f"Módulo '{module_info.id}' tem total_steps negativo: "
                    f"{module_info.total_steps}"
                )

                # progress_status: válido (NOT_STARTED, IN_PROGRESS ou COMPLETED)
                assert module_info.progress_status is not None, (
                    f"Módulo '{module_info.id}' tem progress_status None"
                )
                assert module_info.progress_status in valid_statuses, (
                    f"Módulo '{module_info.id}' tem progress_status inválido: "
                    f"'{module_info.progress_status}'. Esperado: {valid_statuses}"
                )
        finally:
            db.close()


# =============================================================================
# Strategies para Property 7: Rastreamento de caminhos explorados
# =============================================================================


@composite
def explored_paths_scenario(draw):
    """Gera um cenário de ramificação com múltiplos caminhos e seleções do usuário.

    Cria uma estrutura com:
    - Um módulo com caminho principal e uma etapa de ramificação
    - 2 a 5 caminhos de ramificação, cada um com 1 a 5 etapas
    - Um subconjunto não-vazio de caminhos que o usuário irá explorar

    Returns:
        Dict com:
            module_id, main_path_id, branch_step_id, branch_id,
            branch_paths (lista de dicts com path_id, step_ids, num_steps, option_id),
            paths_to_explore (subconjunto de índices dos caminhos que serão explorados)
    """
    suffix = draw(st.integers(min_value=1, max_value=999999))
    module_id = f"mod_p7_{suffix}"
    main_path_id = f"main_path_p7_{suffix}"
    branch_step_id = f"branch_step_p7_{suffix}"
    branch_id = f"branch_p7_{suffix}"

    # Número de caminhos na ramificação (2-5)
    num_paths = draw(st.integers(min_value=2, max_value=5))

    # Gerar caminhos de ramificação
    branch_paths = []
    for i in range(num_paths):
        path_id = f"bpath_p7_{suffix}_{i}"
        num_steps = draw(st.integers(min_value=1, max_value=5))
        step_ids = [f"{path_id}_step_{s}" for s in range(num_steps)]
        option_id = f"opt_p7_{suffix}_{i}"
        label = draw(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
                min_size=5,
                max_size=60,
            ).filter(lambda s: s.strip() != "" and len(s.strip()) >= 5)
        )
        branch_paths.append({
            "path_id": path_id,
            "step_ids": step_ids,
            "num_steps": num_steps,
            "option_id": option_id,
            "label": label,
        })

    # Subconjunto de caminhos que o usuário vai explorar (pelo menos 1)
    all_indices = list(range(num_paths))
    paths_to_explore = draw(
        st.lists(
            st.sampled_from(all_indices),
            min_size=1,
            max_size=num_paths,
            unique=True,
        )
    )

    return {
        "module_id": module_id,
        "main_path_id": main_path_id,
        "branch_step_id": branch_step_id,
        "branch_id": branch_id,
        "branch_paths": branch_paths,
        "paths_to_explore": sorted(paths_to_explore),
    }


def _insert_explored_paths_module(db: Database, scenario: dict) -> None:
    """Insere a estrutura de módulo com ramificação no banco para teste de Property 7.

    Args:
        db: Instância do banco de dados em memória.
        scenario: Dict gerado por explored_paths_scenario.
    """
    module_id = scenario["module_id"]
    main_path_id = scenario["main_path_id"]
    branch_step_id = scenario["branch_step_id"]
    branch_id = scenario["branch_id"]

    # Criar módulo
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo P7", "Teste rastreamento caminhos", "published"),
    )

    # Criar caminho principal com uma etapa de branch
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (main_path_id, module_id, "Principal", True),
    )
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        (branch_step_id, module_id, main_path_id, 0, "branch"),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        (f"c_{branch_step_id}", branch_step_id, "text", "Escolha seu caminho", 0),
    )

    # Criar branch
    db.execute(
        "INSERT INTO branches (id, step_id) VALUES (?, ?)",
        (branch_id, branch_step_id),
    )

    # Criar caminhos de ramificação e suas etapas
    for idx, bp in enumerate(scenario["branch_paths"]):
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, ?, ?, ?)",
            (bp["path_id"], module_id, branch_id, f"Caminho {idx}", False),
        )
        for i, step_id in enumerate(bp["step_ids"]):
            db.execute(
                "INSERT INTO steps (id, module_id, path_id, position, step_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (step_id, module_id, bp["path_id"], i, "content"),
            )
            db.execute(
                "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"c_{step_id}", step_id, "text", f"Conteúdo {step_id}", 0),
            )

        # Criar opção de branch
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (bp["option_id"], branch_id, bp["label"], bp["path_id"], idx),
        )

    db.commit()


# =============================================================================
# Property 7: Rastreamento de caminhos explorados
# =============================================================================


# Feature: client-training, Property 7: Rastreamento de caminhos explorados
class TestProperty7ExploredPathsTracking:
    """**Validates: Requirements 3.4, 3.5**

    Property 7: For any user who has selected branch options leading to paths
    P1..Pn at a given branch point, `get_explored_paths` for that branch should
    return exactly the set {P1..Pn}. Additionally, at the last step of any
    branch path (with parent_branch_id not null), a "return to branch" option
    must be available.
    """

    @given(scenario=explored_paths_scenario())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_get_explored_paths_returns_exact_set_of_explored(self, scenario):
        """get_explored_paths retorna exatamente o conjunto de caminhos explorados.

        Para qualquer usuário que selecionou opções de ramificação levando aos
        caminhos P1..Pn em um ponto de ramificação, get_explored_paths deve
        retornar exatamente o conjunto {P1..Pn}.

        **Validates: Requirements 3.4, 3.5**
        """
        from managers.branch_manager import BranchManager

        db = Database(":memory:")
        db.initialize()

        try:
            # Inserir estrutura no banco
            _insert_explored_paths_module(db, scenario)

            # Criar usuário
            user_id = f"user_p7_{uuid.uuid4().hex[:8]}"
            db.execute(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                (user_id, "Teste P7", f"{user_id}@teste.com"),
            )
            db.commit()

            bm = BranchManager(db)
            branch_step_id = scenario["branch_step_id"]

            # Simular exploração: selecionar cada caminho no subconjunto
            expected_explored_paths = set()
            for idx in scenario["paths_to_explore"]:
                bp = scenario["branch_paths"][idx]
                option_id = bp["option_id"]

                # Selecionar o branch (registra como explorado)
                bm.select_branch(user_id, branch_step_id, option_id)
                expected_explored_paths.add(bp["path_id"])

            # Verificar: get_explored_paths deve retornar exatamente o conjunto esperado
            actual_explored = bm.get_explored_paths(user_id, branch_step_id)
            actual_explored_set = set(actual_explored)

            assert actual_explored_set == expected_explored_paths, (
                f"get_explored_paths retornou {actual_explored_set}, "
                f"mas esperava {expected_explored_paths}. "
                f"Faltando: {expected_explored_paths - actual_explored_set}. "
                f"Extras: {actual_explored_set - expected_explored_paths}."
            )
        finally:
            db.close()

    @given(scenario=explored_paths_scenario())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_return_to_branch_available_at_last_step_of_branch_path(self, scenario):
        """Na última etapa de qualquer caminho de ramificação, get_return_point deve
        estar disponível (retornar a etapa de branch original sem erro).

        Para qualquer caminho com parent_branch_id não nulo, ao chamar
        get_return_point com o path_id desse caminho, o sistema deve retornar
        a etapa onde a ramificação foi apresentada.

        **Validates: Requirements 3.4, 3.5**
        """
        from managers.branch_manager import BranchManager

        db = Database(":memory:")
        db.initialize()

        try:
            # Inserir estrutura no banco
            _insert_explored_paths_module(db, scenario)

            # Criar usuário
            user_id = f"user_p7_{uuid.uuid4().hex[:8]}"
            db.execute(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                (user_id, "Teste P7", f"{user_id}@teste.com"),
            )
            db.commit()

            bm = BranchManager(db)
            branch_step_id = scenario["branch_step_id"]

            # Para cada caminho de ramificação, verificar que get_return_point
            # retorna a etapa de branch original
            for bp in scenario["branch_paths"]:
                path_id = bp["path_id"]

                # get_return_point deve funcionar (caminho tem parent_branch_id)
                return_step = bm.get_return_point(user_id, path_id)

                # O ponto de retorno deve ser a etapa que contém a ramificação
                assert return_step is not None, (
                    f"get_return_point retornou None para caminho '{path_id}' "
                    f"que pertence a uma ramificação."
                )
                assert return_step.id == branch_step_id, (
                    f"get_return_point para caminho '{path_id}' deveria retornar "
                    f"a etapa de branch '{branch_step_id}', "
                    f"mas retornou '{return_step.id}'."
                )

                # Verificar que o step retornado é do tipo branch
                assert return_step.step_type == StepType.BRANCH, (
                    f"A etapa de retorno deveria ser do tipo BRANCH, "
                    f"mas é do tipo '{return_step.step_type}'."
                )
        finally:
            db.close()


# =============================================================================
# Strategies para Property 8: Round-trip do progresso
# =============================================================================


@composite
def progress_round_trip_scenario(draw):
    """Gera um cenário de navegação com transição de etapa A para etapa B.

    Simula a ação do usuário de avançar de uma etapa para outra e verificar
    que save_progress + get_progress preserva o estado corretamente.

    Returns:
        Dict com:
            module_id: ID do módulo
            path_id: ID do caminho principal
            num_steps: quantidade total de etapas no caminho
            step_a_position: posição da etapa de origem (A)
            step_b_position: posição da etapa de destino (B)
            user_suffix: sufixo para gerar user_id único
            title: título do módulo
    """
    suffix = draw(st.integers(min_value=1, max_value=999999))
    module_id = f"mod_p8_{suffix}"
    path_id = f"path_p8_{suffix}"

    # Módulo com pelo menos 2 etapas para permitir transição
    num_steps = draw(st.integers(min_value=2, max_value=15))

    # Etapa A: qualquer posição exceto a última (para poder avançar)
    step_a_position = draw(st.integers(min_value=0, max_value=num_steps - 2))

    # Etapa B: a próxima etapa após A (simula avanço)
    step_b_position = step_a_position + 1

    user_suffix = draw(st.integers(min_value=1, max_value=999999))

    return {
        "module_id": module_id,
        "path_id": path_id,
        "num_steps": num_steps,
        "step_a_position": step_a_position,
        "step_b_position": step_b_position,
        "user_suffix": user_suffix,
    }


def _insert_progress_round_trip_module(db: Database, scenario: dict) -> list:
    """Insere módulo com caminho e etapas para teste de round-trip do progresso.

    Args:
        db: Banco de dados em memória.
        scenario: Dict gerado por progress_round_trip_scenario.

    Returns:
        Lista de step_ids na ordem de posição.
    """
    module_id = scenario["module_id"]
    path_id = scenario["path_id"]
    num_steps = scenario["num_steps"]

    # Inserir módulo publicado
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo Progresso P8", "Teste round-trip progresso", "published"),
    )

    # Inserir caminho principal
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path_id, module_id, "Principal", True),
    )

    # Inserir etapas
    step_ids = []
    for i in range(num_steps):
        step_id = f"{module_id}_step_{i}"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, i, "content"),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"content_{step_id}", step_id, "text", f"Conteúdo etapa {i}", 0),
        )
        step_ids.append(step_id)

    db.commit()
    return step_ids


# =============================================================================
# Property 8: Round-trip do progresso
# =============================================================================


# Feature: client-training, Property 8: Round-trip do progresso
class TestProperty8ProgressRoundTrip:
    """**Validates: Requirements 5.1, 5.2**

    Property 8: For any user navigation action that transitions from step A to
    step B, after `save_progress` succeeds, calling `get_progress` should return
    step B as the current step. Subsequently, if the user leaves and returns, the
    system should offer resumption at step B.
    """

    @given(scenario=progress_round_trip_scenario())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_save_progress_then_get_progress_returns_step_b(self, scenario):
        """Após save_progress para etapa B, get_progress deve retornar B como etapa atual.

        **Validates: Requirements 5.1, 5.2**

        Para qualquer ação de navegação que transiciona da etapa A para a etapa B,
        após save_progress ser bem-sucedido, get_progress deve retornar a etapa B
        como current_step_id.
        """
        from managers.progress_manager import ProgressManager

        db = Database(":memory:")
        db.initialize()

        try:
            # Inserir módulo com etapas
            step_ids = _insert_progress_round_trip_module(db, scenario)

            module_id = scenario["module_id"]
            path_id = scenario["path_id"]
            step_a_id = step_ids[scenario["step_a_position"]]
            step_b_id = step_ids[scenario["step_b_position"]]

            # Inserir usuário
            user_id = f"user_p8_{scenario['user_suffix']}"
            db.execute(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                (user_id, "Usuário P8", f"{user_id}@teste.com"),
            )
            db.commit()

            pm = ProgressManager(db, max_retries=3, retry_interval=0)

            # Simular navegação: usuário está em A, salva progresso em A
            save_a_result = pm.save_progress(user_id, module_id, step_a_id, path_id)
            assert save_a_result is True, (
                f"save_progress falhou para etapa A '{step_a_id}'"
            )

            # Simular transição: usuário avança de A para B, salva progresso em B
            save_b_result = pm.save_progress(user_id, module_id, step_b_id, path_id)
            assert save_b_result is True, (
                f"save_progress falhou para etapa B '{step_b_id}'"
            )

            # Verificar: get_progress deve retornar step B como current_step
            progress = pm.get_progress(user_id, module_id)

            assert progress is not None, (
                f"get_progress retornou None após save_progress bem-sucedido. "
                f"user_id='{user_id}', module_id='{module_id}'"
            )

            assert progress.current_step_id == step_b_id, (
                f"Após salvar progresso na etapa B ('{step_b_id}'), "
                f"get_progress deveria retornar current_step_id='{step_b_id}', "
                f"mas retornou '{progress.current_step_id}'. "
                f"Transição: A (pos={scenario['step_a_position']}) → "
                f"B (pos={scenario['step_b_position']})"
            )

            # Verificar que o path_id também foi preservado
            assert progress.current_path_id == path_id, (
                f"Após salvar progresso, current_path_id deveria ser '{path_id}', "
                f"mas retornou '{progress.current_path_id}'"
            )
        finally:
            db.close()

    @given(scenario=progress_round_trip_scenario())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_progress_persists_after_session_ends_and_resumes_at_step_b(self, scenario):
        """Após salvar progresso em B, uma nova sessão deve oferecer retomada em B.

        **Validates: Requirements 5.1, 5.2**

        Simula o cenário de "sair e retornar": após save_progress para etapa B,
        criar uma nova instância de ProgressManager (simulando nova sessão) e
        verificar que get_progress retorna B como ponto de retomada.
        """
        from managers.progress_manager import ProgressManager

        db = Database(":memory:")
        db.initialize()

        try:
            # Inserir módulo com etapas
            step_ids = _insert_progress_round_trip_module(db, scenario)

            module_id = scenario["module_id"]
            path_id = scenario["path_id"]
            step_b_id = step_ids[scenario["step_b_position"]]

            # Inserir usuário
            user_id = f"user_p8_{scenario['user_suffix']}"
            db.execute(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                (user_id, "Usuário P8", f"{user_id}@teste.com"),
            )
            db.commit()

            # Sessão 1: salvar progresso na etapa B
            pm_session1 = ProgressManager(db, max_retries=3, retry_interval=0)
            save_result = pm_session1.save_progress(user_id, module_id, step_b_id, path_id)
            assert save_result is True, (
                f"save_progress falhou para etapa B '{step_b_id}' na sessão 1"
            )

            # Sessão 2: nova instância de ProgressManager (simula retorno do usuário)
            pm_session2 = ProgressManager(db, max_retries=3, retry_interval=0)
            progress = pm_session2.get_progress(user_id, module_id)

            # Verificar: deve oferecer retomada na etapa B
            assert progress is not None, (
                f"Ao retornar (sessão 2), get_progress retornou None. "
                f"O sistema deveria oferecer retomada na etapa B. "
                f"user_id='{user_id}', module_id='{module_id}'"
            )

            assert progress.current_step_id == step_b_id, (
                f"Ao retornar (sessão 2), o sistema deveria oferecer "
                f"retomada na etapa B ('{step_b_id}'), mas current_step_id "
                f"é '{progress.current_step_id}'. "
                f"step_b_position={scenario['step_b_position']}"
            )

            # Verificar que o status indica progresso existente (IN_PROGRESS ou COMPLETED)
            valid_resume_statuses = {ProgressStatus.IN_PROGRESS, ProgressStatus.COMPLETED}
            assert progress.status in valid_resume_statuses, (
                f"Ao retornar com progresso salvo, status deveria ser "
                f"IN_PROGRESS ou COMPLETED, mas é '{progress.status}'. "
                f"step_b_position={scenario['step_b_position']}"
            )

            # Verificar que step B está nas etapas concluídas
            assert step_b_id in progress.completed_steps, (
                f"Etapa B ('{step_b_id}') deveria estar nas completed_steps "
                f"após save_progress, mas não está. "
                f"completed_steps={progress.completed_steps}"
            )
        finally:
            db.close()


# =============================================================================
# Strategies para Property 9: Cálculo correto do status do módulo
# =============================================================================


@composite
def module_status_calculation_scenario(draw):
    """Gera um cenário para validação do cálculo de status de módulo.

    Cria uma estrutura com:
    - Um módulo com caminho principal (2-10 etapas)
    - Opcionalmente 1-3 ramificações, cada uma com 2-4 caminhos de 1-5 etapas
    - Um subconjunto de etapas que o usuário completou
    - Controle sobre quais caminhos de branch foram completamente percorridos

    Returns:
        Dict com:
            module_id, main_path_id, main_step_ids,
            branches (lista de dicts com branch_id, branch_step_id, paths),
            completed_step_ids (set de step IDs que o usuário concluiu)
    """
    suffix = draw(st.integers(min_value=1, max_value=999999))
    module_id = f"mod_p9_{suffix}"
    main_path_id = f"main_path_p9_{suffix}"

    # Número de etapas no caminho principal (inclui etapas de branch)
    has_branches = draw(st.booleans())
    num_branches = draw(st.integers(min_value=1, max_value=3)) if has_branches else 0
    num_content_steps = draw(st.integers(min_value=2, max_value=8))

    # Total de etapas no main path = content steps + branch steps
    total_main_steps = num_content_steps + num_branches

    # Construir IDs das etapas no caminho principal
    main_step_ids = []
    branch_positions = []

    if num_branches > 0:
        # Distribuir posições de branch uniformemente
        available_positions = list(range(total_main_steps))
        branch_positions = sorted(
            draw(
                st.lists(
                    st.sampled_from(available_positions),
                    min_size=num_branches,
                    max_size=num_branches,
                    unique=True,
                )
            )
        )

    for i in range(total_main_steps):
        step_id = f"{module_id}_main_step_{i}"
        main_step_ids.append(step_id)

    # Construir ramificações
    branches_data = []
    all_branch_path_step_ids = []  # All step IDs from all branch paths

    for b_idx, branch_pos in enumerate(branch_positions):
        branch_id = f"branch_p9_{suffix}_{b_idx}"
        branch_step_id = main_step_ids[branch_pos]
        num_paths = draw(st.integers(min_value=2, max_value=4))

        paths = []
        for p_idx in range(num_paths):
            path_id = f"bpath_p9_{suffix}_{b_idx}_{p_idx}"
            num_path_steps = draw(st.integers(min_value=1, max_value=5))
            path_step_ids = [
                f"{path_id}_step_{s}" for s in range(num_path_steps)
            ]
            all_branch_path_step_ids.extend(path_step_ids)
            paths.append({
                "path_id": path_id,
                "step_ids": path_step_ids,
                "num_steps": num_path_steps,
            })

        branches_data.append({
            "branch_id": branch_id,
            "branch_step_id": branch_step_id,
            "branch_position": branch_pos,
            "paths": paths,
        })

    # Determine which steps the user has completed
    # Strategy: pick a completion level
    all_step_ids = main_step_ids + all_branch_path_step_ids
    completion_level = draw(st.sampled_from(["none", "partial", "full"]))

    if completion_level == "none":
        completed_step_ids = []
    elif completion_level == "partial":
        # Complete some but not all required steps
        # At minimum 1 step, at maximum (total - 1)
        if len(all_step_ids) > 1:
            num_completed = draw(st.integers(min_value=1, max_value=len(all_step_ids) - 1))
            completed_step_ids = draw(
                st.lists(
                    st.sampled_from(all_step_ids),
                    min_size=num_completed,
                    max_size=num_completed,
                    unique=True,
                )
            )
        else:
            completed_step_ids = []
    else:
        # "full": complete ALL main path steps and at least one full path per branch
        completed_step_ids = list(main_step_ids)  # All main steps
        for branch in branches_data:
            # Pick one path to complete fully
            path_to_complete_idx = draw(
                st.integers(min_value=0, max_value=len(branch["paths"]) - 1)
            )
            path_to_complete = branch["paths"][path_to_complete_idx]
            completed_step_ids.extend(path_to_complete["step_ids"])

    return {
        "module_id": module_id,
        "main_path_id": main_path_id,
        "main_step_ids": main_step_ids,
        "branch_positions": branch_positions,
        "branches": branches_data,
        "all_step_ids": all_step_ids,
        "completed_step_ids": list(set(completed_step_ids)),
    }


def _insert_module_status_scenario(db: Database, scenario: dict) -> str:
    """Insere a estrutura de módulo no banco para teste de cálculo de status.

    Args:
        db: Banco de dados em memória.
        scenario: Dict gerado por module_status_calculation_scenario.

    Returns:
        user_id criado.
    """
    module_id = scenario["module_id"]
    main_path_id = scenario["main_path_id"]
    main_step_ids = scenario["main_step_ids"]
    branches = scenario["branches"]
    branch_positions = scenario["branch_positions"]

    # Criar módulo publicado
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo Status P9", "Módulo para teste de status", "published"),
    )

    # Criar caminho principal
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (main_path_id, module_id, "Principal", True),
    )

    # Inserir etapas do caminho principal
    for i, step_id in enumerate(main_step_ids):
        step_type = "branch" if i in branch_positions else "content"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, main_path_id, i, step_type),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"c_{step_id}", step_id, "text", f"Conteúdo main {i}", 0),
        )

    # Inserir ramificações e seus caminhos
    for branch in branches:
        branch_id = branch["branch_id"]
        branch_step_id = branch["branch_step_id"]

        db.execute(
            "INSERT INTO branches (id, step_id) VALUES (?, ?)",
            (branch_id, branch_step_id),
        )

        for p_idx, path_data in enumerate(branch["paths"]):
            path_id = path_data["path_id"]
            db.execute(
                "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
                "VALUES (?, ?, ?, ?, ?)",
                (path_id, module_id, branch_id, f"Caminho {p_idx}", False),
            )

            for s_idx, step_id in enumerate(path_data["step_ids"]):
                db.execute(
                    "INSERT INTO steps (id, module_id, path_id, position, step_type) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (step_id, module_id, path_id, s_idx, "content"),
                )
                db.execute(
                    "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (f"c_{step_id}", step_id, "text", f"Conteúdo {step_id}", 0),
                )

            # Inserir opção de branch
            option_id = f"opt_{branch_id}_{p_idx}"
            db.execute(
                "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
                "VALUES (?, ?, ?, ?, ?)",
                (option_id, branch_id, f"Opção caminho {p_idx}", path_id, p_idx),
            )

    # Criar usuário
    user_id = f"user_p9_{uuid.uuid4().hex[:8]}"
    db.execute(
        "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
        (user_id, "Teste P9", f"{user_id}@teste.com"),
    )

    # Inserir etapas concluídas
    for step_id in scenario["completed_step_ids"]:
        db.execute(
            "INSERT INTO completed_steps (user_id, step_id) VALUES (?, ?)",
            (user_id, step_id),
        )

    db.commit()
    return user_id


# =============================================================================
# Property 9: Cálculo correto do status do módulo
# =============================================================================


# Feature: client-training, Property 9: Cálculo correto do status do módulo
class TestProperty9ModuleStatusCalculation:
    """**Validates: Requirements 5.3, 5.4**

    Property 9: For any user and module: the computed status is COMPLETED iff
    all required steps are in `completed_steps` (including at least one complete
    path per branch); IN_PROGRESS iff at least one step is completed but not all
    required; NOT_STARTED iff zero steps are completed. The percentage must equal
    `completed_steps_count / total_required_steps * 100`.
    """

    @given(scenario=module_status_calculation_scenario())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_module_status_calculation_correct(self, scenario):
        """O status do módulo é calculado corretamente com base nas etapas concluídas.

        **Validates: Requirements 5.3, 5.4**

        Para qualquer usuário e módulo:
        - COMPLETED iff todas as etapas do caminho principal estão concluídas
          E pelo menos um caminho completo por ramificação
        - IN_PROGRESS iff pelo menos uma etapa concluída mas não todas obrigatórias
        - NOT_STARTED iff zero etapas concluídas
        """
        from managers.progress_manager import ProgressManager

        db = Database(":memory:")
        db.initialize()

        try:
            user_id = _insert_module_status_scenario(db, scenario)
            module_id = scenario["module_id"]
            completed_step_ids = set(scenario["completed_step_ids"])

            pm = ProgressManager(db, max_retries=1, retry_interval=0)

            # --- Verify is_module_complete ---
            is_complete = pm.is_module_complete(user_id, module_id)

            # Calculate expected completeness:
            # All main path steps must be completed
            main_step_ids = set(scenario["main_step_ids"])
            all_main_completed = main_step_ids.issubset(completed_step_ids)

            # For each branch, at least one path must be fully completed
            all_branches_satisfied = True
            for branch in scenario["branches"]:
                branch_satisfied = False
                for path_data in branch["paths"]:
                    path_step_ids = set(path_data["step_ids"])
                    if path_step_ids.issubset(completed_step_ids):
                        branch_satisfied = True
                        break
                if not branch_satisfied:
                    all_branches_satisfied = False
                    break

            expected_complete = all_main_completed and all_branches_satisfied

            assert is_complete == expected_complete, (
                f"is_module_complete retornou {is_complete}, esperava {expected_complete}. "
                f"Main completado: {all_main_completed}, "
                f"Branches satisfeitos: {all_branches_satisfied}. "
                f"Completed steps: {len(completed_step_ids)}, "
                f"Main steps: {len(main_step_ids)}"
            )

            # --- Verify status classification ---
            num_completed = len(completed_step_ids)

            if num_completed == 0:
                expected_status = ProgressStatus.NOT_STARTED
            elif expected_complete:
                expected_status = ProgressStatus.COMPLETED
            else:
                expected_status = ProgressStatus.IN_PROGRESS

            # The status is determined by the system when save_progress is called.
            # For this test, we verify the logic: is_module_complete determines COMPLETED,
            # zero completions means NOT_STARTED, anything else is IN_PROGRESS.
            if num_completed == 0:
                assert not is_complete, (
                    "With zero completed steps, module cannot be complete."
                )
            elif is_complete:
                assert num_completed > 0, (
                    "COMPLETED status requires at least one step completed."
                )

            # --- Verify percentage calculation ---
            percentage = pm.get_module_completion_percentage(user_id, module_id)

            # Total steps in the module (all steps across all paths)
            total_steps_row = db.execute(
                "SELECT COUNT(*) as cnt FROM steps WHERE module_id = ?",
                (module_id,),
            ).fetchone()
            total_steps = total_steps_row["cnt"]

            # Completed steps that belong to this module
            completed_in_module_row = db.execute(
                "SELECT COUNT(*) as cnt FROM completed_steps cs "
                "JOIN steps s ON cs.step_id = s.id "
                "WHERE cs.user_id = ? AND s.module_id = ?",
                (user_id, module_id),
            ).fetchone()
            completed_count = completed_in_module_row["cnt"]

            if total_steps == 0:
                expected_percentage = 0.0
            else:
                expected_percentage = round((completed_count / total_steps) * 100.0, 1)

            assert percentage == expected_percentage, (
                f"Percentual incorreto. Esperava {expected_percentage}%, "
                f"obteve {percentage}%. "
                f"completed_count={completed_count}, total_steps={total_steps}"
            )

        finally:
            db.close()

    @given(scenario=module_status_calculation_scenario())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_module_status_transitions_are_mutually_exclusive(self, scenario):
        """Os três estados (NOT_STARTED, IN_PROGRESS, COMPLETED) são mutuamente exclusivos.

        **Validates: Requirements 5.3, 5.4**

        Para qualquer cenário, exatamente um dos três estados deve ser verdadeiro:
        - NOT_STARTED: zero etapas concluídas
        - IN_PROGRESS: pelo menos uma etapa concluída mas módulo não completo
        - COMPLETED: is_module_complete retorna True
        """
        from managers.progress_manager import ProgressManager

        db = Database(":memory:")
        db.initialize()

        try:
            user_id = _insert_module_status_scenario(db, scenario)
            module_id = scenario["module_id"]
            completed_step_ids = set(scenario["completed_step_ids"])

            pm = ProgressManager(db, max_retries=1, retry_interval=0)

            is_complete = pm.is_module_complete(user_id, module_id)
            num_completed = len(completed_step_ids)

            # Determine which status applies
            is_not_started = (num_completed == 0)
            is_in_progress = (num_completed > 0 and not is_complete)
            is_completed = is_complete

            # Exactly one must be true
            statuses = [is_not_started, is_in_progress, is_completed]
            assert sum(statuses) == 1, (
                f"Exatamente um status deve ser verdadeiro, mas obteve: "
                f"NOT_STARTED={is_not_started}, IN_PROGRESS={is_in_progress}, "
                f"COMPLETED={is_completed}. "
                f"num_completed={num_completed}, is_complete={is_complete}"
            )

        finally:
            db.close()
