"""Fixtures compartilhadas e strategies Hypothesis para testes do Sistema de Treinamento.

Fornece:
- Fixtures pytest: banco em memória, módulos de exemplo, usuários de teste, caminhos com ramificações
- Strategies Hypothesis: geração de módulos, etapas e caminhos válidos para property-based tests

Requirements: 5.1, 5.2, 5.3
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytest
from hypothesis import strategies as st
from hypothesis.strategies import composite

# Adicionar raiz do projeto ao path para imports funcionarem
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from managers.branch_manager import BranchManager
from managers.content_manager import ContentManager
from managers.progress_manager import ProgressManager
from managers.training_manager import TrainingManager
from models.data_models import (
    Branch,
    BranchOption,
    Module,
    Path as TrainingPath,
    Step,
    StepContent,
    UserProfile,
    UserProgress,
)
from models.database import Database
from models.enums import ContentType, ModuleStatus, ProgressStatus, StepType


# =============================================================================
# Fixtures: Banco de Dados
# =============================================================================


@pytest.fixture
def db():
    """Banco de dados SQLite em memória, inicializado com esquema completo.

    Yields:
        Database: instância com todas as tabelas criadas.
    """
    database = Database(":memory:")
    database.initialize()
    yield database
    database.close()


# =============================================================================
# Fixtures: Managers
# =============================================================================


@pytest.fixture
def progress_manager(db):
    """ProgressManager com retry_interval=0 para testes rápidos."""
    return ProgressManager(db, max_retries=3, retry_interval=0)


@pytest.fixture
def branch_manager(db):
    """BranchManager conectado ao banco em memória."""
    return BranchManager(db)


@pytest.fixture
def training_manager(db):
    """TrainingManager conectado ao banco em memória."""
    return TrainingManager(db)


@pytest.fixture
def content_manager(db, tmp_path):
    """ContentManager com diretório de mídia temporário."""
    return ContentManager(db, media_path=str(tmp_path / "media"))


# =============================================================================
# Fixtures: Usuários de Teste
# =============================================================================


@pytest.fixture
def create_user(db):
    """Factory fixture para criar usuários de teste.

    Returns:
        Callable que cria um usuário e retorna seu ID.

    Exemplo:
        user_id = create_user("user1", "João", "joao@email.com")
    """

    def _create(
        user_id: Optional[str] = None,
        name: str = "Usuário Teste",
        email: Optional[str] = None,
        is_first_visit: bool = True,
        is_admin: bool = False,
    ) -> str:
        if user_id is None:
            user_id = f"user_{uuid.uuid4().hex[:8]}"
        if email is None:
            email = f"{user_id}@teste.com"

        db.execute(
            "INSERT INTO users (id, name, email, is_first_visit, is_admin) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, name, email, is_first_visit, is_admin),
        )
        db.commit()
        return user_id

    return _create


@pytest.fixture
def test_user(create_user):
    """Usuário padrão de teste (não-admin, primeira visita)."""
    return create_user("test_user", "Teste Padrão", "teste@email.com")


@pytest.fixture
def admin_user(create_user):
    """Usuário administrador de teste."""
    return create_user(
        "admin_user", "Admin Teste", "admin@email.com", is_first_visit=False, is_admin=True
    )


@pytest.fixture
def returning_user(create_user):
    """Usuário que já visitou o sistema (is_first_visit=False)."""
    return create_user(
        "returning_user", "Retornante", "retornante@email.com", is_first_visit=False
    )


# =============================================================================
# Fixtures: Módulos de Exemplo
# =============================================================================


@pytest.fixture
def create_module(db):
    """Factory fixture para criar módulos de treinamento.

    Returns:
        Callable que cria um módulo e retorna seu ID.
    """

    def _create(
        module_id: Optional[str] = None,
        title: str = "Módulo Teste",
        description: str = "Descrição do módulo de teste",
        status: ModuleStatus = ModuleStatus.PUBLISHED,
        version: int = 1,
    ) -> str:
        if module_id is None:
            module_id = f"mod_{uuid.uuid4().hex[:8]}"

        db.execute(
            "INSERT INTO modules (id, title, description, status, version) "
            "VALUES (?, ?, ?, ?, ?)",
            (module_id, title, description, status.value, version),
        )
        db.commit()
        return module_id

    return _create


@pytest.fixture
def sample_module(db):
    """Módulo publicado com caminho principal e 5 etapas de conteúdo.

    Retorna dict com:
        module_id, path_id, step_ids (lista de 5 IDs)
    """
    module_id = "sample_module"
    path_id = "sample_main_path"

    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo Exemplo", "Um módulo de exemplo para testes", "published"),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path_id, module_id, "Principal", True),
    )

    step_ids = []
    for i in range(5):
        step_id = f"sample_step_{i}"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, i, "content"),
        )
        # Adicionar conteúdo a cada etapa
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"content_{step_id}", step_id, "text", f"Conteúdo da etapa {i + 1}", 0),
        )
        step_ids.append(step_id)

    db.commit()
    return {"module_id": module_id, "path_id": path_id, "step_ids": step_ids}


@pytest.fixture
def draft_module(db):
    """Módulo em rascunho (não publicado) com 2 etapas."""
    module_id = "draft_module"
    path_id = "draft_main_path"

    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo Rascunho", "Módulo ainda não publicado", "draft"),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path_id, module_id, "Principal", True),
    )

    step_ids = []
    for i in range(2):
        step_id = f"draft_step_{i}"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, i, "content"),
        )
        step_ids.append(step_id)

    db.commit()
    return {"module_id": module_id, "path_id": path_id, "step_ids": step_ids}


# =============================================================================
# Fixtures: Caminhos com Ramificações
# =============================================================================


@pytest.fixture
def module_with_branches(db):
    """Módulo com caminho principal e ramificação com 3 caminhos alternativos.

    Estrutura:
        Principal: step_0 (content) → step_1 (branch) → step_2 (content)
        Caminho A: a_step_0 → a_step_1
        Caminho B: b_step_0 → b_step_1 → b_step_2
        Caminho C: c_step_0

    Retorna dict com:
        module_id, main_path_id, branch_step_id, branch_id,
        main_step_ids, path_a (dict com id, step_ids),
        path_b (dict com id, step_ids), path_c (dict com id, step_ids),
        option_ids (lista de IDs das opções)
    """
    module_id = "branched_module"
    main_path_id = "branched_main_path"

    # Criar módulo
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo com Ramificações", "Testa caminhos alternativos", "published"),
    )

    # Caminho principal
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (main_path_id, module_id, "Principal", True),
    )
    main_step_ids = []
    for i, step_type in enumerate(["content", "branch", "content"]):
        step_id = f"branched_main_step_{i}"
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, module_id, main_path_id, i, step_type),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"content_{step_id}", step_id, "text", f"Conteúdo principal {i}", 0),
        )
        main_step_ids.append(step_id)

    branch_step_id = main_step_ids[1]

    # Criar branch
    branch_id = "branch_1"
    db.execute(
        "INSERT INTO branches (id, step_id) VALUES (?, ?)",
        (branch_id, branch_step_id),
    )

    # Caminhos alternativos
    paths_data = {
        "a": {"name": "Caminho A", "num_steps": 2},
        "b": {"name": "Caminho B", "num_steps": 3},
        "c": {"name": "Caminho C", "num_steps": 1},
    }

    paths_result = {}
    option_ids = []

    for idx, (key, pdata) in enumerate(paths_data.items()):
        path_id = f"branch_path_{key}"
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, ?, ?, ?)",
            (path_id, module_id, branch_id, pdata["name"], False),
        )

        step_ids = []
        for i in range(pdata["num_steps"]):
            step_id = f"branch_{key}_step_{i}"
            db.execute(
                "INSERT INTO steps (id, module_id, path_id, position, step_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (step_id, module_id, path_id, i, "content"),
            )
            db.execute(
                "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"content_{step_id}", step_id, "text", f"Conteúdo {key} etapa {i}", 0),
            )
            step_ids.append(step_id)

        # Opção de branch
        option_id = f"option_{key}"
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (option_id, branch_id, f"Escolher {pdata['name']}", path_id, idx),
        )
        option_ids.append(option_id)

        paths_result[f"path_{key}"] = {"id": path_id, "step_ids": step_ids}

    db.commit()

    return {
        "module_id": module_id,
        "main_path_id": main_path_id,
        "branch_step_id": branch_step_id,
        "branch_id": branch_id,
        "main_step_ids": main_step_ids,
        "option_ids": option_ids,
        **paths_result,
    }


# =============================================================================
# Fixtures: Configuração parametrizada de módulos
# =============================================================================


@pytest.fixture
def create_module_with_steps(db):
    """Factory fixture para criar módulos com número variável de etapas.

    Returns:
        Callable que cria módulo + caminho + etapas e retorna dict.
    """

    def _create(
        module_id: Optional[str] = None,
        num_steps: int = 3,
        status: str = "published",
        title: str = "Módulo Dinâmico",
    ) -> dict:
        if module_id is None:
            module_id = f"mod_{uuid.uuid4().hex[:8]}"
        path_id = f"{module_id}_main_path"

        db.execute(
            "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
            (module_id, title, f"Módulo com {num_steps} etapas", status),
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
        return {"module_id": module_id, "path_id": path_id, "step_ids": step_ids}

    return _create


# =============================================================================
# Hypothesis Strategies: Geração de dados para property-based tests
# =============================================================================


# Strategies básicas reutilizáveis
valid_id = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_-"),
    min_size=4,
    max_size=20,
).filter(lambda s: s[0].isalpha())

valid_title = st.text(min_size=3, max_size=80).filter(lambda s: s.strip() != "")

valid_description = st.text(min_size=5, max_size=150).filter(lambda s: s.strip() != "")

valid_email = st.from_regex(
    r"[a-z][a-z0-9]{2,8}@[a-z]{3,8}\.(com|org|net)", fullmatch=True
)

valid_branch_label = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
    min_size=3,
    max_size=80,
).filter(lambda s: s.strip() != "" and len(s.strip()) >= 3)


@composite
def module_strategy(draw, status=None):
    """Gera um Module válido para testes.

    Args:
        status: Se fornecido, usa este status. Caso contrário, sorteia.

    Returns:
        Module dataclass com dados válidos.
    """
    mod_id = draw(valid_id.map(lambda s: f"mod_{s}"))
    title = draw(valid_title)
    description = draw(valid_description)
    mod_status = status or draw(st.sampled_from(list(ModuleStatus)))
    now = datetime.now()

    return Module(
        id=mod_id,
        title=title,
        description=description,
        status=mod_status,
        created_at=now,
        updated_at=now,
        version=draw(st.integers(min_value=1, max_value=10)),
    )


@composite
def step_strategy(draw, module_id=None, path_id=None, position=None, step_type=None):
    """Gera um Step válido para testes.

    Args:
        module_id: ID do módulo (gerado se não fornecido).
        path_id: ID do caminho (gerado se não fornecido).
        position: Posição sequencial (gerada se não fornecida).
        step_type: Tipo da etapa (sorteado se não fornecido).

    Returns:
        Step dataclass com dados válidos.
    """
    step_id = draw(valid_id.map(lambda s: f"step_{s}"))
    mod_id = module_id or draw(valid_id.map(lambda s: f"mod_{s}"))
    p_id = path_id or draw(valid_id.map(lambda s: f"path_{s}"))
    pos = position if position is not None else draw(st.integers(min_value=0, max_value=50))
    s_type = step_type or draw(st.sampled_from(list(StepType)))

    return Step(
        id=step_id,
        module_id=mod_id,
        path_id=p_id,
        position=pos,
        step_type=s_type,
        content=[],
        created_at=datetime.now(),
    )


@composite
def path_with_steps_strategy(draw, min_steps=2, max_steps=20, module_id=None):
    """Gera um Path com N etapas sequenciais (position 0..N-1).

    Todas as etapas são do tipo CONTENT e possuem conteúdo textual.
    Útil para testar navegação round-trip e indicadores de posição.

    Args:
        min_steps: Número mínimo de etapas.
        max_steps: Número máximo de etapas.
        module_id: ID do módulo (gerado se não fornecido).

    Returns:
        Tuple (TrainingPath, list[Step]) com caminho e suas etapas.
    """
    num_steps = draw(st.integers(min_value=min_steps, max_value=max_steps))
    mod_id = module_id or f"mod_{draw(valid_id)}"
    path_id = f"path_{draw(valid_id)}"

    steps = []
    for i in range(num_steps):
        step_id = f"{path_id}_step_{i}"
        content = StepContent(
            id=f"content_{step_id}",
            step_id=step_id,
            content_type=ContentType.TEXT,
            content_data=f"Conteúdo da etapa {i + 1}",
            alt_text=None,
            order=0,
        )
        step = Step(
            id=step_id,
            module_id=mod_id,
            path_id=path_id,
            position=i,
            step_type=StepType.CONTENT,
            content=[content],
            created_at=datetime.now(),
        )
        steps.append(step)

    path = TrainingPath(
        id=path_id,
        module_id=mod_id,
        parent_branch_id=None,
        name=f"Caminho com {num_steps} etapas",
        steps=steps,
    )

    return path, steps


@composite
def branch_options_strategy(draw, min_options=2, max_options=5):
    """Gera uma lista de BranchOption válidas (2-5 opções).

    Cada opção tem label entre 3 e 80 caracteres e path_id único.

    Args:
        min_options: Mínimo de opções (padrão 2).
        max_options: Máximo de opções (padrão 5).

    Returns:
        List[BranchOption] com opções válidas.
    """
    num_options = draw(st.integers(min_value=min_options, max_value=max_options))
    branch_id = f"branch_{draw(valid_id)}"

    options = []
    for i in range(num_options):
        option_id = f"opt_{branch_id}_{i}"
        label = draw(valid_branch_label)
        path_id = f"path_{branch_id}_{i}"

        options.append(
            BranchOption(
                id=option_id,
                branch_id=branch_id,
                label=label,
                path_id=path_id,
                position=i,
            )
        )

    return options


@composite
def user_profile_strategy(draw, is_first_visit=None, is_admin=None):
    """Gera um UserProfile válido para testes.

    Args:
        is_first_visit: Se fornecido, fixa o valor. Caso contrário, sorteia.
        is_admin: Se fornecido, fixa o valor. Caso contrário, sorteia.

    Returns:
        UserProfile dataclass com dados válidos.
    """
    user_id = draw(valid_id.map(lambda s: f"user_{s}"))
    name = draw(st.text(min_size=2, max_size=50).filter(lambda s: s.strip() != ""))
    email = draw(valid_email)
    first_visit = is_first_visit if is_first_visit is not None else draw(st.booleans())
    admin = is_admin if is_admin is not None else draw(st.booleans())

    return UserProfile(
        id=user_id,
        name=name,
        email=email,
        is_first_visit=first_visit,
        is_admin=admin,
        created_at=datetime.now(),
        last_login=datetime.now(),
    )


@composite
def module_with_branches_strategy(draw, num_paths=None):
    """Gera estrutura completa de módulo com ramificação para property tests.

    Retorna um dicionário com IDs e estrutura suficiente para inserir no banco
    durante testes de propriedade.

    Args:
        num_paths: Número de caminhos na ramificação (2-5, sorteado se não fornecido).

    Returns:
        Dict com: module_id, main_path_id, branch_step_id, branch_id,
                  main_steps (list), branch_paths (list de dicts com path_id, step_ids),
                  options (list de dicts com id, label, path_id)
    """
    n_paths = num_paths or draw(st.integers(min_value=2, max_value=5))
    module_id = f"mod_{draw(valid_id)}"
    main_path_id = f"main_path_{module_id}"
    branch_step_id = f"branch_step_{module_id}"
    branch_id = f"branch_{module_id}"

    # Etapas do caminho principal (pelo menos a etapa de branch)
    num_main_steps = draw(st.integers(min_value=1, max_value=5))
    branch_position = draw(st.integers(min_value=0, max_value=num_main_steps - 1))

    main_steps = []
    for i in range(num_main_steps):
        step_id = branch_step_id if i == branch_position else f"{main_path_id}_step_{i}"
        s_type = StepType.BRANCH if i == branch_position else StepType.CONTENT
        main_steps.append({"id": step_id, "position": i, "step_type": s_type.value})

    # Caminhos da ramificação
    branch_paths = []
    options = []
    for p_idx in range(n_paths):
        path_id = f"bpath_{module_id}_{p_idx}"
        num_steps = draw(st.integers(min_value=1, max_value=8))
        step_ids = [f"{path_id}_step_{s}" for s in range(num_steps)]
        branch_paths.append({"path_id": path_id, "step_ids": step_ids, "num_steps": num_steps})

        label = draw(valid_branch_label)
        option_id = f"opt_{module_id}_{p_idx}"
        options.append({"id": option_id, "label": label, "path_id": path_id})

    return {
        "module_id": module_id,
        "main_path_id": main_path_id,
        "branch_step_id": branch_step_id,
        "branch_id": branch_id,
        "branch_position": branch_position,
        "main_steps": main_steps,
        "branch_paths": branch_paths,
        "options": options,
    }


# =============================================================================
# Helpers: Funções utilitárias para inserção no banco durante testes
# =============================================================================


def insert_module_structure(db: Database, structure: dict) -> None:
    """Insere uma estrutura completa de módulo no banco para property tests.

    Args:
        db: Instância do banco de dados.
        structure: Dict gerado por module_with_branches_strategy.
    """
    module_id = structure["module_id"]
    main_path_id = structure["main_path_id"]
    branch_id = structure["branch_id"]
    branch_step_id = structure["branch_step_id"]

    # Módulo
    db.execute(
        "INSERT INTO modules (id, title, description, status) VALUES (?, ?, ?, ?)",
        (module_id, "Módulo Gerado", "Módulo para teste de propriedade", "published"),
    )

    # Caminho principal
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (main_path_id, module_id, "Principal", True),
    )

    # Etapas do caminho principal
    for step_data in structure["main_steps"]:
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_data["id"], module_id, main_path_id, step_data["position"], step_data["step_type"]),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"c_{step_data['id']}", step_data["id"], "text", "Conteúdo", 0),
        )

    # Branch
    db.execute(
        "INSERT INTO branches (id, step_id) VALUES (?, ?)",
        (branch_id, branch_step_id),
    )

    # Caminhos de ramificação e suas etapas
    for bp in structure["branch_paths"]:
        db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, ?, ?, ?)",
            (bp["path_id"], module_id, branch_id, f"Caminho {bp['path_id']}", False),
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

    # Opções do branch
    for idx, opt in enumerate(structure["options"]):
        db.execute(
            "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (opt["id"], branch_id, opt["label"], opt["path_id"], idx),
        )

    db.commit()


def insert_user(db: Database, user_id: str, name: str = "Teste", email: Optional[str] = None) -> str:
    """Insere um usuário no banco para property tests.

    Args:
        db: Instância do banco de dados.
        user_id: ID do usuário.
        name: Nome do usuário.
        email: Email (gerado automaticamente se não fornecido).

    Returns:
        O user_id inserido.
    """
    if email is None:
        email = f"{user_id}@teste.com"
    db.execute(
        "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
        (user_id, name, email),
    )
    db.commit()
    return user_id
