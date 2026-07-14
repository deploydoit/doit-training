"""Testes de integração end-to-end do Sistema de Treinamento.

Testa fluxos completos usando managers reais e banco SQLite em memória:
- Criar módulo → publicar → navegar como usuário → concluir
- Salvar e recuperar progresso no SQLite
- Versionamento de módulo com migração de progresso

Requirements validated: 1.4, 5.1, 5.2, 5.4, 6.4
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from managers.content_manager import ContentManager
from managers.progress_manager import ProgressManager
from managers.training_manager import TrainingManager
from models.data_models import StepContent
from models.enums import ContentType, ModuleStatus, ProgressStatus, StepType


# =============================================================================
# Teste 1: Fluxo completo - criar módulo → publicar → navegar → concluir
# Requirements: 1.4, 5.4
# =============================================================================


class TestFullFlowCreatePublishNavigateComplete:
    """Testa o fluxo completo end-to-end do sistema."""

    def test_create_publish_navigate_complete_module(
        self, db, content_manager, training_manager, progress_manager, create_user
    ):
        """Fluxo: admin cria módulo com etapas → publica → usuário navega e conclui."""
        # 1. Admin cria módulo
        module = content_manager.create_module(
            title="Introdução ao Sistema",
            description="Módulo introdutório para novos clientes",
        )
        assert module.status == ModuleStatus.DRAFT
        assert module.version == 1

        # 2. Admin adiciona etapas ao módulo
        step_0 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Bem-vindo ao treinamento!", alt_text=None, order=0,
            ),
            position=0,
        )
        step_1 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Vamos aprender sobre o painel.", alt_text=None, order=0,
            ),
            position=1,
        )
        step_2 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Parabéns! Módulo concluído.", alt_text=None, order=0,
            ),
            position=2,
        )

        # 3. Publicar módulo
        publish_result = content_manager.publish_module(module.id)
        assert publish_result.published is True
        assert publish_result.version == 2
        assert publish_result.errors == []

        # 4. Usuário acessa o sistema
        user_id = create_user("user_flow", "Maria Silva", "maria@email.com")

        # 5. Verificar que módulo aparece na lista (Req 1.4)
        modules = training_manager.get_modules(user_id)
        assert len(modules) == 1
        assert modules[0].title == "Introdução ao Sistema"
        assert modules[0].progress_status == ProgressStatus.NOT_STARTED

        # 6. Usuário seleciona módulo → primeira etapa (Req 1.4)
        first_step = training_manager.get_first_step(module.id)
        assert first_step is not None
        assert first_step.id == step_0.id
        assert first_step.position == 0

        # 7. Navegar pelas etapas salvando progresso
        # Etapa 0 → salvar progresso
        progress_manager.save_progress(user_id, module.id, step_0.id)

        # Avançar para etapa 1
        next_step = training_manager.get_next_step(module.id, step_0.id)
        assert next_step is not None
        assert next_step.id == step_1.id
        progress_manager.save_progress(user_id, module.id, step_1.id)

        # Avançar para etapa 2 (última)
        next_step = training_manager.get_next_step(module.id, step_1.id)
        assert next_step is not None
        assert next_step.id == step_2.id
        progress_manager.save_progress(user_id, module.id, step_2.id)

        # 8. Verificar que está na última etapa
        assert training_manager.is_last_step(module.id, step_2.id) is True

        # 9. Concluir módulo (Req 5.4)
        completed = training_manager.complete_module(user_id, module.id)
        assert completed is True

        # 10. Verificar status na lista de módulos
        modules = training_manager.get_modules(user_id)
        assert modules[0].progress_status == ProgressStatus.COMPLETED
        assert modules[0].progress_percentage == 100.0

    def test_module_selection_loads_first_step(
        self, db, content_manager, training_manager, create_user
    ):
        """Ao selecionar um módulo publicado, o sistema carrega a primeira etapa (Req 1.4)."""
        # Criar e publicar módulo com etapas
        module = content_manager.create_module(
            title="Módulo Básico",
            description="Teste de seleção",
        )
        content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Primeira etapa aqui", alt_text=None, order=0,
            ),
            position=0,
        )
        content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Segunda etapa", alt_text=None, order=0,
            ),
            position=1,
        )
        content_manager.publish_module(module.id)

        # Selecionar módulo deve retornar a etapa na posição 0
        first_step = training_manager.get_first_step(module.id)
        assert first_step is not None
        assert first_step.position == 0
        assert first_step.content[0].content_data == "Primeira etapa aqui"


# =============================================================================
# Teste 2: Salvar e recuperar progresso no SQLite
# Requirements: 5.1, 5.2
# =============================================================================


class TestSaveAndRecoverProgress:
    """Testa persistência e recuperação do progresso no SQLite."""

    def test_save_progress_and_recover(
        self, db, content_manager, progress_manager, create_user
    ):
        """Progresso salvo deve ser recuperável após nova sessão (Req 5.1, 5.2)."""
        # Setup: criar módulo publicado com etapas
        module = content_manager.create_module(
            title="Módulo Progresso", description="Teste de persistência"
        )
        step_0 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Etapa inicial", alt_text=None, order=0,
            ),
            position=0,
        )
        step_1 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Etapa intermediária", alt_text=None, order=0,
            ),
            position=1,
        )
        step_2 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Etapa final", alt_text=None, order=0,
            ),
            position=2,
        )
        content_manager.publish_module(module.id)

        user_id = create_user("user_progress", "João", "joao@email.com")

        # Navegar até a segunda etapa e salvar
        result = progress_manager.save_progress(user_id, module.id, step_0.id)
        assert result is True

        result = progress_manager.save_progress(user_id, module.id, step_1.id)
        assert result is True

        # Simular nova sessão: recuperar progresso
        progress = progress_manager.get_progress(user_id, module.id)
        assert progress is not None
        assert progress.current_step_id == step_1.id
        assert progress.status == ProgressStatus.IN_PROGRESS
        assert step_0.id in progress.completed_steps
        assert step_1.id in progress.completed_steps

    def test_progress_percentage_increments(
        self, db, content_manager, progress_manager, create_user
    ):
        """Percentual de progresso deve aumentar a cada etapa concluída (Req 5.1)."""
        module = content_manager.create_module(
            title="Módulo Percentual", description="Teste percentual"
        )
        steps = []
        for i in range(4):
            step = content_manager.create_step(
                module_id=module.id,
                content=StepContent(
                    id="", step_id="", content_type=ContentType.TEXT,
                    content_data=f"Conteúdo {i}", alt_text=None, order=0,
                ),
                position=i,
            )
            steps.append(step)
        content_manager.publish_module(module.id)

        user_id = create_user("user_pct", "Ana", "ana@email.com")

        # Concluir etapas uma a uma e verificar percentual crescente
        previous_pct = 0.0
        for step in steps:
            progress_manager.save_progress(user_id, module.id, step.id)
            current_pct = progress_manager.get_module_completion_percentage(
                user_id, module.id
            )
            assert current_pct >= previous_pct
            previous_pct = current_pct

        # Após todas etapas, deve ser 100%
        final_pct = progress_manager.get_module_completion_percentage(
            user_id, module.id
        )
        assert final_pct == 100.0

    def test_progress_persists_across_multiple_modules(
        self, db, content_manager, progress_manager, create_user
    ):
        """Progresso em múltiplos módulos é mantido independentemente (Req 5.2)."""
        user_id = create_user("user_multi", "Pedro", "pedro@email.com")

        # Criar 2 módulos publicados
        module_a = content_manager.create_module(
            title="Módulo A", description="Primeiro módulo"
        )
        step_a = content_manager.create_step(
            module_id=module_a.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Conteúdo A", alt_text=None, order=0,
            ),
            position=0,
        )
        content_manager.publish_module(module_a.id)

        module_b = content_manager.create_module(
            title="Módulo B", description="Segundo módulo"
        )
        step_b = content_manager.create_step(
            module_id=module_b.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Conteúdo B", alt_text=None, order=0,
            ),
            position=0,
        )
        content_manager.publish_module(module_b.id)

        # Salvar progresso em ambos
        progress_manager.save_progress(user_id, module_a.id, step_a.id)
        progress_manager.save_progress(user_id, module_b.id, step_b.id)

        # Verificar que ambos são recuperáveis independentemente
        progress_a = progress_manager.get_progress(user_id, module_a.id)
        progress_b = progress_manager.get_progress(user_id, module_b.id)

        assert progress_a is not None
        assert progress_a.current_step_id == step_a.id
        assert progress_b is not None
        assert progress_b.current_step_id == step_b.id

    def test_resume_from_last_step(
        self, db, content_manager, training_manager, progress_manager, create_user
    ):
        """Usuário pode retomar de onde parou usando progresso salvo (Req 5.2)."""
        module = content_manager.create_module(
            title="Módulo Retomada", description="Teste retomada"
        )
        steps = []
        for i in range(5):
            step = content_manager.create_step(
                module_id=module.id,
                content=StepContent(
                    id="", step_id="", content_type=ContentType.TEXT,
                    content_data=f"Etapa {i}", alt_text=None, order=0,
                ),
                position=i,
            )
            steps.append(step)
        content_manager.publish_module(module.id)

        user_id = create_user("user_resume", "Laura", "laura@email.com")

        # Navegar até etapa 3 (posição 2, zero-indexed)
        for step in steps[:3]:
            progress_manager.save_progress(user_id, module.id, step.id)

        # Simular "saída" e "retorno" - recuperar progresso
        progress = progress_manager.get_progress(user_id, module.id)
        assert progress is not None
        assert progress.current_step_id == steps[2].id

        # Carregar a etapa de retomada
        resumed_step = training_manager.get_step(module.id, progress.current_step_id)
        assert resumed_step.id == steps[2].id
        assert resumed_step.position == 2


# =============================================================================
# Teste 3: Versionamento de módulo com migração de progresso
# Requirements: 6.4
# =============================================================================


class TestVersioningWithProgressMigration:
    """Testa versionamento e preservação de progresso durante atualização."""

    def test_publish_new_version_preserves_completed_steps(
        self, db, content_manager, progress_manager, create_user
    ):
        """Ao publicar nova versão, etapas concluídas que ainda existem são preservadas (Req 6.4)."""
        # Criar módulo com 3 etapas
        module = content_manager.create_module(
            title="Módulo Versionado", description="Teste de versionamento"
        )
        step_0 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Etapa 1 original", alt_text=None, order=0,
            ),
            position=0,
        )
        step_1 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Etapa 2 original", alt_text=None, order=0,
            ),
            position=1,
        )
        step_2 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Etapa 3 original", alt_text=None, order=0,
            ),
            position=2,
        )

        # Publicar versão 1
        result = content_manager.publish_module(module.id)
        assert result.published is True
        assert result.version == 2

        # Usuário avança até etapa 1
        user_id = create_user("user_version", "Carlos", "carlos@email.com")
        progress_manager.save_progress(user_id, module.id, step_0.id)
        progress_manager.save_progress(user_id, module.id, step_1.id)

        # Verificar progresso antes da nova versão
        progress = progress_manager.get_progress(user_id, module.id)
        assert step_0.id in progress.completed_steps
        assert step_1.id in progress.completed_steps

        # Publicar nova versão (etapas existentes permanecem)
        result = content_manager.publish_module(module.id)
        assert result.published is True
        assert result.version == 3
        assert result.migrated_users == 1

        # Verificar que progresso foi preservado
        progress_after = progress_manager.get_progress(user_id, module.id)
        assert progress_after is not None
        # Etapas que ainda existem devem permanecer concluídas
        assert step_0.id in progress_after.completed_steps
        assert step_1.id in progress_after.completed_steps

    def test_version_increment_on_publish(self, db, content_manager):
        """Cada publicação incrementa a versão do módulo (Req 6.4)."""
        module = content_manager.create_module(
            title="Módulo Multi-versão", description="Teste incremento"
        )
        # Adicionar conteúdo para permitir publicação
        content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Conteúdo base", alt_text=None, order=0,
            ),
            position=0,
        )

        # Publicar versão 2
        r1 = content_manager.publish_module(module.id)
        assert r1.version == 2

        # Publicar versão 3
        r2 = content_manager.publish_module(module.id)
        assert r2.version == 3

        # Publicar versão 4
        r3 = content_manager.publish_module(module.id)
        assert r3.version == 4

    def test_migration_removes_invalid_completed_steps(
        self, db, content_manager, progress_manager, create_user
    ):
        """Migração remove etapas concluídas que não existem mais na nova versão (Req 6.4)."""
        module = content_manager.create_module(
            title="Módulo Migração", description="Teste remoção steps"
        )
        step_0 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Permanece", alt_text=None, order=0,
            ),
            position=0,
        )
        step_1 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Será removida", alt_text=None, order=0,
            ),
            position=1,
        )

        # Publicar e criar progresso
        content_manager.publish_module(module.id)
        user_id = create_user("user_migrate", "Fernanda", "fernanda@email.com")
        progress_manager.save_progress(user_id, module.id, step_0.id)
        progress_manager.save_progress(user_id, module.id, step_1.id)

        # Verificar que ambas estão nas completed_steps antes da migração
        progress_before = progress_manager.get_progress(user_id, module.id)
        assert step_0.id in progress_before.completed_steps
        assert step_1.id in progress_before.completed_steps

        # Remover step_1 desabilitando FK temporariamente (simula edição admin)
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("DELETE FROM step_contents WHERE step_id = ?", (step_1.id,))
        db.execute("DELETE FROM steps WHERE id = ?", (step_1.id,))
        db.commit()
        db.execute("PRAGMA foreign_keys = ON")

        # Republicar módulo - migração deve limpar step_1 das completed_steps
        result = content_manager.publish_module(module.id)
        assert result.published is True
        assert result.migrated_users == 1

        # Verificar que step_1 não está mais nas completed_steps do progresso
        progress_after = progress_manager.get_progress(user_id, module.id)
        assert progress_after is not None
        assert step_0.id in progress_after.completed_steps
        assert step_1.id not in progress_after.completed_steps

    def test_migration_repositions_user_to_valid_step(
        self, db, content_manager, progress_manager, create_user
    ):
        """Se etapa atual foi removida, usuário é reposicionado na mais avançada válida (Req 6.4)."""
        module = content_manager.create_module(
            title="Módulo Reposição", description="Teste reposição"
        )
        step_0 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Etapa 0", alt_text=None, order=0,
            ),
            position=0,
        )
        step_1 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Etapa 1 (será removida)", alt_text=None, order=0,
            ),
            position=1,
        )
        step_2 = content_manager.create_step(
            module_id=module.id,
            content=StepContent(
                id="", step_id="", content_type=ContentType.TEXT,
                content_data="Etapa 2", alt_text=None, order=0,
            ),
            position=2,
        )

        # Publicar e criar progresso na step_1
        content_manager.publish_module(module.id)
        user_id = create_user("user_repos", "Diego", "diego@email.com")
        progress_manager.save_progress(user_id, module.id, step_0.id)
        progress_manager.save_progress(user_id, module.id, step_1.id)

        # Confirmar posição atual
        progress_before = progress_manager.get_progress(user_id, module.id)
        assert progress_before.current_step_id == step_1.id

        # Remover step_1 desabilitando FK temporariamente (simula edição admin)
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("DELETE FROM step_contents WHERE step_id = ?", (step_1.id,))
        db.execute("DELETE FROM steps WHERE id = ?", (step_1.id,))
        db.commit()
        db.execute("PRAGMA foreign_keys = ON")

        # Republicar com migração
        result = content_manager.publish_module(module.id)
        assert result.migrated_users == 1

        # Usuário deve ser reposicionado numa etapa válida (step_1 não existe mais)
        progress = progress_manager.get_progress(user_id, module.id)
        assert progress is not None
        assert progress.current_step_id != step_1.id
        # Deve estar em step_0 (mais avançada concluída válida) ou step_2
        assert progress.current_step_id in (step_0.id, step_2.id)
