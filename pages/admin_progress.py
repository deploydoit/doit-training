"""Painel de progresso dos usuários para administradores."""

import streamlit as st
from models.database import Database


def render_progress_panel(db: Database) -> None:
    """Renderiza painel com progresso de todos os usuários."""
    st.subheader("Progresso dos Usuários")

    # Buscar todos os usuários (exceto admins)
    users = db.execute(
        "SELECT id, name, email, last_login FROM users "
        "WHERE is_admin = 0 ORDER BY name"
    ).fetchall()

    if not users:
        st.info("Nenhum usuário cadastrado ainda.")
        return

    # Buscar todos os módulos publicados
    modules = db.execute(
        "SELECT id, title FROM modules WHERE status = 'published' ORDER BY title"
    ).fetchall()

    total_modules = len(modules)

    st.markdown(f"**{len(users)} usuário(s)** | **{total_modules} módulo(s) publicado(s)**")
    st.divider()

    for user in users:
        user_id = user["id"]
        user_name = user["name"]
        user_email = user["email"]

        # Contar módulos concluídos
        completed = db.execute(
            "SELECT COUNT(*) as cnt FROM user_progress "
            "WHERE user_id = ? AND status = 'completed'",
            (user_id,)
        ).fetchone()["cnt"]

        # Contar módulos em andamento
        in_progress = db.execute(
            "SELECT COUNT(*) as cnt FROM user_progress "
            "WHERE user_id = ? AND status = 'in_progress'",
            (user_id,)
        ).fetchone()["cnt"]

        # Percentual geral
        pct = (completed / total_modules * 100) if total_modules > 0 else 0

        # Card do usuário
        col_info, col_progress = st.columns([2, 1])

        with col_info:
            st.markdown(f"**{user_name}**")
            st.caption(user_email)

        with col_progress:
            st.markdown(f"{completed}/{total_modules} concluídos")

        st.progress(pct / 100.0)

        # Detalhes por módulo (expansível)
        with st.expander("Ver detalhes"):
            for mod in modules:
                prog = db.execute(
                    "SELECT status, percentage FROM user_progress "
                    "WHERE user_id = ? AND module_id = ?",
                    (user_id, mod["id"])
                ).fetchone()

                if prog is None:
                    status_label = "Não iniciado"
                elif prog["status"] == "completed":
                    status_label = "Concluído"
                else:
                    status_label = f"Em andamento ({prog['percentage']:.0f}%)"

                st.markdown(f"- {mod['title']} — {status_label}")

        st.divider()
