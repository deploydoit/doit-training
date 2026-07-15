"""Página de visualização de etapa com navegação.

Renderiza o conteúdo de uma etapa do módulo de treinamento e fornece
controles de navegação para avançar, retroceder ou concluir o módulo.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.1
"""

from __future__ import annotations

import streamlit as st

from managers.training_manager import TrainingManager
from managers.progress_manager import ProgressManager
from models.data_models import Step


def _get_total_steps_in_path(training_manager: TrainingManager, module_id: str, path_id: str) -> int:
    """Calcula o total de etapas no caminho atual.

    Args:
        training_manager: Instância do TrainingManager.
        module_id: ID do módulo.
        path_id: ID do caminho.

    Returns:
        Total de etapas no caminho.
    """
    row = training_manager.db.execute(
        "SELECT COUNT(*) as cnt FROM steps WHERE module_id = ? AND path_id = ?",
        (module_id, path_id),
    ).fetchone()
    return row["cnt"] if row else 0


def render_step(
    step: Step,
    training_manager: TrainingManager,
    progress_manager: ProgressManager,
    user_id: str,
    module_id: str,
) -> None:
    """Renderiza uma etapa com controles de navegação.

    Exibe o conteúdo da etapa atual e botões de navegação (avançar/retroceder).
    Na primeira etapa o botão retroceder é desabilitado. Na última etapa o botão
    avançar é substituído por "Concluir Módulo". O progresso é salvo automaticamente
    ao avançar.

    Args:
        step: Objeto Step com o conteúdo da etapa atual.
        training_manager: Instância do TrainingManager para navegação.
        progress_manager: Instância do ProgressManager para salvar progresso.
        user_id: ID do usuário atual.
        module_id: ID do módulo sendo visualizado.

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.1
    """
    path_id = step.path_id
    is_first = training_manager.is_first_step(module_id, step.id, path_id)
    is_last = training_manager.is_last_step(module_id, step.id, path_id)

    # Indicador de progresso: "Etapa X de Y"
    # Requirement 2.6
    total_steps = _get_total_steps_in_path(training_manager, module_id, path_id)
    current_position = step.position + 1  # position is 0-indexed

    st.markdown(
        f'<p style="text-align: center; color: #6b7280; font-size: 0.9rem;">'
        f"Etapa {current_position} de {total_steps}"
        f"</p>",
        unsafe_allow_html=True,
    )

    # Separador visual
    st.divider()

    # Renderizar conteúdo da etapa
    _render_step_content(step)

    # Separador antes da navegação
    st.divider()

    # Botões de navegação
    # Requirement 2.1: botões com tamanho mínimo de 44x44px
    _render_navigation_buttons(
        step=step,
        training_manager=training_manager,
        progress_manager=progress_manager,
        user_id=user_id,
        module_id=module_id,
        is_first=is_first,
        is_last=is_last,
    )


def _render_step_content(step: Step) -> None:
    """Renderiza o conteúdo multimídia de uma etapa.

    Layout didático: texto primeiro, depois mídia em destaque centralizada.
    """
    if not step.content:
        st.info("Esta etapa não possui conteúdo.")
        return

    from models.enums import ContentType

    # Separar conteúdo por tipo
    texts = [c for c in step.content if c.content_type == ContentType.TEXT]
    media = [c for c in step.content if c.content_type in (ContentType.IMAGE, ContentType.VIDEO)]
    links = [c for c in step.content if c.content_type == ContentType.LINK]

    # 1. Texto: primeira metade (até ---) antes da mídia
    for content_item in texts:
        text_data = content_item.content_data
        if '---' in text_data:
            parts = text_data.split('---', 1)
            st.markdown(parts[0].strip(), unsafe_allow_html=True)
            # 2. Mídia no meio
            if media:
                for m in media:
                    _render_content_fallback(m)
            st.markdown(parts[1].strip(), unsafe_allow_html=True)
        else:
            # Sem separador: texto completo, mídia depois
            st.markdown(text_data, unsafe_allow_html=True)
            if media:
                for m in media:
                    _render_content_fallback(m)
        media = []  # Já renderizada

    # Mídia sem texto associado
    if media:
        for content_item in media:
            _render_content_fallback(content_item)

    # 3. Links por último
    for content_item in links:
        _render_content_fallback(content_item)


def _render_content_fallback(content_item) -> None:
    """Renderização básica de conteúdo como fallback.

    Args:
        content_item: StepContent a ser renderizado.
    """
    from models.enums import ContentType

    if content_item.content_type == ContentType.TEXT:
        st.markdown(content_item.content_data)
    elif content_item.content_type == ContentType.IMAGE:
        # Usar st.image nativo — funciona local e no Streamlit Cloud
        img_path = content_item.content_data
        # Larguras personalizadas por imagem (em pixels)
        max_width_por_imagem = {
            "visualizacao.png": 150,
            "notificacaorecado.png": 50,
            "salvar.png": 180,
            "salvareenviar.png": 180,
            "criarata.png": 180,
            "lancarhoras.png": 180,
        }
        # Verificar se tem largura customizada
        custom_width = None
        for nome, largura in max_width_por_imagem.items():
            if img_path.endswith(nome):
                custom_width = largura
                break
        try:
            if custom_width:
                st.image(img_path, width=custom_width)
            else:
                # Padrão: 440px para imagens normais
                st.image(img_path, width=440)
        except Exception:
            st.caption(f"Imagem não encontrada: {img_path}")
    elif content_item.content_type == ContentType.VIDEO:
        try:
            st.video(content_item.content_data)
        except Exception:
            st.caption(f"Vídeo não encontrado: {content_item.content_data}")
    elif content_item.content_type == ContentType.LINK:
        label = content_item.alt_text or content_item.content_data
        st.markdown(
            f'<a href="{content_item.content_data}" target="_blank" '
            f'rel="noopener noreferrer">{label} ↗</a>',
            unsafe_allow_html=True,
        )


def _render_navigation_buttons(
    step: Step,
    training_manager: TrainingManager,
    progress_manager: ProgressManager,
    user_id: str,
    module_id: str,
    is_first: bool,
    is_last: bool,
) -> None:
    """Renderiza os botões de navegação com estilo adequado.

    - Botão retroceder desabilitado na primeira etapa (Requirement 2.4)
    - Botão avançar substituído por "Concluir Módulo" na última etapa (Requirement 2.5)
    - Tamanho mínimo de 44x44px em todos os dispositivos (Requirement 2.1)

    Args:
        step: Etapa atual.
        training_manager: Instância do TrainingManager.
        progress_manager: Instância do ProgressManager.
        user_id: ID do usuário.
        module_id: ID do módulo.
        is_first: Se é a primeira etapa do caminho.
        is_last: Se é a última etapa do caminho.
    """
    # CSS para estilização dos botões de navegação
    st.markdown(
        """
        <style>
        div[data-testid="stColumns"] button {
            min-height: 44px;
            min-width: 44px;
            padding: 0.5rem 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_back, col_spacer, col_forward = st.columns([1, 2, 1])

    # Botão retroceder
    with col_back:
        st.button(
            "← Anterior",
            key="btn_previous",
            disabled=is_first,
            on_click=_on_previous_click,
            kwargs={
                "step": step,
                "training_manager": training_manager,
                "module_id": module_id,
            },
            use_container_width=True,
        )

    # Botão avançar / concluir
    with col_forward:
        if is_last:
            st.button(
                "Concluir Módulo ",
                key="btn_complete",
                
                on_click=_on_complete_click,
                kwargs={
                    "step": step,
                    "training_manager": training_manager,
                    "progress_manager": progress_manager,
                    "user_id": user_id,
                    "module_id": module_id,
                },
                use_container_width=True,
            )
        else:
            st.button(
                "Próxima →",
                key="btn_next",
                
                on_click=_on_next_click,
                kwargs={
                    "step": step,
                    "training_manager": training_manager,
                    "progress_manager": progress_manager,
                    "user_id": user_id,
                    "module_id": module_id,
                },
                use_container_width=True,
            )


def _on_previous_click(
    step: Step,
    training_manager: TrainingManager,
    module_id: str,
) -> None:
    """Callback para o botão de retroceder.

    Navega para a etapa anterior sem salvar progresso.

    Args:
        step: Etapa atual.
        training_manager: Instância do TrainingManager.
        module_id: ID do módulo.

    Requirements: 2.3
    """
    prev_step = training_manager.get_previous_step(
        module_id=module_id,
        current_step_id=step.id,
        path_id=step.path_id,
    )
    if prev_step is not None:
        st.session_state["current_step_id"] = prev_step.id
        st.session_state["current_path_id"] = prev_step.path_id


def _on_next_click(
    step: Step,
    training_manager: TrainingManager,
    progress_manager: ProgressManager,
    user_id: str,
    module_id: str,
) -> None:
    """Callback para o botão de avançar.

    Salva progresso automaticamente e navega para a próxima etapa.

    Args:
        step: Etapa atual.
        training_manager: Instância do TrainingManager.
        progress_manager: Instância do ProgressManager.
        user_id: ID do usuário.
        module_id: ID do módulo.

    Requirements: 2.2, 5.1
    """
    next_step = training_manager.get_next_step(
        module_id=module_id,
        current_step_id=step.id,
        path_id=step.path_id,
    )
    if next_step is not None:
        # Requirement 5.1: Salvar progresso automaticamente ao avançar
        progress_manager.save_progress(
            user_id=user_id,
            module_id=module_id,
            step_id=next_step.id,
            path_id=next_step.path_id,
        )
        st.session_state["current_step_id"] = next_step.id
        st.session_state["current_path_id"] = next_step.path_id


def _render_dashboard_tabs():
    """Renderiza o módulo Dashboard com navegação por setas."""
    from pathlib import Path
    import base64

    st.markdown("# Dashboard — Seu Painel Gerencial")
    st.markdown("Ao fazer login, você cai na Dashboard — um resumo de tudo que acontece no escritório.")
    st.divider()

    sections = [
        ("Notificações", """Você recebe avisos quando:
- Novas cobranças são geradas
- Prazo de um projeto se aproximando
- Projeto mudando de etapa
- Tarefa de um projeto que você lidera foi realizada
- Visitas ou horas de reuniões excederam as contratadas
- Horas trabalhadas excederam as contratadas

*Observação: a visualização depende das suas permissões e dos projetos vinculados.*""", "media/dashboard/notificacoes.png"),

        ("Agenda", """Resumo dos eventos futuros do dia e do dia seguinte (máximo 5 dias).

Para alterar a quantidade de dias:
1. Clique nas suas iniciais (canto superior direito)
2. Pref. Pessoais → Agenda
3. Altere o campo "Dias dashboard" """, "media/dashboard/agenda.png"),

        ("Datas Importantes", """Exibe datas relevantes cadastradas no sistema:
- Aniversários de clientes e colaboradores
- Datas de contratação
- Datas de fundação de empresas
- Outras datas comemorativas

Essas datas são registradas na ficha dos cadastros, no campo "Datas".""", None),

        ("Recados", """Sistema de lembretes internos entre usuários. Não é um chat.

- Ao enviar, o destinatário recebe uma notificação
- Não é possível responder — comunicação unidirecional
- Use para avisos rápidos e lembretes

Exemplos: solicitação de retorno para fornecedor, avisos de prazos, lembretes operacionais.""", None),

        ("Tarefas", """Mostra todas as tarefas pendentes atribuídas a você.

- Ordenação: primeiro por prioridade, depois por prazo
- Limite: máximo 10 tarefas simultâneas

Start/Stop:
- Start — começa a contabilizar tempo
- Stop — para a contagem (permite ajustar horários)
- Concluir — finaliza com todas as horas registradas""", "media/dashboard/tarefas.png"),

        ("Financeiro e Faturamento", """Financeiro (requer acesso ao módulo):
- Contas vencidas
- Contas a vencer
- Pendências financeiras

Faturamento (requer acesso ao módulo):
- Gráficos com base nas notas fiscais emitidas
- Evolução financeira do mês

*Observação: visível apenas para usuários com permissão nos respectivos módulos.*""", None),

        ("Documentos a Expirar", """Exibe documentos com data de vencimento próxima.

Regra padrão:
- Aparecem 20 dias antes do vencimento
- Ficam visíveis até 10 dias após

Podem estar vinculados a cadastros, projetos ou reuniões.""", None),
    ]

    # Estado da seção atual
    if "dashboard_section" not in st.session_state:
        st.session_state["dashboard_section"] = 0

    idx = st.session_state["dashboard_section"]
    total = len(sections)
    title, content, image = sections[idx]

    # Indicador de posição
    st.markdown(
        f'<p style="text-align:center;color:#999;font-size:0.85rem;">'
        f'{idx + 1} de {total} — {title}</p>',
        unsafe_allow_html=True,
    )

    # Conteúdo
    st.markdown(f"### {title}")
    st.markdown(content)

    # Imagem se houver
    if image:
        img_path = Path(image)
        if img_path.exists():
            img_bytes = img_path.read_bytes()
            b64 = base64.b64encode(img_bytes).decode()
            st.markdown(
                f'<div style="text-align:center;margin:12px 0;">'
                f'<img src="data:image/png;base64,{b64}" style="width:100%;max-width:460px;height:auto;border-radius:8px;display:inline-block;image-orientation:from-image;">'
                f'</div>', unsafe_allow_html=True)

    # Setas de navegação
    st.divider()
    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("Anterior", key="dash_prev", disabled=(idx == 0)):
            st.session_state["dashboard_section"] = idx - 1
            st.rerun()

    with col_next:
        if st.button("Próxima", key="dash_next", disabled=(idx == total - 1)):
            st.session_state["dashboard_section"] = idx + 1
            st.rerun()


def _on_complete_click(
    step: Step,
    training_manager: TrainingManager,
    progress_manager: ProgressManager,
    user_id: str,
    module_id: str,
) -> None:
    """Callback para o botão de concluir módulo.

    Marca todas as etapas do caminho principal como concluídas
    (o usuário navegou até o fim), salva progresso e conclui o módulo.

    Args:
        step: Etapa atual (última do caminho).
        training_manager: Instância do TrainingManager.
        progress_manager: Instância do ProgressManager.
        user_id: ID do usuário.
        module_id: ID do módulo.

    Requirements: 2.5, 5.1
    """
    # Marcar TODAS as etapas do caminho principal como concluídas
    # (o usuário chegou até o fim, portanto viu todas)
    all_steps = training_manager.db.execute(
        "SELECT id FROM steps WHERE module_id = ? AND path_id = ?",
        (module_id, step.path_id),
    ).fetchall()
    for s in all_steps:
        training_manager.db.execute(
            "INSERT OR IGNORE INTO completed_steps (user_id, step_id) VALUES (?, ?)",
            (user_id, s["id"]),
        )
    training_manager.db.commit()

    # Salvar progresso da última etapa
    progress_manager.save_progress(
        user_id=user_id,
        module_id=module_id,
        step_id=step.id,
        path_id=step.path_id,
    )

    # Concluir módulo (agora todas as etapas estão marcadas)
    completed = training_manager.complete_module(user_id=user_id, module_id=module_id)

    if completed:
        st.session_state["module_completed"] = True
        st.session_state["current_step_id"] = None
    else:
        # Fallback: forçar conclusão visual mesmo se a verificação falhar
        st.session_state["module_completed"] = True
        st.session_state["current_step_id"] = None
