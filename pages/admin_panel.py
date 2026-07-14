"""Painel Administrativo do Sistema de Treinamento.

Interface CRUD para gestão de módulos pelo administrador:
- Listagem de módulos existentes com status
- Criação de novos módulos
- Edição de módulos existentes
- Exclusão com confirmação explícita e aviso de usuários afetados

Requirements: 6.1, 6.6
"""

from __future__ import annotations

import streamlit as st

from managers.content_manager import ContentManager
from managers.errors import ModuleNotFoundError, ValidationError
from models.database import Database
from models.enums import ModuleStatus


def render_admin_panel(db: Database, content_manager: ContentManager) -> None:
    """Renderiza o painel administrativo para gestão de módulos.

    Exibe a lista de módulos existentes e fornece formulários para
    criar, editar e excluir módulos com confirmação explícita.

    Args:
        db: Instância do banco de dados.
        content_manager: Instância do ContentManager.

    Requirements: 6.1, 6.6
    """
    st.title("Painel Administrativo")
    st.markdown("Gerencie os módulos de treinamento.")
    st.divider()

    # Abas para organizar as ações
    tab_list, tab_create, tab_edit, tab_delete = st.tabs(
        [" Módulos", " Criar Módulo", " Editar Módulo", " Excluir Módulo"]
    )

    with tab_list:
        _render_module_list(db)

    with tab_create:
        _render_create_form(content_manager)

    with tab_edit:
        _render_edit_form(db, content_manager)

    with tab_delete:
        _render_delete_form(db, content_manager)


def _get_all_modules(db: Database) -> list[dict]:
    """Busca todos os módulos do banco de dados.

    Args:
        db: Instância do banco de dados.

    Returns:
        Lista de dicts com dados dos módulos.
    """
    cursor = db.execute(
        "SELECT id, title, description, status, version, created_at, updated_at "
        "FROM modules ORDER BY updated_at DESC"
    )
    return [dict(row) for row in cursor.fetchall()]


def _render_module_list(db: Database) -> None:
    """Renderiza a lista de módulos existentes com status.

    Args:
        db: Instância do banco de dados.
    """
    modules = _get_all_modules(db)

    if not modules:
        st.info("Nenhum módulo cadastrado ainda. Use a aba 'Criar Módulo' para começar.")
        return

    st.markdown(f"**{len(modules)} módulo(s) cadastrado(s)**")

    for module in modules:
        status = module["status"]
        status_icon = _get_status_icon(status)

        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**{status_icon} {module['title']}**")
                st.caption(module["description"][:150] if module["description"] else "")

            with col2:
                st.markdown(f"Status: `{status}`")

            with col3:
                st.markdown(f"Versão: `{module['version']}`")

        st.divider()


def _get_status_icon(status: str) -> str:
    """Retorna ícone visual para o status do módulo.

    Args:
        status: Status do módulo (draft, published, archived).

    Returns:
        Emoji representando o status.
    """
    icons = {
        "draft": "",
        "published": "",
        "archived": "",
    }
    return icons.get(status, "")


def _render_create_form(content_manager: ContentManager) -> None:
    """Renderiza formulário para criação de novo módulo.

    Args:
        content_manager: Instância do ContentManager.

    Requirements: 6.1
    """
    st.markdown("### Criar Novo Módulo")
    st.markdown("Preencha os dados abaixo para criar um novo módulo de treinamento.")

    with st.form("create_module_form", clear_on_submit=True):
        title = st.text_input(
            "Título do Módulo",
            placeholder="Ex: Introdução ao Sistema",
            key="create_title",
        )
        description = st.text_area(
            "Descrição (máximo 150 caracteres)",
            placeholder="Breve descrição do conteúdo do módulo",
            max_chars=150,
            key="create_description",
        )

        submitted = st.form_submit_button(
            "Criar Módulo",
            use_container_width=True,
            
        )

    if submitted:
        if not title or not title.strip():
            st.error("O título do módulo é obrigatório.")
            return

        try:
            module = content_manager.create_module(
                title=title.strip(),
                description=description or "",
            )
            st.success(
                f"Módulo **{module.title}** criado com sucesso! "
                f"(ID: `{module.id[:8]}...`)"
            )
        except ValidationError as e:
            for error in e.errors:
                st.error(error)


def _render_edit_form(db: Database, content_manager: ContentManager) -> None:
    """Renderiza formulário para edição de módulo existente.

    Args:
        db: Instância do banco de dados.
        content_manager: Instância do ContentManager.

    Requirements: 6.1
    """
    st.markdown("### Editar Módulo")

    modules = _get_all_modules(db)

    if not modules:
        st.info("Nenhum módulo disponível para edição.")
        return

    # Seletor de módulo
    module_options = {m["title"]: m["id"] for m in modules}
    selected_title = st.selectbox(
        "Selecione o módulo para editar",
        options=list(module_options.keys()),
        key="edit_module_selector",
    )

    if selected_title is None:
        return

    selected_id = module_options[selected_title]

    # Buscar dados atuais do módulo
    selected_module = next((m for m in modules if m["id"] == selected_id), None)
    if selected_module is None:
        st.error("Módulo não encontrado.")
        return

    st.markdown(f"Editando: **{selected_module['title']}** (versão {selected_module['version']})")

    with st.form("edit_module_form", clear_on_submit=False):
        new_title = st.text_input(
            "Novo Título",
            value=selected_module["title"],
            key="edit_title",
        )
        new_description = st.text_area(
            "Nova Descrição (máximo 150 caracteres)",
            value=selected_module["description"],
            max_chars=150,
            key="edit_description",
        )

        submitted = st.form_submit_button(
            "Salvar Alterações",
            use_container_width=True,
            
        )

    if submitted:
        try:
            kwargs = {}
            if new_title.strip() != selected_module["title"]:
                kwargs["title"] = new_title.strip()
            if new_description != selected_module["description"]:
                kwargs["description"] = new_description

            if not kwargs:
                st.warning("Nenhuma alteração detectada.")
                return

            updated = content_manager.update_module(selected_id, **kwargs)
            st.success(f"Módulo **{updated.title}** atualizado com sucesso!")
        except ValidationError as e:
            for error in e.errors:
                st.error(error)
        except ModuleNotFoundError:
            st.error("Módulo não encontrado. Ele pode ter sido excluído.")


def _render_delete_form(db: Database, content_manager: ContentManager) -> None:
    """Renderiza formulário para exclusão de módulo com confirmação explícita.

    Exibe aviso com quantidade de usuários afetados quando o módulo
    possui progresso registrado. Requer confirmação explícita via checkbox
    antes de permitir a exclusão.

    Args:
        db: Instância do banco de dados.
        content_manager: Instância do ContentManager.

    Requirements: 6.1, 6.6
    """
    st.markdown("### Excluir Módulo")
    st.markdown(
        " A exclusão de um módulo é **irreversível** e remove todo o conteúdo associado."
    )

    modules = _get_all_modules(db)

    if not modules:
        st.info("Nenhum módulo disponível para exclusão.")
        return

    # Seletor de módulo
    module_options = {m["title"]: m["id"] for m in modules}
    selected_title = st.selectbox(
        "Selecione o módulo para excluir",
        options=list(module_options.keys()),
        key="delete_module_selector",
    )

    if selected_title is None:
        return

    selected_id = module_options[selected_title]

    # Verificar usuários afetados (sem confirmar a exclusão ainda)
    try:
        preliminary_result = content_manager.delete_module(selected_id, confirm=False)
    except ModuleNotFoundError:
        st.error("Módulo não encontrado.")
        return

    # Se o módulo não foi excluído (precisa confirmação ou sem usuários)
    # Exibir aviso de usuários afetados (Req 6.6)
    if preliminary_result.affected_users > 0:
        st.warning(
            f" **Atenção:** Este módulo possui **{preliminary_result.affected_users} "
            f"usuário(s)** com progresso registrado. "
            f"A exclusão removerá todo o progresso desses usuários."
        )
    else:
        st.info("Este módulo não possui usuários com progresso registrado.")

    # Confirmação explícita (Req 6.1)
    # Usar session_state para a confirmação em duas etapas
    confirm_key = f"confirm_delete_{selected_id}"

    confirm_checked = st.checkbox(
        f"Confirmo que desejo excluir o módulo **\"{selected_title}\"** e entendo que está ação é irreversível.",
        key=confirm_key,
    )

    if st.button(
        " Excluir Módulo",
        key="delete_module_btn",
        use_container_width=True,
        
        disabled=not confirm_checked,
    ):
        if not confirm_checked:
            st.error("Você deve confirmar a exclusão marcando a caixa acima.")
            return

        try:
            result = content_manager.delete_module(selected_id, confirm=True)
            if result.deleted:
                st.success(
                    f"Módulo **\"{selected_title}\"** excluído com sucesso. "
                    f"{result.affected_users} usuário(s) afetado(s)."
                )
                # Limpar estado para evitar referências inválidas
                if "selected_module_id" in st.session_state:
                    if st.session_state.get("selected_module_id") == selected_id:
                        del st.session_state["selected_module_id"]
            else:
                st.error("Não foi possível excluir o módulo.")
        except ModuleNotFoundError:
            st.error("Módulo não encontrado. Ele pode já ter sido excluído.")
