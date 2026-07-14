"""Página de boas-vindas e identificação do usuário.

Implementa a tela de boas-vindas para novos usuários e o formulário
de identificação (nome/email). Usuários que retornam ao sistema são
direcionados diretamente para a lista de módulos.

Requirements: 1.1, 1.2
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

import streamlit as st

from models.database import Database
from models.data_models import UserProfile


def _get_or_create_user(db: Database, name: str, email: str) -> UserProfile:
    """Busca usuário existente por email ou cria um novo.

    Se o usuário já existe, atualiza last_login e retorna o perfil.
    Se não existe, cria um novo usuário com is_first_visit=True.

    Args:
        db: Instância do banco de dados.
        name: Nome do usuário.
        email: Email do usuário.

    Returns:
        UserProfile do usuário encontrado ou criado.
    """
    row = db.execute(
        "SELECT id, name, email, is_first_visit, is_admin, created_at, last_login "
        "FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    now = datetime.now()

    if row is not None:
        # Atualizar last_login
        db.execute(
            "UPDATE users SET last_login = ?, name = ? WHERE id = ?",
            (now.isoformat(), name, row["id"]),
        )
        db.commit()
        return UserProfile(
            id=row["id"],
            name=name,
            email=row["email"],
            is_first_visit=bool(row["is_first_visit"]),
            is_admin=bool(row["is_admin"]),
            created_at=datetime.fromisoformat(row["created_at"])
            if isinstance(row["created_at"], str)
            else now,
            last_login=now,
        )

    # Criar novo usuário
    user_id = str(uuid4())
    db.execute(
        "INSERT INTO users (id, name, email, is_first_visit, is_admin, created_at, last_login) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, name, email, True, False, now.isoformat(), now.isoformat()),
    )
    db.commit()

    return UserProfile(
        id=user_id,
        name=name,
        email=email,
        is_first_visit=True,
        is_admin=False,
        created_at=now,
        last_login=now,
    )


def _mark_first_visit_complete(db: Database, user_id: str) -> None:
    """Marca que o usuário já viu a tela de boas-vindas.

    Atualiza is_first_visit para False no banco de dados.

    Args:
        db: Instância do banco de dados.
        user_id: ID do usuário.
    """
    db.execute(
        "UPDATE users SET is_first_visit = ? WHERE id = ?",
        (False, user_id),
    )
    db.commit()


def is_first_visit(db: Database, user_id: str) -> bool:
    """Verifica se é a primeira visita do usuário ao sistema.

    Args:
        db: Instância do banco de dados.
        user_id: ID do usuário.

    Returns:
        True se é a primeira visita, False caso contrário.
    """
    row = db.execute(
        "SELECT is_first_visit FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if row is None:
        return True

    return bool(row["is_first_visit"])


def _render_welcome_content() -> None:
    """Renderiza o conteúdo de boas-vindas com objetivo e instruções."""
    st.markdown("## Bem-vindo ao Sistema de Treinamento!")

    st.markdown(
        """
        ### Objetivo do Treinamento

        Este sistema foi criado para ajudar você a aprender e dominar
        as ferramentas e processos necessarios para o seu trabalho.
        Aqui você encontrara conteúdo interativo organizado em módulos,
        cada um focado em um tema especifico.
        """
    )

    st.markdown(
        """
        ### Como Navegar

        - **Módulos**: O conteúdo está organizado em módulos temáticos.
          Escolha o módulo que deseja explorar na lista.
        - **Avançar/Retroceder**: Use os botões de navegação para
          percorrer as etapas de cada módulo.
        - **Ramificações**: Em alguns pontos, você poderá escolher
          caminhos diferentes de acordo com seu perfil ou interesse.
        - **Progresso Salvo**: Seu progresso e salvo automaticamente.
          Você pode sair e voltar a qualquer momento sem perder o avanço.
        - **Conclusão**: Ao completar todas as etapas obrigatórias,
          o módulo será marcado como concluído.
        """
    )

    st.info(
        "Dica: Você pode explorar os módulos na ordem que preferir. "
        "Não ha uma sequencia obrigatoria entre módulos."
    )


def _render_identification_form(db: Database) -> Optional[UserProfile]:
    """Renderiza o formulário de identificação e retorna o perfil se submetido.

    Args:
        db: Instância do banco de dados.

    Returns:
        UserProfile se o formulário foi submetido com sucesso, None caso contrário.
    """
    st.markdown("---")
    st.markdown("Para começar, informe seus dados abaixo:")

    with st.form("identification_form", clear_on_submit=False):
        name = st.text_input(
            "Nome completo",
            placeholder="Digite seu nome completo",
            key="welcome_name_input",
        )
        email = st.text_input(
            "Email",
            placeholder="seu.email@empresa.com",
            key="welcome_email_input",
        )
        submitted = st.form_submit_button(
            "Começar Treinamento",
            use_container_width=True,
            
        )

    if submitted:
        # Validação
        if not name or not name.strip():
            st.error("Por favor, informe seu nome.")
            return None
        if not email or not email.strip():
            st.error("Por favor, informe seu email.")
            return None
        if "@" not in email or "." not in email.split("@")[-1]:
            st.error("Por favor, informe um email válido.")
            return None

        user = _get_or_create_user(db, name.strip(), email.strip().lower())
        return user

    return None


def render_welcome_page(db: Database) -> None:
    """Renderiza a página de boas-vindas e identificação do usuário.

    Fluxo:
    1. Se o usuário já está identificado na sessão e NÃO é primeira visita,
       sinaliza para redirecionar à lista de módulos.
    2. Se é primeira visita, mostra conteúdo de boas-vindas + formulário.
    3. Se o usuário não está identificado, mostra apenas o formulário.

    Após identificação:
    - Se is_first_visit=True: exibe boas-vindas, marca como visitado e
      permite avançar para módulos.
    - Se is_first_visit=False: redireciona direto para lista de módulos.

    Args:
        db: Instância do banco de dados.
    """
    # Se já há um usuário na sessão, verificar se precisa ver boas-vindas
    if st.session_state.get("user_profile") is not None:
        user: UserProfile = st.session_state["user_profile"]
        if not is_first_visit(db, user.id):
            # Não é primeira visita - sinalizar redirecionamento
            st.session_state["current_page"] = "module_list"
            st.rerun()
            return

        # É primeira visita - mostrar boas-vindas
        _render_welcome_content()
        st.markdown("---")
        st.markdown(f"Olá, **{user.name}**! Vamos começar?")
        if st.button(
            "Ir para os Módulos",
            use_container_width=True,
            
            key="go_to_modules_btn",
        ):
            _mark_first_visit_complete(db, user.id)
            st.session_state["user_profile"] = UserProfile(
                id=user.id,
                name=user.name,
                email=user.email,
                is_first_visit=False,
                is_admin=user.is_admin,
                created_at=user.created_at,
                last_login=user.last_login,
            )
            st.session_state["current_page"] = "module_list"
            st.rerun()
        return

    # Nenhum usuário na sessão - mostrar formulário de identificação
    st.markdown("## Sistema de Treinamento DOit")

    user = _render_identification_form(db)

    if user is not None:
        st.session_state["user_profile"] = user
        st.session_state["user_id"] = user.id

        if user.is_first_visit:
            # Primeira visita - rerun para mostrar boas-vindas
            st.rerun()
        else:
            # Visita subsequente - ir direto para módulos
            st.session_state["current_page"] = "module_list"
            st.rerun()
