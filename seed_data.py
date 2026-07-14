"""Script para popular o banco com dados de demonstração."""

import uuid
from models.database import Database


def seed():
    db = Database("training.db")
    db.initialize()

    # Criar usuário admin
    db.execute(
        "INSERT OR IGNORE INTO users (id, name, email, is_first_visit, is_admin) "
        "VALUES (?, ?, ?, ?, ?)",
        ("admin-1", "Administrador", "admin@doit.com", False, True),
    )

    # ===== Módulo 1: Introdução ao Sistema =====
    mod1_id = "mod-intro"
    path1_id = "path-intro-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod1_id, "Introdução ao Sistema", "Aprenda os conceitos básicos e navegação do sistema DOit", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path1_id, mod1_id, "Principal", True),
    )

    steps_mod1 = [
        ("step-intro-1", "text", "# Bem-vindo ao DOit! 🎉\n\nO DOit é um sistema de gestão de projetos para escritórios de arquitetura e design.\n\nNeste módulo você aprenderá:\n- Como navegar pelo sistema\n- Os principais menus e funcionalidades\n- Como acessar seus projetos"),
        ("step-intro-2", "text", "# Navegação Principal\n\nO sistema possui os seguintes menus:\n\n1. **Dashboard** — Visão geral dos seus projetos\n2. **Projetos** — Lista completa de projetos\n3. **Tarefas** — Suas tarefas pendentes\n4. **Financeiro** — Controle financeiro\n5. **Contatos** — Clientes e fornecedores"),
        ("step-intro-3", "text", "# Seu Primeiro Passo\n\nAgora que você conhece os menus, vamos praticar!\n\n**Dica:** Sempre que tiver dúvida, procure o ícone ❓ no canto superior direito da tela.\n\n✅ Você completou a introdução ao sistema!"),
    ]

    for i, (step_id, ctype, content) in enumerate(steps_mod1):
        db.execute(
            "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, mod1_id, path1_id, i, "content"),
        )
        db.execute(
            "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"c-{step_id}", step_id, ctype, content, 0),
        )

    # ===== Módulo 2: Gestão de Projetos (com ramificação) =====
    mod2_id = "mod-projetos"
    path2_main = "path-proj-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod2_id, "Gestão de Projetos", "Aprenda a criar e gerenciar projetos no DOit com caminhos por perfil", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path2_main, mod2_id, "Principal", True),
    )

    # Etapa 1: conteúdo
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-proj-1", mod2_id, path2_main, 0, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-proj-1", "step-proj-1", "text", "# Gestão de Projetos\n\nO módulo de projetos é o coração do DOit. Aqui você pode:\n\n- Criar novos projetos\n- Acompanhar o andamento\n- Gerenciar equipes\n- Controlar prazos\n\nVamos começar! Na próxima etapa você escolherá seu perfil.", 0),
    )

    # Etapa 2: ramificação
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-proj-branch", mod2_id, path2_main, 1, "branch"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-proj-branch", "step-proj-branch", "text", "# Escolha seu perfil\n\nPara personalizar o treinamento, selecione seu perfil abaixo:", 0),
    )

    # Branch
    branch_id = "branch-perfil"
    db.execute(
        "INSERT OR IGNORE INTO branches (id, step_id) VALUES (?, ?)",
        (branch_id, "step-proj-branch"),
    )

    # Caminho A: Arquiteto
    path_arq = "path-arquiteto"
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, parent_branch_id, name, is_main) "
        "VALUES (?, ?, ?, ?, ?)",
        (path_arq, mod2_id, branch_id, "Sou Arquiteto(a)", False),
    )
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-arq-1", mod2_id, path_arq, 0, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-arq-1", "step-arq-1", "text", "# Projetos para Arquitetos\n\nComo arquiteto(a), você terá acesso a:\n\n- **Briefing do cliente** — Requisitos e preferências\n- **Cronograma de obra** — Fases e marcos\n- **Fornecedores** — Catálogo de materiais\n- **Pranchas** — Upload de arquivos DWG/PDF\n\n💡 Dica: Use o filtro 'Meus Projetos' para ver apenas os projetos onde você é responsável.", 0),
    )
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-arq-2", mod2_id, path_arq, 1, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-arq-2", "step-arq-2", "text", "# Criando um Novo Projeto\n\n1. Clique em **+ Novo Projeto**\n2. Preencha o briefing do cliente\n3. Defina as etapas do cronograma\n4. Adicione membros da equipe\n5. Salve e comece a trabalhar!\n\n✅ Você aprendeu o fluxo básico de projetos para arquitetos!", 0),
    )

    # Caminho B: Gestor
    path_gestor = "path-gestor"
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, parent_branch_id, name, is_main) "
        "VALUES (?, ?, ?, ?, ?)",
        (path_gestor, mod2_id, branch_id, "Sou Gestor(a) / Admin", False),
    )
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-gestor-1", mod2_id, path_gestor, 0, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-gestor-1", "step-gestor-1", "text", "# Projetos para Gestores\n\nComo gestor(a), você tem visão completa de todos os projetos:\n\n- **Dashboard** — KPIs e métricas do escritório\n- **Alocação** — Distribuição de equipes\n- **Financeiro** — Custos e faturamento por projeto\n- **Relatórios** — Exportação para Excel/PDF\n\n💡 Dica: Use o Dashboard para identificar projetos atrasados rapidamente.", 0),
    )
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-gestor-2", mod2_id, path_gestor, 1, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-gestor-2", "step-gestor-2", "text", "# Gerenciando Equipes\n\n1. Acesse **Configurações > Equipes**\n2. Adicione membros com seus perfis\n3. Defina permissões de acesso\n4. Acompanhe produtividade no relatório semanal\n\n✅ Você aprendeu o fluxo de gestão!", 0),
    )

    # Opções de branch
    db.execute(
        "INSERT OR IGNORE INTO branch_options (id, branch_id, label, path_id, position) "
        "VALUES (?, ?, ?, ?, ?)",
        ("opt-arq", branch_id, "Sou Arquiteto(a) — quero aprender sobre projetos de design", path_arq, 0),
    )
    db.execute(
        "INSERT OR IGNORE INTO branch_options (id, branch_id, label, path_id, position) "
        "VALUES (?, ?, ?, ?, ?)",
        ("opt-gestor", branch_id, "Sou Gestor(a) / Admin — quero a visão gerencial", path_gestor, 1),
    )

    # ===== Módulo 3: Financeiro =====
    mod3_id = "mod-financeiro"
    path3_id = "path-fin-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod3_id, "Controle Financeiro", "Gerencie pagamentos, recebimentos e fluxo de caixa do escritório", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path3_id, mod3_id, "Principal", True),
    )

    steps_mod3 = [
        ("step-fin-1", "text", "# Módulo Financeiro\n\nO controle financeiro do DOit permite:\n\n- Registrar receitas e despesas\n- Associar custos a projetos\n- Gerar relatórios de fluxo de caixa\n- Emitir cobranças para clientes"),
        ("step-fin-2", "text", "# Lançamentos\n\nPara registrar um lançamento:\n\n1. Vá em **Financeiro > Lançamentos**\n2. Clique em **+ Novo**\n3. Selecione: Receita ou Despesa\n4. Vincule ao projeto (opcional)\n5. Confirme\n\n✅ Módulo financeiro concluído!"),
    ]

    for i, (step_id, ctype, content) in enumerate(steps_mod3):
        db.execute(
            "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, mod3_id, path3_id, i, "content"),
        )
        db.execute(
            "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"c-{step_id}", step_id, ctype, content, 0),
        )

    db.commit()
    db.close()
    print("✅ Dados de demonstração criados com sucesso!")
    print("   - 3 módulos publicados")
    print("   - 1 ramificação (Arquiteto vs Gestor)")
    print("   - 1 usuário admin (admin@doit.com)")


if __name__ == "__main__":
    seed()
