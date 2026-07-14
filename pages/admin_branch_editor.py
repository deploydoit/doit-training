"""Editor Visual de Ramificações do Sistema de Treinamento.

Interface administrativa para definir a estrutura de etapas e ramificações
de um módulo, incluindo:
- Visualização da estrutura de etapas e ramificações como nós conectados
- Adição de etapas com posição sequencial
- Criação de ramificações com 2-5 opções
- Validação de rótulos (3-80 caracteres)

Requirements: 6.2, 6.3
"""

from __future__ import annotations

import uuid
from typing import List, Optional

import streamlit as st

from managers.branch_manager import BranchManager
from managers.content_manager import ContentManager
from managers.errors import ValidationError, ValidationResult
from models.data_models import StepContent
from models.database import Database
from models.enums import ContentType, StepType


# Constantes de validação
MIN_BRANCH_OPTIONS = 2
MAX_BRANCH_OPTIONS = 5
MIN_LABEL_LENGTH = 3
MAX_LABEL_LENGTH = 80


def render_branch_editor(
    content_manager: ContentManager,
    branch_manager: BranchManager,
    db: Database,
    module_id: str,
) -> None:
    """Renderiza o editor visual de ramificações para um módulo.

    Exibe a estrutura atual de etapas e ramificações como nós conectados,
    permitindo ao administrador adicionar etapas, criar ramificações e
    definir rótulos para cada opção de caminho.

    Args:
        content_manager: Instância do ContentManager para operações CRUD.
        branch_manager: Instância do BranchManager para validação.
        db: Instância do banco de dados.
        module_id: ID do módulo sendo editado.

    Requirements: 6.2, 6.3
    """
    st.markdown("##  Editor de Ramificações")
    st.markdown(
        "Defina a estrutura de etapas e ramificações do módulo. "
        "Etapas são exibidas como nós conectados sequencialmente."
    )

    # Carregar caminhos do módulo
    paths = _get_module_paths(db, module_id)

    if not paths:
        st.info("Nenhum caminho encontrado para este módulo.")
        return

    # Renderizar caminho principal primeiro
    main_path = next((p for p in paths if p["is_main"]), None)
    if main_path:
        _render_path_editor(
            content_manager=content_manager,
            branch_manager=branch_manager,
            db=db,
            module_id=module_id,
            path_id=main_path["id"],
            path_name=main_path["name"],
            is_main=True,
        )

    # Renderizar caminhos de ramificação
    branch_paths = [p for p in paths if not p["is_main"]]
    if branch_paths:
        st.markdown("---")
        st.markdown("###  Caminhos de Ramificação")
        for path in branch_paths:
            _render_path_editor(
                content_manager=content_manager,
                branch_manager=branch_manager,
                db=db,
                module_id=module_id,
                path_id=path["id"],
                path_name=path["name"],
                is_main=False,
            )


def _render_path_editor(
    content_manager: ContentManager,
    branch_manager: BranchManager,
    db: Database,
    module_id: str,
    path_id: str,
    path_name: str,
    is_main: bool,
) -> None:
    """Renderiza o editor de um caminho específico com suas etapas.

    Exibe as etapas do caminho como nós visuais conectados, com opções
    para adicionar novas etapas e criar ramificações.

    Args:
        content_manager: Instância do ContentManager.
        branch_manager: Instância do BranchManager.
        db: Instância do banco de dados.
        module_id: ID do módulo.
        path_id: ID do caminho.
        path_name: Nome do caminho para exibição.
        is_main: Se é o caminho principal.
    """
    icon = "" if is_main else ""
    with st.expander(f"{icon} {path_name}", expanded=is_main):
        # Carregar etapas do caminho
        steps = _get_path_steps(db, path_id)

        if not steps:
            st.caption("Nenhuma etapa neste caminho ainda.")
        else:
            # Exibir etapas como nós visuais
            for i, step in enumerate(steps):
                _render_step_node(
                    db=db,
                    branch_manager=branch_manager,
                    step=step,
                    index=i,
                    total=len(steps),
                    path_id=path_id,
                )

        # Botão para adicionar nova etapa
        st.markdown("---")
        _render_add_step_form(
            content_manager=content_manager,
            db=db,
            module_id=module_id,
            path_id=path_id,
            current_step_count=len(steps),
        )


def _render_step_node(
    db: Database,
    branch_manager: BranchManager,
    step: dict,
    index: int,
    total: int,
    path_id: str,
) -> None:
    """Renderiza uma etapa como nó visual no editor.

    Exibe informações da etapa e, se for do tipo branch, mostra as
    opções de ramificação configuradas.

    Args:
        db: Instância do banco de dados.
        branch_manager: Instância do BranchManager.
        step: Dados da etapa (dict do SQLite).
        index: Índice da etapa no caminho.
        total: Total de etapas no caminho.
        path_id: ID do caminho.
    """
    step_type = step["step_type"]
    step_id = step["id"]

    # Ícone baseado no tipo
    if step_type == StepType.BRANCH.value:
        icon = ""
        type_label = "Ramificação"
    else:
        icon = ""
        type_label = "Conteúdo"

    # Nó visual da etapa
    col_connector, col_node = st.columns([1, 9])

    with col_connector:
        # Conector visual entre nós
        if index > 0:
            st.markdown("")
        st.markdown(f"**{index + 1}**")
        if index < total - 1:
            st.markdown("")

    with col_node:
        st.markdown(
            f"{icon} **Etapa {step['position'] + 1}** — _{type_label}_"
        )

        # Mostrar conteúdo resumido
        contents = _get_step_contents(db, step_id)
        if contents:
            for content in contents:
                content_type = content["content_type"]
                content_data = content["content_data"]
                if content_type == ContentType.TEXT.value:
                    preview = content_data[:80] + ("..." if len(content_data) > 80 else "")
                    st.caption(f" {preview}")
                elif content_type == ContentType.IMAGE.value:
                    st.caption(f" Imagem: {content_data[:50]}")
                elif content_type == ContentType.VIDEO.value:
                    st.caption(f" Vídeo: {content_data[:50]}")
                elif content_type == ContentType.LINK.value:
                    st.caption(f" Link: {content_data[:50]}")
        else:
            st.caption(" Sem conteúdo definido")

        # Se é uma ramificação, exibir opções
        if step_type == StepType.BRANCH.value:
            _render_branch_options_summary(db, branch_manager, step_id)


def _render_branch_options_summary(
    db: Database,
    branch_manager: BranchManager,
    step_id: str,
) -> None:
    """Exibe resumo das opções de ramificação de uma etapa.

    Args:
        db: Instância do banco de dados.
        branch_manager: Instância do BranchManager.
        step_id: ID da etapa com ramificação.
    """
    options = branch_manager.get_branch_options(step_id)

    if options:
        st.markdown("**Opções de ramificação:**")
        for opt in options:
            st.markdown(f"  ↳ `{opt.label}` → caminho `{opt.path_id[:8]}...`")

        # Validação visual
        validation = branch_manager.validate_branch(step_id)
        if not validation.is_valid:
            for error in validation.errors:
                st.warning(f" {error}")
        else:
            st.success(" Ramificação válida")
    else:
        st.warning(" Ramificação sem opções configuradas")


def _render_add_step_form(
    content_manager: ContentManager,
    db: Database,
    module_id: str,
    path_id: str,
    current_step_count: int,
) -> None:
    """Renderiza formulário para adicionar nova etapa ao caminho.

    Permite ao administrador adicionar etapas do tipo conteúdo ou
    ramificação, com posição sequencial automaticamente calculada.

    Args:
        content_manager: Instância do ContentManager.
        db: Instância do banco de dados.
        module_id: ID do módulo.
        path_id: ID do caminho.
        current_step_count: Quantidade atual de etapas no caminho.

    Requirements: 6.2
    """
    form_key = f"add_step_{path_id}"

    st.markdown("####  Adicionar Etapa")

    with st.form(key=form_key):
        # Tipo da etapa
        step_type_option = st.selectbox(
            "Tipo da etapa",
            options=["Conteúdo", "Ramificação"],
            key=f"step_type_{path_id}",
            help="Conteúdo: etapa com texto/mídia. Ramificação: ponto de decisão.",
        )

        # Conteúdo inicial da etapa
        content_type_option = st.selectbox(
            "Tipo de conteúdo",
            options=["Texto", "Imagem", "Vídeo", "Link"],
            key=f"content_type_{path_id}",
        )

        content_data = st.text_area(
            "Conteúdo",
            placeholder="Digite o texto ou URL do conteúdo...",
            key=f"content_data_{path_id}",
        )

        alt_text = st.text_input(
            "Texto alternativo (acessibilidade)",
            placeholder="Descrição para leitores de tela",
            key=f"alt_text_{path_id}",
        )

        # Posição (automática: próximo na sequência)
        next_position = current_step_count
        st.caption(f" Posição: {next_position + 1} (sequencial)")

        submitted = st.form_submit_button("Adicionar Etapa", )

        if submitted:
            if not content_data.strip():
                st.error(" O conteúdo da etapa não pode ser vazio.")
            else:
                _create_step(
                    content_manager=content_manager,
                    db=db,
                    module_id=module_id,
                    path_id=path_id,
                    position=next_position,
                    step_type_option=step_type_option,
                    content_type_option=content_type_option,
                    content_data=content_data.strip(),
                    alt_text=alt_text.strip() or None,
                )


def _create_step(
    content_manager: ContentManager,
    db: Database,
    module_id: str,
    path_id: str,
    position: int,
    step_type_option: str,
    content_type_option: str,
    content_data: str,
    alt_text: Optional[str],
) -> None:
    """Cria uma nova etapa e, se for ramificação, solicita configuração.

    Args:
        content_manager: Instância do ContentManager.
        db: Instância do banco de dados.
        module_id: ID do módulo.
        path_id: ID do caminho.
        position: Posição sequencial.
        step_type_option: 'Conteúdo' ou 'Ramificação'.
        content_type_option: Tipo de conteúdo selecionado.
        content_data: Dados do conteúdo.
        alt_text: Texto alternativo.
    """
    # Mapear tipo de conteúdo
    content_type_map = {
        "Texto": ContentType.TEXT,
        "Imagem": ContentType.IMAGE,
        "Vídeo": ContentType.VIDEO,
        "Link": ContentType.LINK,
    }
    content_type = content_type_map[content_type_option]

    # Mapear tipo de etapa
    step_type = (
        StepType.BRANCH if step_type_option == "Ramificação" else StepType.CONTENT
    )

    # Criar conteúdo da etapa
    step_content = StepContent(
        id="",  # Será gerado pelo ContentManager
        step_id="",  # Será preenchido pelo ContentManager
        content_type=content_type,
        content_data=content_data,
        alt_text=alt_text,
        order=0,
    )

    try:
        step = content_manager.create_step(
            module_id=module_id,
            content=step_content,
            position=position,
            path_id=path_id,
            step_type=step_type,
        )

        # Se é ramificação, criar branch no banco
        if step_type == StepType.BRANCH:
            branch_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO branches (id, step_id) VALUES (?, ?)",
                (branch_id, step.id),
            )
            db.commit()
            st.session_state[f"pending_branch_{step.id}"] = branch_id

        st.success(f" Etapa adicionada na posição {position + 1}!")
        st.rerun()

    except ValidationError as e:
        for error in e.errors:
            st.error(f" {error}")
    except Exception as e:
        st.error(f" Erro ao criar etapa: {str(e)}")


def render_create_branch_form(
    db: Database,
    branch_manager: BranchManager,
    module_id: str,
    step_id: str,
) -> None:
    """Renderiza formulário para criar/editar opções de ramificação.

    Permite definir entre 2 e 5 opções de caminho, com validação de
    rótulos (3-80 caracteres) em tempo real.

    Args:
        db: Instância do banco de dados.
        branch_manager: Instância do BranchManager.
        module_id: ID do módulo.
        step_id: ID da etapa do tipo branch.

    Requirements: 6.2, 6.3
    """
    st.markdown("###  Configurar Ramificação")
    st.markdown(
        f"Defina entre **{MIN_BRANCH_OPTIONS}** e **{MAX_BRANCH_OPTIONS}** opções "
        f"de caminho. Cada rótulo deve ter entre **{MIN_LABEL_LENGTH}** e "
        f"**{MAX_LABEL_LENGTH}** caracteres."
    )

    # Buscar branch existente para a etapa
    cursor = db.execute(
        "SELECT id FROM branches WHERE step_id = ?", (step_id,)
    )
    branch_row = cursor.fetchone()

    if branch_row is None:
        st.error(" Ramificação não encontrada para está etapa.")
        return

    branch_id = branch_row["id"]

    # Buscar opções existentes
    existing_options = branch_manager.get_branch_options(step_id)

    # Controle de quantidade de opções
    num_options_key = f"num_options_{step_id}"
    if num_options_key not in st.session_state:
        st.session_state[num_options_key] = max(
            len(existing_options), MIN_BRANCH_OPTIONS
        )

    col_minus, col_count, col_plus = st.columns([1, 2, 1])

    with col_minus:
        if st.button(
            "",
            key=f"decrease_options_{step_id}",
            disabled=st.session_state[num_options_key] <= MIN_BRANCH_OPTIONS,
        ):
            st.session_state[num_options_key] -= 1
            st.rerun()

    with col_count:
        st.markdown(
            f"**Opções: {st.session_state[num_options_key]}**"
        )

    with col_plus:
        if st.button(
            "",
            key=f"increase_options_{step_id}",
            disabled=st.session_state[num_options_key] >= MAX_BRANCH_OPTIONS,
        ):
            st.session_state[num_options_key] += 1
            st.rerun()

    # Formulário para cada opção
    num_options = st.session_state[num_options_key]

    with st.form(key=f"branch_options_form_{step_id}"):
        labels: List[str] = []
        validation_errors: List[str] = []

        for i in range(num_options):
            # Pré-preencher com opção existente, se disponível
            default_label = ""
            if i < len(existing_options):
                default_label = existing_options[i].label

            label = st.text_input(
                f"Opção {i + 1} — Rótulo",
                value=default_label,
                max_chars=MAX_LABEL_LENGTH,
                key=f"branch_label_{step_id}_{i}",
                placeholder=f"Ex: Sou novo na ferramenta ({MIN_LABEL_LENGTH}-{MAX_LABEL_LENGTH} caracteres)",
            )
            labels.append(label)

            # Indicador visual de tamanho
            if label:
                label_len = len(label)
                if label_len < MIN_LABEL_LENGTH:
                    st.caption(
                        f" Mínimo {MIN_LABEL_LENGTH} caracteres "
                        f"(atual: {label_len})"
                    )
                elif label_len > MAX_LABEL_LENGTH:
                    st.caption(
                        f" Máximo {MAX_LABEL_LENGTH} caracteres "
                        f"(atual: {label_len})"
                    )
                else:
                    st.caption(f" {label_len} caracteres")

        submitted = st.form_submit_button(
            " Salvar Ramificação", 
        )

        if submitted:
            # Validar todos os rótulos
            validation_errors = validate_branch_labels(labels)

            if validation_errors:
                for error in validation_errors:
                    st.error(f" {error}")
            else:
                _save_branch_options(
                    db=db,
                    module_id=module_id,
                    branch_id=branch_id,
                    step_id=step_id,
                    labels=labels,
                )


def validate_branch_labels(labels: List[str]) -> List[str]:
    """Valida rótulos de opções de ramificação.

    Critérios:
    - Cada rótulo deve ter entre 3 e 80 caracteres
    - Nenhum rótulo pode estar vazio
    - Deve haver entre 2 e 5 opções

    Args:
        labels: Lista de rótulos a validar.

    Returns:
        Lista de mensagens de erro. Lista vazia se tudo válido.

    Requirements: 6.3
    """
    errors: List[str] = []

    # Validar quantidade
    num_labels = len(labels)
    if num_labels < MIN_BRANCH_OPTIONS:
        errors.append(
            f"Ramificação deve ter no mínimo {MIN_BRANCH_OPTIONS} opções "
            f"(tem {num_labels})."
        )
    elif num_labels > MAX_BRANCH_OPTIONS:
        errors.append(
            f"Ramificação deve ter no máximo {MAX_BRANCH_OPTIONS} opções "
            f"(tem {num_labels})."
        )

    # Validar cada rótulo
    for i, label in enumerate(labels):
        if not label.strip():
            errors.append(f"Opção {i + 1}: rótulo não pode ser vazio.")
            continue

        label_stripped = label.strip()
        label_len = len(label_stripped)

        if label_len < MIN_LABEL_LENGTH:
            errors.append(
                f"Opção {i + 1}: rótulo deve ter no mínimo {MIN_LABEL_LENGTH} "
                f"caracteres (tem {label_len})."
            )
        elif label_len > MAX_LABEL_LENGTH:
            errors.append(
                f"Opção {i + 1}: rótulo deve ter no máximo {MAX_LABEL_LENGTH} "
                f"caracteres (tem {label_len})."
            )

    return errors


def _save_branch_options(
    db: Database,
    module_id: str,
    branch_id: str,
    step_id: str,
    labels: List[str],
) -> None:
    """Salva opções de ramificação no banco de dados.

    Remove opções anteriores e cria novas com os rótulos fornecidos.
    Cada opção cria um novo caminho associado ao módulo.

    Args:
        db: Instância do banco de dados.
        module_id: ID do módulo.
        branch_id: ID da ramificação.
        step_id: ID da etapa.
        labels: Lista de rótulos validados.
    """
    try:
        # Remover opções antigas e seus caminhos associados
        cursor = db.execute(
            "SELECT id, path_id FROM branch_options WHERE branch_id = ?",
            (branch_id,),
        )
        old_options = cursor.fetchall()

        for old_opt in old_options:
            # Remover etapas do caminho antigo
            db.execute(
                "DELETE FROM steps WHERE path_id = ?", (old_opt["path_id"],)
            )
            # Remover caminho antigo
            db.execute("DELETE FROM paths WHERE id = ?", (old_opt["path_id"],))

        # Remover opções antigas
        db.execute(
            "DELETE FROM branch_options WHERE branch_id = ?", (branch_id,)
        )

        # Criar novas opções com caminhos
        for i, label in enumerate(labels):
            # Criar caminho de destino
            path_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
                "VALUES (?, ?, ?, ?, FALSE)",
                (path_id, module_id, branch_id, label.strip()),
            )

            # Criar opção de ramificação
            option_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO branch_options (id, branch_id, label, path_id, position) "
                "VALUES (?, ?, ?, ?, ?)",
                (option_id, branch_id, label.strip(), path_id, i),
            )

        db.commit()
        st.success(
            f" Ramificação salva com {len(labels)} opções!"
        )
        st.rerun()

    except Exception as e:
        db.rollback()
        st.error(f" Erro ao salvar ramificação: {str(e)}")


def render_branch_editor_for_step(
    content_manager: ContentManager,
    branch_manager: BranchManager,
    db: Database,
    module_id: str,
    step_id: str,
) -> None:
    """Renderiza editor completo de ramificação para uma etapa específica.

    Combina visualização da etapa com formulário de configuração
    de ramificação. Usado quando o admin seleciona uma etapa do tipo
    branch para editar suas opções.

    Args:
        content_manager: Instância do ContentManager.
        branch_manager: Instância do BranchManager.
        db: Instância do banco de dados.
        module_id: ID do módulo.
        step_id: ID da etapa a editar.

    Requirements: 6.2, 6.3
    """
    # Verificar se a etapa existe e é do tipo branch
    cursor = db.execute(
        "SELECT id, position, step_type, path_id FROM steps WHERE id = ?",
        (step_id,),
    )
    step_row = cursor.fetchone()

    if step_row is None:
        st.error(" Etapa não encontrada.")
        return

    if step_row["step_type"] != StepType.BRANCH.value:
        st.warning(" Esta etapa não é do tipo ramificação.")
        return

    st.markdown(
        f"**Editando ramificação da Etapa {step_row['position'] + 1}**"
    )

    # Renderizar formulário de opções
    render_create_branch_form(
        db=db,
        branch_manager=branch_manager,
        module_id=module_id,
        step_id=step_id,
    )

    # Exibir validação atual
    st.markdown("---")
    st.markdown("####  Validação")
    validation = branch_manager.validate_branch(step_id)
    if validation.is_valid:
        st.success("Ramificação válida — pronta para publicação.")
    else:
        for error in validation.errors:
            st.error(f" {error}")


def _get_module_paths(db: Database, module_id: str) -> List[dict]:
    """Retorna todos os caminhos de um módulo.

    Args:
        db: Instância do banco de dados.
        module_id: ID do módulo.

    Returns:
        Lista de dicts com dados dos caminhos.
    """
    cursor = db.execute(
        "SELECT id, module_id, parent_branch_id, name, is_main "
        "FROM paths WHERE module_id = ? ORDER BY is_main DESC, name",
        (module_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def _get_path_steps(db: Database, path_id: str) -> List[dict]:
    """Retorna etapas de um caminho ordenadas por posição.

    Args:
        db: Instância do banco de dados.
        path_id: ID do caminho.

    Returns:
        Lista de dicts com dados das etapas.
    """
    cursor = db.execute(
        "SELECT id, module_id, path_id, position, step_type, created_at "
        "FROM steps WHERE path_id = ? ORDER BY position",
        (path_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def _get_step_contents(db: Database, step_id: str) -> List[dict]:
    """Retorna conteúdos de uma etapa ordenados por display_order.

    Args:
        db: Instância do banco de dados.
        step_id: ID da etapa.

    Returns:
        Lista de dicts com dados dos conteúdos.
    """
    cursor = db.execute(
        "SELECT id, step_id, content_type, content_data, alt_text, display_order "
        "FROM step_contents WHERE step_id = ? ORDER BY display_order",
        (step_id,),
    )
    return [dict(row) for row in cursor.fetchall()]
