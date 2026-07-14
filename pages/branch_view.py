"""Página de Ramificações do Sistema de Treinamento.

Renderiza pontos de decisão (branches) onde o usuário escolhe entre
caminhos diferentes. Inclui:
- Exibição de opções como botões clicáveis com rótulos descritivos
- Indicação visual de caminhos já explorados
- Botão de retorno ao ponto de ramificação na última etapa de um caminho
- Tratamento de caminho indisponível com mensagem de erro

Requirements: 3.1, 3.2, 3.4, 3.5, 3.6
"""

from __future__ import annotations

from typing import List, Optional

import streamlit as st

from managers.branch_manager import BranchManager
from managers.errors import PathUnavailableError
from models.data_models import BranchOption, Step


def render_branch(
    branch_manager: BranchManager,
    step_id: str,
    user_id: str,
) -> Optional[str]:
    """Renderiza opções de ramificação com indicadores de exploração.

    Apresenta as opções de ramificação como botões clicáveis. Cada botão
    exibe o rótulo descritivo (até 150 caracteres) e indica visualmente
    se o caminho já foi explorado pelo usuário.

    Args:
        branch_manager: Instância do BranchManager para acessar dados.
        step_id: ID da etapa que contém a ramificação.
        user_id: ID do usuário atual.

    Returns:
        ID da opção selecionada pelo usuário, ou None se nenhuma
        seleção foi feita.

    Requirements: 3.1, 3.2, 3.4, 3.5
    """
    # Obter opções de ramificação para a etapa
    options: List[BranchOption] = branch_manager.get_branch_options(step_id)

    if not options:
        return None

    # Obter caminhos já explorados pelo usuário
    explored_paths: List[str] = branch_manager.get_explored_paths(user_id, step_id)

    # Título da seção de ramificação
    st.markdown("###  Escolha seu caminho")
    st.markdown("Selecione uma das opções abaixo para continuar:")

    selected_option_id: Optional[str] = None

    # Renderizar cada opção como um botão clicável
    for option in options:
        is_explored = option.path_id in explored_paths

        # Construir rótulo do botão com indicador de exploração
        label = option.label
        if is_explored:
            button_label = f" {label}"
        else:
            button_label = f" {label}"

        # Usar colunas para layout com indicador visual
        col_button, col_status = st.columns([5, 1])

        with col_button:
            # Botão clicável com rótulo descritivo (até 150 caracteres)
            if st.button(
                button_label,
                key=f"branch_option_{option.id}",
                use_container_width=True,
            ):
                selected_option_id = option.id

        with col_status:
            if is_explored:
                st.markdown(
                    "<span style='color: #28a745; font-size: 0.85em;'>"
                    "Explorado</span>",
                    unsafe_allow_html=True,
                )

    # Processar seleção
    if selected_option_id is not None:
        try:
            first_step: Step = branch_manager.select_branch(
                user_id=user_id,
                step_id=step_id,
                option_id=selected_option_id,
            )
            # Armazenar navegação no session_state
            st.session_state["current_step_id"] = first_step.id
            st.session_state["current_path_id"] = first_step.path_id
            st.session_state["branch_source_step_id"] = step_id
            st.rerun()
        except PathUnavailableError as e:
            _render_path_unavailable_error(str(e))
            return None

    return selected_option_id


def render_return_to_branch_button(
    branch_manager: BranchManager,
    user_id: str,
    current_path_id: str,
) -> None:
    """Renderiza botão para retornar ao ponto de ramificação original.

    Exibido na última etapa de um caminho de ramificação para permitir
    que o usuário explore outras opções.

    Args:
        branch_manager: Instância do BranchManager.
        user_id: ID do usuário atual.
        current_path_id: ID do caminho atual do usuário.

    Requirements: 3.4
    """
    st.divider()
    st.markdown("---")
    st.markdown("####  Explorar outros caminhos")
    st.markdown(
        "Você chegou ao final deste caminho. "
        "Deseja retornar ao ponto de ramificação para explorar outras opções?"
    )

    if st.button(
        " Retornar ao ponto de ramificação",
        key="return_to_branch_point",
        use_container_width=True,
        
    ):
        try:
            return_step: Step = branch_manager.get_return_point(
                user_id=user_id,
                path_id=current_path_id,
            )
            # Navegar de volta ao ponto de ramificação
            st.session_state["current_step_id"] = return_step.id
            st.session_state["current_path_id"] = return_step.path_id
            # Limpar referência ao branch de origem
            if "branch_source_step_id" in st.session_state:
                del st.session_state["branch_source_step_id"]
            st.rerun()
        except PathUnavailableError as e:
            _render_path_unavailable_error(str(e))


def should_show_return_button(
    branch_manager: BranchManager,
    training_manager,
    step_id: str,
    module_id: str,
    path_id: Optional[str],
) -> bool:
    """Determina se o botão de retorno ao branch deve ser exibido.

    O botão é exibido quando:
    1. O usuário está na última etapa de um caminho
    2. O caminho pertence a uma ramificação (tem parent_branch_id)

    Args:
        branch_manager: Instância do BranchManager.
        training_manager: Instância do TrainingManager.
        step_id: ID da etapa atual.
        module_id: ID do módulo atual.
        path_id: ID do caminho atual.

    Returns:
        True se o botão deve ser exibido, False caso contrário.

    Requirements: 3.4
    """
    if path_id is None:
        return False

    # Verificar se é a última etapa do caminho
    is_last = training_manager.is_last_step(module_id, step_id, path_id)
    if not is_last:
        return False

    # Verificar se o caminho pertence a uma ramificação
    db = branch_manager.db
    cursor = db.execute(
        "SELECT parent_branch_id FROM paths WHERE id = ?",
        (path_id,),
    )
    path_row = cursor.fetchone()

    if path_row is None:
        return False

    return path_row["parent_branch_id"] is not None


def _render_path_unavailable_error(message: str) -> None:
    """Renderiza mensagem de erro quando caminho está indisponível.

    Exibe um alerta informativo mantendo o usuário no ponto de
    ramificação atual, conforme requisito 3.6.

    Args:
        message: Mensagem de erro descritiva.

    Requirements: 3.6
    """
    st.error(
        f" **Caminho indisponível**\n\n"
        f"{message}\n\n"
        f"Você permanecerá no ponto de ramificação atual. "
        f"Por favor, escolha outra opção."
    )
