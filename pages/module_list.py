"""Página de lista de módulos do Sistema de Treinamento.

Renderiza os módulos disponíveis como cards com informações de progresso,
indicadores visuais de status e opção de continuar de onde parou.

Requirements: 1.3, 1.5, 5.2, 5.3
"""

from __future__ import annotations

import streamlit as st
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from managers.training_manager import ModuleInfo

from models.enums import ProgressStatus


def render_module_list(user_id: str, modules: list["ModuleInfo"]) -> None:
    """Renderiza lista de módulos com status de progresso.

    Exibe cards para cada módulo com título, descrição (≤150 caracteres),
    quantidade de etapas e indicadores visuais de progresso. Trata o caso
    de nenhum módulo disponível.

    Args:
        user_id: ID do usuário logado.
        modules: Lista de ModuleInfo retornada por TrainingManager.get_modules().

    Requirements: 1.3, 1.5, 5.2, 5.3
    """
    # Tratar caso de nenhum módulo disponível (Req 1.5)
    if not modules:
        _render_empty_state()
        return

    # Renderizar cards dos módulos
    for module in modules:
        _render_module_card(module)


def _render_empty_state() -> None:
    """Renderiza mensagem quando nenhum módulo está disponível.

    Requirements: 1.5
    """
    st.markdown(
        """
        <div style="
            text-align: center;
            padding: 60px 20px;
            background-color: #f8f9fa;
            border-radius: 12px;
            margin-top: 20px;
        ">
            <div style="font-size: 48px; margin-bottom: 16px;"></div>
            <h3 style="color: #6c757d; margin-bottom: 8px;">
                Nenhum módulo disponível no momento
            </h3>
            <p style="color: #adb5bd; font-size: 14px;">
                Novos conteúdos de treinamento serão adicionados em breve.
                Volte mais tarde para verificar.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_module_card(module: "ModuleInfo") -> None:
    """Renderiza card individual de um módulo com informações e status.

    Exibe título, descrição, quantidade de etapas, indicador de progresso
    e botão de ação adequado ao status.

    Args:
        module: ModuleInfo com dados do módulo e progresso do usuário.

    Requirements: 1.3, 5.2, 5.3
    """
    status_config = _get_status_config(module.progress_status, module.progress_percentage)

    # Card container com borda colorida pelo status
    with st.container():
        st.markdown(
            f"""
            <div style="
                border-left: 4px solid {status_config['border_color']};
                background-color: {status_config['bg_color']};
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 16px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            ">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex: 1;">
                        <h3 style="margin: 0 0 8px 0; color: #404040; font-size: 18px;">
                            {status_config['icon']} {module.title}
                        </h3>
                        <p style="margin: 0 0 12px 0; color: #404040; font-size: 14px; line-height: 1.5;">
                            {module.description[:150]}
                        </p>
                        <div style="display: flex; gap: 16px; align-items: center; flex-wrap: wrap;">
                            <span style="
                                font-size: 13px;
                                color: #6c757d;
                                background-color: #e9ecef;
                                padding: 4px 10px;
                                border-radius: 12px;
                            ">
                                {module.total_steps} etapa{"s" if module.total_steps != 1 else ""}
                            </span>
                            <span style="
                                font-size: 13px;
                                color: {status_config['text_color']};
                                background-color: {status_config['badge_bg']};
                                padding: 4px 10px;
                                border-radius: 12px;
                                font-weight: 500;
                            ">
                                {status_config['badge_text']}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Barra de progresso para módulos em andamento
        if module.progress_status == ProgressStatus.IN_PROGRESS:
            st.progress(
                module.progress_percentage / 100.0,
                text=f"{module.progress_percentage:.0f}% concluído",
            )

        # Botões de ação (largura total)
        if module.progress_status == ProgressStatus.IN_PROGRESS:
            if st.button(
                "Continuar",
                key=f"continue_{module.id}",
                use_container_width=True,
            ):
                st.session_state["selected_module_id"] = module.id
                st.session_state["resume_module"] = True
                st.session_state["current_page"] = "step_view"
                st.rerun()
        elif module.progress_status == ProgressStatus.COMPLETED:
            if st.button(
                "Revisar",
                key=f"review_{module.id}",
                use_container_width=True,
                help="Módulo concluído",
            ):
                st.session_state["selected_module_id"] = module.id
                st.session_state["resume_module"] = False
                st.session_state["current_page"] = "step_view"
                st.rerun()
        else:
            if st.button(
                "Iniciar",
                key=f"start_{module.id}",
                use_container_width=True,
            ):
                st.session_state["selected_module_id"] = module.id
                st.session_state["resume_module"] = False
                st.session_state["current_page"] = "step_view"
                st.rerun()

        st.markdown("---")


def _get_status_config(
    status: ProgressStatus, percentage: float
) -> dict[str, str]:
    """Retorna configuração visual para o status de progresso.

    Define cores, ícones e textos distintos para cada estado:
    - Concluído: verde com ícone de check
    - Em andamento: azul com percentual
    - Não iniciado: cinza

    Args:
        status: Status de progresso do módulo.
        percentage: Percentual de conclusão (0-100).

    Returns:
        Dicionário com chaves de configuração visual.

    Requirements: 5.3
    """
    if status == ProgressStatus.COMPLETED:
        return {
            "icon": "",
            "border_color": "#28a745",
            "bg_color": "#f0fff4",
            "text_color": "#28a745",
            "badge_bg": "#d4edda",
            "badge_text": "Concluído",
        }
    elif status == ProgressStatus.IN_PROGRESS:
        return {
            "icon": "",
            "border_color": "#F5C085",
            "bg_color": "#FFFFD6",
            "text_color": "#404040",
            "badge_bg": "#FFFFD6",
            "badge_text": f"Em andamento — {percentage:.0f}%",
        }
    else:  # NOT_STARTED
        return {
            "icon": "",
            "border_color": "#C0C0C0",
            "bg_color": "#ffffff",
            "text_color": "#404040",
            "badge_bg": "#F4F4F4",
            "badge_text": "Não iniciado",
        }
