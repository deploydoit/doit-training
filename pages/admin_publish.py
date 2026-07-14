"""Página de publicação e versionamento de módulos.

Interface administrativa para publicação de módulos de treinamento.
Realiza validação prévia, bloqueia publicação se houver problemas,
e gerencia o versionamento com migração de progresso dos usuários.

Requirements: 6.4, 6.5
"""

from __future__ import annotations

import streamlit as st

from managers.content_manager import ContentManager, PublishResult
from managers.errors import ModuleNotFoundError
from models.enums import ModuleStatus


def render_publish_module(content_manager: ContentManager, module_id: str) -> None:
    """Renderiza a interface de publicação de um módulo.

    Exibe o status atual do módulo, executa validação prévia ao clicar em
    publicar, e mostra resultado da publicação (sucesso ou erros bloqueantes).

    Args:
        content_manager: Instância do ContentManager.
        module_id: ID do módulo a ser publicado.

    Requirements: 6.4, 6.5
    """
    try:
        module_row = content_manager._get_module_row(module_id)
    except Exception:
        st.error("Erro ao carregar informações do módulo.")
        return

    if module_row is None:
        st.error("Módulo não encontrado.")
        return

    module_title = module_row["title"]
    module_version = module_row["version"]
    module_status = module_row["status"]

    # Cabeçalho
    st.subheader(" Publicação de Módulo")
    st.markdown(f"**Módulo:** {module_title}")

    # Informações da versão atual
    col_version, col_status = st.columns(2)
    with col_version:
        st.metric("Versão Atual", module_version)
    with col_status:
        status_label = _get_status_label(module_status)
        st.metric("Status", status_label)

    st.divider()

    # Seção de validação prévia
    _render_validation_section(content_manager, module_id)

    st.divider()

    # Botão de publicar
    _render_publish_button(content_manager, module_id, module_title, module_version)


def _render_validation_section(content_manager: ContentManager, module_id: str) -> None:
    """Renderiza a seção de validação prévia do módulo.

    Permite ao administrador executar a validação antes de publicar,
    visualizando erros que bloqueariam a publicação.

    Args:
        content_manager: Instância do ContentManager.
        module_id: ID do módulo.

    Requirements: 6.5
    """
    st.markdown("###  Validação Prévia")
    st.caption(
        "Verifique se o módulo está pronto para publicação. "
        "A publicação será bloqueada se houver problemas."
    )

    if st.button("Executar Validação", key="btn_validate"):
        with st.spinner("Validando módulo..."):
            try:
                errors = content_manager.validate_module(module_id)
            except ModuleNotFoundError:
                st.error("Módulo não encontrado.")
                return

        if not errors:
            st.success(" Módulo válido! Pronto para publicação.")
        else:
            st.error(
                f" Publicação bloqueada: {len(errors)} problema(s) encontrado(s)."
            )
            _display_validation_errors(errors)


def _render_publish_button(
    content_manager: ContentManager,
    module_id: str,
    module_title: str,
    current_version: int,
) -> None:
    """Renderiza o botão de publicar com confirmação e resultado.

    O botão executa validação + publicação em uma única operação.
    Se a validação falhar, a publicação é bloqueada e os erros são exibidos.
    Se a publicação for bem-sucedida, exibe a nova versão e usuários migrados.

    Args:
        content_manager: Instância do ContentManager.
        module_id: ID do módulo.
        module_title: Título do módulo (para confirmação).
        current_version: Versão atual do módulo.

    Requirements: 6.4, 6.5
    """
    st.markdown("###  Publicar Módulo")

    # Aviso sobre versionamento
    st.info(
        f"Ao publicar, a versão será incrementada de **{current_version}** para "
        f"**{current_version + 1}**. O progresso dos usuários que já iniciaram "
        f"o módulo será migrado automaticamente, preservando etapas concluídas "
        f"que ainda existem na nova versão."
    )

    # Confirmação antes de publicar
    confirm_key = f"confirm_publish_{module_id}"
    confirmed = st.checkbox(
        f"Confirmo que desejo publicar o módulo \"{module_title}\"",
        key=confirm_key,
    )

    if st.button(
        "Publicar Módulo",
        key="btn_publish",
        
        disabled=not confirmed,
    ):
        _execute_publish(content_manager, module_id)


def _execute_publish(content_manager: ContentManager, module_id: str) -> None:
    """Executa a publicação do módulo e exibe o resultado.

    Chama ContentManager.publish_module() que internamente valida,
    incrementa versão e migra progresso dos usuários.

    Args:
        content_manager: Instância do ContentManager.
        module_id: ID do módulo.

    Requirements: 6.4, 6.5
    """
    with st.spinner("Publicando módulo..."):
        try:
            result: PublishResult = content_manager.publish_module(module_id)
        except ModuleNotFoundError:
            st.error("Módulo não encontrado.")
            return
        except Exception as e:
            st.error(f"Erro inesperado ao publicar: {str(e)}")
            return

    if result.published:
        # Publicação bem-sucedida
        st.success(
            f" Módulo publicado com sucesso! Nova versão: **{result.version}**"
        )
        if result.migrated_users > 0:
            st.info(
                f" {result.migrated_users} usuário(s) tiveram seu progresso "
                f"migrado para a nova versão."
            )
        else:
            st.caption("Nenhum usuário tinha progresso para migrar.")

        # Sugestão para recarregar a página
        st.balloons()
    else:
        # Publicação bloqueada por erros de validação
        st.error(
            f" Publicação bloqueada: {len(result.errors)} problema(s) encontrado(s)."
        )
        _display_publish_errors(result.errors)


def _display_validation_errors(errors: list) -> None:
    """Exibe erros de validação de forma estruturada.

    Agrupa erros por tipo de elemento (etapa ou ramificação) e
    exibe em um formato legível para o administrador.

    Args:
        errors: Lista de ValidationErrorItem retornados por validate_module.

    Requirements: 6.5
    """
    step_errors = [e for e in errors if e.element_type == "step"]
    branch_errors = [e for e in errors if e.element_type == "branch"]

    if step_errors:
        st.markdown("**Etapas com problemas:**")
        for error in step_errors:
            st.markdown(f"-  {error.message}")

    if branch_errors:
        st.markdown("**Ramificações com problemas:**")
        for error in branch_errors:
            st.markdown(f"-  {error.message}")


def _display_publish_errors(errors: list[str]) -> None:
    """Exibe erros de publicação (strings simples) retornados pelo PublishResult.

    Args:
        errors: Lista de mensagens de erro.

    Requirements: 6.5
    """
    st.markdown("**Problemas que impedem a publicação:**")
    for error_msg in errors:
        st.markdown(f"-  {error_msg}")

    st.caption(
        "Corrija os problemas acima e tente publicar novamente. "
        "Todas as etapas devem ter conteúdo e ramificações devem ter "
        "entre 2 e 5 caminhos definidos."
    )


def _get_status_label(status: str) -> str:
    """Converte o status interno para um rótulo legível.

    Args:
        status: Valor do enum ModuleStatus.

    Returns:
        Rótulo formatado para exibição.
    """
    labels = {
        ModuleStatus.DRAFT.value: " Rascunho",
        ModuleStatus.PUBLISHED.value: " Publicado",
        ModuleStatus.ARCHIVED.value: " Arquivado",
    }
    return labels.get(status, status)
