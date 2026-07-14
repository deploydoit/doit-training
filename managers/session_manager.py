"""Gerenciador de Sessão do Sistema de Treinamento.

Controla o estado da aplicação através do st.session_state do Streamlit,
gerenciando:
- Dados do usuário autenticado (perfil)
- Página atual e navegação
- Módulo e etapa selecionados
- Estado de retomada de progresso

Requirements: 1.1, 1.2, 7.1
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from models.data_models import UserProfile


# Chaves padrão do session_state
_DEFAULT_STATE = {
    "current_page": "welcome",
    "user_profile": None,
    "user_id": None,
    "selected_module_id": None,
    "current_step_id": None,
    "current_path_id": None,
    "branch_source_step_id": None,
    "resume_module": False,
    "module_completed": False,
}


class SessionManager:
    """Gerenciador de estado da sessão do Streamlit.

    Centraliza a inicialização e acesso às variáveis de session_state,
    garantindo que todas as chaves necessárias existam com valores
    padrão antes de serem acessadas pela aplicação.
    """

    @staticmethod
    def initialize() -> None:
        """Inicializa o session_state com valores padrão.

        Apenas cria chaves que ainda não existem, preservando
        valores já definidos em reruns anteriores.
        """
        for key, default_value in _DEFAULT_STATE.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @staticmethod
    def get_current_page() -> str:
        """Retorna a página atual da navegação.

        Returns:
            Nome da página atual (welcome, module_list, step_view, admin).
        """
        return st.session_state.get("current_page", "welcome")

    @staticmethod
    def set_current_page(page: str) -> None:
        """Define a página atual da navegação.

        Args:
            page: Nome da página destino.
        """
        st.session_state["current_page"] = page

    @staticmethod
    def get_user_profile() -> Optional[UserProfile]:
        """Retorna o perfil do usuário logado.

        Returns:
            UserProfile se autenticado, None caso contrário.
        """
        return st.session_state.get("user_profile")

    @staticmethod
    def get_user_id() -> Optional[str]:
        """Retorna o ID do usuário logado.

        Returns:
            ID do usuário ou None.
        """
        return st.session_state.get("user_id")

    @staticmethod
    def is_authenticated() -> bool:
        """Verifica se o usuário está autenticado na sessão.

        Returns:
            True se há um perfil de usuário na sessão.
        """
        return st.session_state.get("user_profile") is not None

    @staticmethod
    def is_admin() -> bool:
        """Verifica se o usuário atual é administrador.

        Returns:
            True se o usuário é admin, False caso contrário.
        """
        profile = st.session_state.get("user_profile")
        if profile is None:
            return False
        return profile.is_admin

    @staticmethod
    def get_selected_module_id() -> Optional[str]:
        """Retorna o ID do módulo selecionado.

        Returns:
            ID do módulo ou None.
        """
        return st.session_state.get("selected_module_id")

    @staticmethod
    def get_current_step_id() -> Optional[str]:
        """Retorna o ID da etapa atual.

        Returns:
            ID da etapa ou None.
        """
        return st.session_state.get("current_step_id")

    @staticmethod
    def get_current_path_id() -> Optional[str]:
        """Retorna o ID do caminho atual.

        Returns:
            ID do caminho ou None.
        """
        return st.session_state.get("current_path_id")

    @staticmethod
    def should_resume_module() -> bool:
        """Verifica se deve retomar módulo de onde parou.

        Returns:
            True se deve retomar, False para iniciar do começo.
        """
        return st.session_state.get("resume_module", False)

    @staticmethod
    def clear_navigation_state() -> None:
        """Limpa o estado de navegação (módulo/etapa/caminho).

        Útil ao voltar para a lista de módulos.
        """
        st.session_state["selected_module_id"] = None
        st.session_state["current_step_id"] = None
        st.session_state["current_path_id"] = None
        st.session_state["branch_source_step_id"] = None
        st.session_state["resume_module"] = False
        st.session_state["module_completed"] = False

    @staticmethod
    def logout() -> None:
        """Limpa toda a sessão do usuário."""
        for key in _DEFAULT_STATE:
            st.session_state[key] = _DEFAULT_STATE[key]
