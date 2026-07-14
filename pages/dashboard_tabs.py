"""Renderização especial do módulo Dashboard com abas."""
import streamlit as st


def render_dashboard_tabs():
    """Renderiza o módulo Dashboard com abas para cada seção."""

    st.markdown("# Dashboard — Seu Painel Gerencial")
    st.markdown("Ao fazer login, você cai na Dashboard — um resumo de tudo que está acontecendo no escritório.")

    tabs = st.tabs([
        "Notificações",
        "Agenda",
        "Datas Importantes",
        "Recados",
        "Tarefas",
        "Financeiro",
        "Documentos a Expirar",
    ])

    with tabs[0]:
        st.markdown("""As notificações exibem alertas dos seus projetos. Você recebe avisos quando:

- Novas cobranças são geradas
- Prazo de um projeto se aproximando
- Projeto mudando de etapa
- Tarefa de um projeto que você lidera foi realizada
- Número de visitas ou horas de reuniões excederam as contratadas
- Horas trabalhadas excederam as contratadas""")
        _show_image("media/dashboard/notificacoes.png")
        st.markdown("*Observação: a visualização depende das suas permissões e dos projetos aos quais você está vinculado.*")

    with tabs[1]:
        st.markdown("""Resumo dos eventos que estão na sua agenda e nas agendas públicas que você ativou.

Por padrão, mostra o dia atual e o dia seguinte (máximo 5 dias).

Para alterar a quantidade de dias exibidos:
1. Clique nas suas iniciais (canto superior direito)
2. Vá em Pref. Pessoais
3. Acesse Agenda
4. Altere o campo "Dias dashboard"
""")
        _show_image("media/dashboard/agenda.png")

    with tabs[2]:
        st.markdown("""Exibe datas relevantes cadastradas no sistema:

- Aniversários de clientes e colaboradores
- Datas de contratação
- Datas de fundação de empresas
- Outras datas comemorativas ou de controle interno

Essas datas são registradas dentro dos cadastros feitos no sistema, no campo "Datas" da ficha.""")

    with tabs[3]:
        st.markdown("""Funciona como um sistema de lembretes internos entre usuários. Não é um chat.

Como funciona:
- Ao enviar um recado, o destinatário recebe uma notificação
- O destinatário não pode responder — é comunicação unidirecional
- Use para avisos rápidos e lembretes operacionais

Exemplos de uso:
- Solicitação de retorno para um fornecedor
- Avisos internos sobre prazos
- Lembretes operacionais""")

    with tabs[4]:
        st.markdown("""Mostra todas as tarefas pendentes atribuídas a você.

Ordenação: primeiro por prioridade, depois por prazo.
Limite: máximo 10 tarefas simultâneas.

Como usar o Start/Stop:
- Start — começa a contabilizar tempo dedicado à tarefa
- Stop — para a contagem (permite ajustar horários manualmente)
- Concluir — finaliza a tarefa com todas as horas registradas

As tarefas também são um dos métodos de lançamento de horas no sistema.""")
        _show_image("media/dashboard/tarefas.png")

    with tabs[5]:
        st.markdown("""**Financeiro** (requer acesso ao módulo)
- Contas vencidas
- Contas a vencer
- Pendências financeiras

**Faturamento** (requer acesso ao módulo)
- Gráficos com base nas notas fiscais emitidas
- Evolução financeira do mês""")
        st.markdown("*Observação: estes campos são visíveis apenas para usuários com permissão nos respectivos módulos.*")

    with tabs[6]:
        st.markdown("""Exibe documentos anexados no sistema que possuem data de vencimento próxima.

Regra padrão:
- Aparecem 20 dias antes do vencimento
- Ficam visíveis até 10 dias após o vencimento
- Esses prazos podem ser customizados

Os documentos podem estar vinculados a:
- Cadastros
- Projetos
- Reuniões""")


def _show_image(path):
    """Mostra imagem centralizada."""
    import base64
    from pathlib import Path
    img_path = Path(path)
    if img_path.exists():
        img_bytes = img_path.read_bytes()
        suffix = img_path.suffix.lower().replace('.', '')
        mime = f"image/{suffix}"
        b64 = base64.b64encode(img_bytes).decode()
        st.markdown(
            f'<div style="text-align:center;margin:12px 0;">'
            f'<img src="data:{mime};base64,{b64}" '
            f'style="width:100%;max-width:460px;height:auto;border-radius:8px;display:inline-block;'
            f'image-orientation:from-image;">'
            f'</div>',
            unsafe_allow_html=True,
        )
