"""Aplicação principal do Sistema de Treinamento.

Ponto de entrada do Streamlit que implementa:
- Roteamento entre páginas usando st.session_state
- Integração do SessionManager para controle de estado
- Conexão de todos os managers com o banco de dados
- Layout responsivo (desktop >1024px, tablet 601-1024px, mobile ≤600px)

Requirements: 1.1, 1.2, 7.1, 7.2, 7.3
"""

from __future__ import annotations

import streamlit as st

from managers.branch_manager import BranchManager
from managers.content_manager import ContentManager
from managers.progress_manager import ProgressManager
from managers.session_manager import SessionManager
from managers.training_manager import TrainingManager
from models.database import Database


# ---------------------------------------------------------------------------
# Configuração da página Streamlit
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="DOit | Treinamento",
    page_icon="https://www.doit.com.br/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# CSS responsivo: desktop (>1024px), tablet (601-1024px), mobile (≤600px)
# ---------------------------------------------------------------------------

_RESPONSIVE_CSS = """
<style>
/* DOit Training — Identidade Visual limpa e consistente */
* {
    font-family: "Lucida Grande", "Lucida Sans Unicode", Arial, Verdana, sans-serif;
}

.main .block-container {
    max-width: 640px;
    margin: 0 auto;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    background-color: #FAFAFA;
}

/* Esconder sidebar */
[data-testid="stSidebar"] { display: none; }
section[data-testid="stSidebarContent"] { display: none; }
.main { margin-left: auto !important; margin-right: auto !important; }

/* ===== TIPOGRAFIA UNIFORME ===== */
/* Tamanho base: 14px para tudo. Títulos proporcionais. */

h1, h2, h3, h4 {
    font-family: "Lucida Grande", "Lucida Sans Unicode", Arial, Verdana, sans-serif;
    font-weight: 600;
    color: #333;
    text-align: left;
    margin-top: 1.2rem;
    margin-bottom: 0.5rem;
}

h1 { font-size: 1.3rem; }
h2 { font-size: 1.1rem; border-bottom: 2px solid #F5C085; padding-bottom: 0.4rem; }
h3 { font-size: 0.95rem; color: #555; }

.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    text-align: left;
}

/* Corpo de texto — tamanho único e legível */
.stMarkdown p,
.stMarkdown ul,
.stMarkdown ol,
.stMarkdown li {
    font-size: 14px;
    line-height: 1.6;
    color: #404040;
    text-align: left;
}

.stMarkdown ul, .stMarkdown ol {
    padding-left: 1.2rem;
    list-style-position: outside;
}

.stMarkdown li {
    margin-bottom: 4px;
}

.stMarkdown em {
    color: #777;
    font-style: italic;
    font-size: 13px;
}

.stMarkdown strong {
    color: #333;
}

.stMarkdown code {
    background: #FFF8E1;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 13px;
    color: #404040;
    border: 1px solid #E0E0E0;
}

.stMarkdown table { margin: 0 auto; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th { background: #FFF8E1; font-weight: 600; text-align: left; padding: 8px 10px; border-bottom: 2px solid #F5C085; color: #333; }
td { padding: 8px 10px; border-bottom: 1px solid #E0E0E0; color: #404040; }

/* ===== BOTÕES ===== */
.stButton > button {
    min-height: 40px;
    min-width: 40px;
    padding: 8px 16px;
    margin-bottom: 4px;
    border-radius: 6px;
    font-weight: 500;
    font-size: 14px;
    font-family: "Lucida Grande", "Lucida Sans Unicode", Arial, Verdana, sans-serif;
    background-color: #F5C085 !important;
    color: #404040 !important;
    border: 1px solid #E0C9A8 !important;
    transition: background-color 0.2s;
}

.stButton > button:hover {
    background-color: #e8ad6a !important;
    border-color: #404040 !important;
}

button[kind="primary"],
button[data-testid="baseButton-primary"] {
    background-color: #F5C085 !important;
    color: #404040 !important;
    border-color: #F5C085 !important;
}

button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background-color: #e8ad6a !important;
}

/* ===== COMPONENTES ===== */
[data-testid="stExpander"] {
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    background: #FFFFFF;
}

.stProgress > div > div { background-color: #F5C085 !important; }
.stProgress > div > div > div { background-color: #F5C085 !important; }
[data-testid="stProgress"] div[role="progressbar"] > div { background-color: #F5C085 !important; }

img { max-width: 100%; height: auto; }
[data-testid="stImage"] img { max-width: 100%; }

/* ===== RESPONSIVO ===== */
@media (min-width: 1025px) { .main .block-container { padding-left: 3rem; padding-right: 3rem; } }
@media (min-width: 601px) and (max-width: 1024px) { .main .block-container { max-width: 100%; padding-left: 2rem; padding-right: 2rem; } }
@media (max-width: 600px) {
    .main .block-container { max-width: 100%; padding-left: 1rem; padding-right: 1rem; }
    .stButton > button { min-height: 44px; min-width: 44px; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
    [data-testid="stHorizontalBlock"] > div { flex: 1 1 100% !important; min-width: 100% !important; }
}

.stButton + .stButton { margin-top: 8px; }

/* Form submit */
.stFormSubmitButton > button,
[data-testid="stFormSubmitButton"] > button {
    background-color: #F5C085 !important;
    color: #404040 !important;
    border-color: #F5C085 !important;
}

.stFormSubmitButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background-color: #e8ad6a !important;
    border-color: #e8ad6a !important;
}

/* Botão Revisar verde */
div:has(> [data-testid="stTooltipHoverTarget"]) button {
    background-color: #28a745 !important;
    color: white !important;
    border-color: #28a745 !important;
}
</style>
"""


# ---------------------------------------------------------------------------
# Inicialização da aplicação
# ---------------------------------------------------------------------------


def _get_database() -> Database:
    """Cria e inicializa a instância do banco de dados."""
    db = Database("training.db")
    db.initialize()
    return db


def _get_managers(db: Database) -> dict:
    """Cria instâncias de todos os managers conectados ao banco.

    Args:
        db: Instância do banco de dados.

    Returns:
        Dicionário com todas as instâncias de managers.
    """
    progress_manager = ProgressManager(db, retry_interval=0)
    branch_manager = BranchManager(db)
    training_manager = TrainingManager(db)
    content_manager = ContentManager(db, media_path="media")

    return {
        "progress_manager": progress_manager,
        "branch_manager": branch_manager,
        "training_manager": training_manager,
        "content_manager": content_manager,
    }


# ---------------------------------------------------------------------------
# Roteamento de páginas
# ---------------------------------------------------------------------------


def _route_to_page(db: Database, managers: dict) -> None:
    """Roteia para a página apropriada com base no session_state.

    Páginas disponíveis:
    - welcome: Tela de boas-vindas e identificação
    - module_list: Lista de módulos disponíveis
    - step_view: Visualização de etapa com navegação
    - admin: Painel administrativo

    Args:
        db: Instância do banco de dados.
        managers: Dicionário com instâncias dos managers.
    """
    current_page = SessionManager.get_current_page()

    if current_page == "welcome":
        _render_welcome(db)

    elif current_page == "module_list":
        _render_module_list(managers)

    elif current_page == "step_view":
        _render_step_view(db, managers)

    elif current_page == "admin":
        _render_admin(db, managers)

    else:
        # Página desconhecida - voltar para welcome
        SessionManager.set_current_page("welcome")
        st.rerun()


def _render_welcome(db: Database) -> None:
    """Renderiza a página de boas-vindas.

    Delega para pages/welcome.py. Após identificação, o fluxo de
    redirecionamento é gerenciado pelo próprio render_welcome_page.

    Args:
        db: Instância do banco de dados.
    """
    from pages.welcome import render_welcome_page

    render_welcome_page(db)


def _render_module_list(managers: dict) -> None:
    """Renderiza a lista de módulos com progresso do usuário.

    Inclui navegação para o painel admin se o usuário é administrador.

    Args:
        managers: Dicionário com instâncias dos managers.
    """
    from pages.module_list import render_module_list

    user_id = SessionManager.get_user_id()
    if user_id is None:
        SessionManager.set_current_page("welcome")
        st.rerun()
        return

    # Cabeçalho com opções do usuário
    _render_header_bar()

    # Obter módulos com progresso
    training_manager: TrainingManager = managers["training_manager"]
    modules = training_manager.get_modules(user_id)

    render_module_list(user_id, modules)


def _render_step_view(db: Database, managers: dict) -> None:
    """Renderiza a etapa atual do módulo selecionado.

    Gerencia:
    - Carregamento da etapa correta (resumo ou primeira)
    - Renderização de conteúdo ou ramificação
    - Botão de retorno ao branch quando aplicável
    - Tela de conclusão do módulo

    Args:
        db: Instância do banco de dados.
        managers: Dicionário com instâncias dos managers.
    """
    from pages.branch_view import (
        render_branch,
        render_return_to_branch_button,
        should_show_return_button,
    )
    from pages.step_view import render_step

    user_id = SessionManager.get_user_id()
    module_id = SessionManager.get_selected_module_id()

    if user_id is None or module_id is None:
        SessionManager.set_current_page("module_list")
        st.rerun()
        return

    training_manager: TrainingManager = managers["training_manager"]
    progress_manager: ProgressManager = managers["progress_manager"]
    branch_manager: BranchManager = managers["branch_manager"]

    # Verificar se módulo foi concluído
    if st.session_state.get("module_completed"):
        _render_module_completion()
        return

    # Determinar etapa atual
    step_id = SessionManager.get_current_step_id()
    path_id = SessionManager.get_current_path_id()

    if step_id is None:
        # Precisa carregar a etapa inicial ou retomar progresso
        step = _resolve_initial_step(
            training_manager, progress_manager, user_id, module_id
        )
        if step is None:
            st.warning("Este módulo não possui conteúdo disponível.")
            _render_back_to_modules_button()
            return
        st.session_state["current_step_id"] = step.id
        st.session_state["current_path_id"] = step.path_id
        st.rerun()
        return

    # Carregar etapa atual
    try:
        step = training_manager.get_step(module_id, step_id)
    except Exception:
        st.error("Erro ao carregar a etapa. Tente novamente.")
        _render_back_to_modules_button()
        return

    # Cabeçalho com botão de voltar à lista
    _render_step_header()

    # Renderizar conteúdo da etapa
    from models.enums import StepType

    if step.step_type == StepType.BRANCH:
        # Etapa de ramificação - exibir opções
        render_step(step, training_manager, progress_manager, user_id, module_id)
        render_branch(branch_manager, step_id, user_id)
    else:
        # Etapa de conteúdo regular
        render_step(step, training_manager, progress_manager, user_id, module_id)

    # Verificar se deve exibir botão de retorno ao branch
    if should_show_return_button(
        branch_manager, training_manager, step_id, module_id, path_id
    ):
        render_return_to_branch_button(branch_manager, user_id, path_id)


def _render_admin(db: Database, managers: dict) -> None:
    """Renderiza o painel administrativo.

    Inclui abas para CRUD de módulos, editor de ramificações e publicação.

    Args:
        db: Instância do banco de dados.
        managers: Dicionário com instâncias dos managers.
    """
    from pages.admin_panel import render_admin_panel
    from pages.admin_progress import render_progress_panel

    if not SessionManager.is_admin():
        st.error("Acesso restrito a administradores.")
        SessionManager.set_current_page("module_list")
        st.rerun()
        return

    if st.button("Voltar para módulos", key="admin_back_to_modules"):
        SessionManager.set_current_page("module_list")
        st.rerun()

    tab_progress, tab_manage = st.tabs(["Progresso", "Gerenciar Módulos"])

    with tab_progress:
        render_progress_panel(db)

    with tab_manage:
        content_manager: ContentManager = managers["content_manager"]
        render_admin_panel(db, content_manager)


# ---------------------------------------------------------------------------
# Componentes de interface auxiliares
# ---------------------------------------------------------------------------


def _render_header_bar() -> None:
    """Renderiza barra de cabeçalho com logo DOit e informações do usuário."""
    profile = SessionManager.get_user_profile()
    if profile is None:
        return

    col_logo, col_title, col_user = st.columns([1, 3, 1])

    with col_logo:
        st.image("media/logo-doit.png", width=70)

    with col_title:
        st.markdown(
            '<p style="font-size:1.4rem;font-weight:600;color:#404040;margin:0;padding-top:14px;">'
            'Módulos de Treinamento</p>',
            unsafe_allow_html=True,
        )

    with col_user:
        st.markdown(f"<p style='text-align:right;padding-top:8px;'><strong>{profile.name}</strong></p>", unsafe_allow_html=True)
        if profile.is_admin:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Admin", key="nav_admin", use_container_width=True):
                    SessionManager.set_current_page("admin")
                    st.rerun()
            with c2:
                if st.button("Sair", key="nav_logout", use_container_width=True):
                    SessionManager.logout()
                    st.rerun()
        else:
            if st.button("Sair", key="nav_logout", use_container_width=True):
                SessionManager.logout()
                st.rerun()

    st.divider()


def _render_step_header() -> None:
    """Renderiza cabeçalho da etapa: logo + botão voltar."""
    st.image("media/logo-doit.png", width=70)
    if st.button("Voltar para módulos", key="step_back_to_modules"):
        SessionManager.clear_navigation_state()
        SessionManager.set_current_page("module_list")
        st.rerun()


def _render_module_completion() -> None:
    """Renderiza tela de conclusão do módulo."""
    st.markdown(
        """
        <div style="
            text-align: center;
            padding: 40px 20px;
            background-color: #FFFFD6;
            border-radius: 12px;
            border: 2px solid #F5C085;
            margin: 20px 0;
        ">
            <h2 style="color: #404040; margin-bottom: 8px;">
                Parabéns! Módulo Concluído!
            </h2>
            <p style="color: #404040; font-size: 16px;">
                Você completou todas as etapas deste módulo.
                Continue explorando outros módulos para aprofundar seu aprendizado.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_back_to_modules_button()


def _render_back_to_modules_button() -> None:
    """Renderiza botão para voltar à lista de módulos."""
    if st.button(
        "Voltar para a lista de módulos",
        key="back_to_modules_completion",
        use_container_width=True,
        
    ):
        SessionManager.clear_navigation_state()
        SessionManager.set_current_page("module_list")
        st.rerun()


def _resolve_initial_step(
    training_manager: TrainingManager,
    progress_manager: ProgressManager,
    user_id: str,
    module_id: str,
):
    """Resolve a etapa inicial para exibição.

    Se o usuário deve retomar progresso, busca a última etapa salva.
    Caso contrário, retorna a primeira etapa do caminho principal.

    Args:
        training_manager: Instância do TrainingManager.
        progress_manager: Instância do ProgressManager.
        user_id: ID do usuário.
        module_id: ID do módulo.

    Returns:
        Step inicial ou None se o módulo não tem etapas.
    """
    if SessionManager.should_resume_module():
        # Tentar retomar de onde parou
        progress = progress_manager.get_progress(user_id, module_id)
        if progress is not None and progress.current_step_id:
            try:
                step = training_manager.get_step(module_id, progress.current_step_id)
                # Limpar flag de retomada
                st.session_state["resume_module"] = False
                return step
            except Exception:
                pass

    # Limpar flag de retomada
    st.session_state["resume_module"] = False

    # Carregar primeira etapa do módulo
    return training_manager.get_first_step(module_id)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Função principal da aplicação.

    Inicializa sessão, banco de dados, managers e roteia para a
    página correta baseado no estado atual da sessão.
    """
    # Inicializar session_state
    SessionManager.initialize()

    # AUTO-LOGIN para desenvolvimento (remover depois)
    if st.session_state.get("user_profile") is None:
        from models.data_models import UserProfile
        from datetime import datetime
        st.session_state["user_profile"] = UserProfile(
            id="97493147-58c5-47d2-abb9-2ad67f861c49",
            name="Isabela Silva",
            email="isabela@doit.com.br",
            is_first_visit=False,
            is_admin=True,
            created_at=datetime.now(),
            last_login=datetime.now(),
        )
        st.session_state["user_id"] = "97493147-58c5-47d2-abb9-2ad67f861c49"
        st.session_state["current_page"] = "module_list"

    # Injetar CSS responsivo
    st.markdown(_RESPONSIVE_CSS, unsafe_allow_html=True)

    # Inicializar banco de dados e managers
    db = _get_database()
    managers = _get_managers(db)

    # Rotear para a página correta
    _route_to_page(db, managers)


if __name__ == "__main__":
    main()
