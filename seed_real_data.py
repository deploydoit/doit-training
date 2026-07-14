"""Script para popular o banco com conteúdo REAL do manual DOit.

Remove todos os dados de demonstração e insere módulos baseados no
manual oficial do Sistema DOit.
"""

import sys
from pathlib import Path

# Garantir que o diretório do projeto está no path
sys.path.insert(0, str(Path(__file__).parent))

from models.database import Database


def clear_data(db: Database) -> None:
    """Remove todos os dados existentes (exceto tabela users)."""
    tables = [
        "explored_paths",
        "completed_steps",
        "user_progress",
        "branch_options",
        "branches",
        "step_contents",
        "steps",
        "paths",
        "modules",
    ]
    for table in tables:
        db.execute(f"DELETE FROM {table}")
    db.commit()
    print("🗑️  Dados anteriores removidos.")


def seed():
    db = Database("training.db")
    db.initialize()

    # Limpar dados existentes
    clear_data(db)

    # ===== Usuário Admin =====
    db.execute(
        "INSERT OR IGNORE INTO users (id, name, email, is_first_visit, is_admin) "
        "VALUES (?, ?, ?, ?, ?)",
        ("admin-1", "Administrador", "admin@doit.com", False, True),
    )

    # =========================================================================
    # MÓDULO 1: Dashboard (3 steps, linear)
    # =========================================================================
    mod1_id = "mod-dashboard"
    path1_main = "path-dashboard-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod1_id, "Dashboard", "Sua visão geral do sistema — agenda, tarefas, recados e documentos", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path1_main, mod1_id, "Principal", True),
    )

    steps_mod1 = [
        ("step-dash-1", "text", "# Dashboard — Sua Visão Geral\n\nA Dashboard é um resumo do que está acontecendo no seu sistema. A visualização dos itens pode variar de acordo com o nível de acesso.\n\nAqui você encontra:\n- **Agenda** — Resumo dos eventos do dia atual e seguinte\n- **Datas Importantes** — Aniversários, contratações, fundações\n- **Recados** — Comunicação rápida entre usuários\n- **Tarefas** — Suas tarefas pendentes com Start/Stop\n- **Documentos a Expirar** — Alertas de vencimento"),
        ("step-dash-2", "text", "# Campo: Tarefas\n\nQuando uma tarefa é delegada a você, ela aparece aqui na Dashboard.\n\n**Como funciona:**\n1. Tarefas são ordenadas por prioridade e depois por prazo\n2. Máximo de 10 tarefas visíveis simultaneamente\n3. Clique no botão ▶️ (Start) para iniciar a contagem de horas\n4. Clique no botão ⏹️ (Stop) para parar a contagem\n5. Após o Stop, você pode ajustar a data de início/fim manualmente\n6. Para finalizar uma tarefa sem mais horas, clique no ☐ (checkbox)\n\n💡 **Dica:** Se esquecer de parar o cronômetro, edite manualmente após clicar Stop."),
        ("step-dash-3", "text", "# Campo: Documentos a Expirar\n\nDocumentos com data de vencimento aparecem aqui automaticamente.\n\n**Configuração padrão:**\n- Aparecem **20 dias antes** do vencimento\n- Ficam visíveis até **10 dias após** o vencimento\n- Configuração pode ser personalizada\n\n**Exemplos de uso:**\n- RG com validade\n- Contratos assinados\n- Certificados digitais\n\n✅ Módulo Dashboard concluído!"),
    ]

    for i, (step_id, ctype, content) in enumerate(steps_mod1):
        db.execute(
            "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, mod1_id, path1_main, i, "content"),
        )
        db.execute(
            "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"c-{step_id}", step_id, ctype, content, 0),
        )

    # =========================================================================
    # MÓDULO 2: Cadastros (5 steps main, branching at step 3)
    # =========================================================================
    mod2_id = "mod-cadastros"
    path2_main = "path-cadastros-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod2_id, "Cadastros", "O coração do sistema — clientes, fornecedores, colaboradores e empresas", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path2_main, mod2_id, "Principal", True),
    )

    # Step 1
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-cad-1", mod2_id, path2_main, 0, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-cad-1", "step-cad-1", "text", "# Módulo: Cadastros\n\nO módulo Cadastro é o **coração do Sistema DOit**. Aqui ficam armazenadas as informações de todos os cadastros:\n\n- 👥 Clientes\n- 🏭 Fornecedores\n- 👷 Colaboradores\n- 🏢 Empresas parceiras\n\n**Ações principais:**\n- Criar cadastros\n- Busca avançada (Bairro, CEP, Cidade, Documento, UF)\n- Relatórios em PDF e Excel\n- Criação de listas de e-mail", 0),
    )

    # Step 2
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-cad-2", mod2_id, path2_main, 1, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-cad-2", "step-cad-2", "text", "# Listas de Cadastro\n\nO DOit oferece duas visualizações:\n\n### Lista 1\nFiltros básicos: ID, Nome, Apelido, E-mail, Telefone\n\n### Lista 2\nMesmo conteúdo + filtros avançados: Origem, Classificação, Anotações, UF\n\n💡 **Dica:** Use a Lista 2 quando precisar de filtros mais específicos, como buscar todos os fornecedores de São Paulo.", 0),
    )

    # Step 3 (BRANCH step)
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-cad-3", mod2_id, path2_main, 2, "branch"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-cad-3", "step-cad-3", "text", "# Ficha de Cadastro\n\nA ficha abre ao clicar no ID de um cadastro. Ela contém:\n- Origem, Classificação, Informações Cadastrais\n- E-mails, Telefones, Documentos (CPF/CNPJ), Datas\n- Anotações\n\n**Sub-abas na parte inferior:**\nContatos, Endereços, Documentos, Compromissos, Tarefas, E-mail, Projetos\n\n👇 Escolha o que deseja aprender:", 0),
    )

    # Branch for Cadastros
    branch_cad = "branch-cad-ficha"
    db.execute(
        "INSERT OR IGNORE INTO branches (id, step_id) VALUES (?, ?)",
        (branch_cad, "step-cad-3"),
    )

    # Path A: Campos da Ficha
    path_cad_campos = "path-cad-campos"
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, parent_branch_id, name, is_main) "
        "VALUES (?, ?, ?, ?, ?)",
        (path_cad_campos, mod2_id, branch_cad, "Campos da Ficha", False),
    )

    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-cad-campos-1", mod2_id, path_cad_campos, 0, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-cad-campos-1", "step-cad-campos-1", "text", "# Campos da Ficha\n\n**Origem:** Como o cadastro conheceu seus serviços (ex: Instagram 2023)\n\n**Classificação:** Categorias personalizáveis (Fornecedor, Piso, Laminado, etc). Clique no texto para trocar.\n\n**Informações Cadastrais:** Nome, Apelido e Website\n\n**E-mails:** O marcado com ● é o principal\n\n**Telefones:** O marcado com ● é o principal\n\n**Documentos:** CPF/CNPJ (validado automaticamente), Instagram, IE. Clique no texto cinza para trocar o tipo.", 0),
    )

    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-cad-campos-2", mod2_id, path_cad_campos, 1, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-cad-campos-2", "step-cad-campos-2", "text", "# Campos: Datas e Anotações\n\n**Datas:** Fundação, Aniversário, etc. Clique no texto cinza para trocar o tipo.\n\n**Anotações:** Campo livre para qualquer informação que não se encaixa nos outros campos.\n\n💡 **Dica: Tornar cadastro privado**\nNo ícone de cadeado, selecione quais usuários podem acessar. Clique Salvar. Para reverter, clique no cadeado > Tornar Público.\n\n✅ Campos da ficha concluídos!", 0),
    )

    # Path B: Sub-abas da Ficha
    path_cad_subabas = "path-cad-subabas"
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, parent_branch_id, name, is_main) "
        "VALUES (?, ?, ?, ?, ?)",
        (path_cad_subabas, mod2_id, branch_cad, "Sub-abas da Ficha", False),
    )

    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-cad-subabas-1", mod2_id, path_cad_subabas, 0, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-cad-subabas-1", "step-cad-subabas-1", "text", "# Sub-abas da Ficha\n\n**Contatos:** Vincule relações entre cadastros (Esposo/a, Sócio/a, etc)\n\n**Endereços:** Crie e edite endereços. Marque um como principal com ☑️\n\n**Documentos:** Adicione comprovantes, RG, etc. Marque como principal com ☑️. Oculte com o ícone de privacidade.\n\n**Compromissos:** Eventos vinculados ao cadastro (aparecem na Agenda)", 0),
    )

    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-cad-subabas-2", mod2_id, path_cad_subabas, 1, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-cad-subabas-2", "step-cad-subabas-2", "text", "# Sub-abas: Tarefas, E-mail e Projetos\n\n**Tarefas:** Crie, edite e exclua tarefas do cadastro. Extraia relatório com ícone de impressora.\n\n**E-mail:** Histórico de todos os e-mails enviados para este cadastro.\n\n**Projetos:** Visualize projetos onde o cadastro é cliente, fornecedor ou contato.\n\n✅ Sub-abas da ficha concluídas!", 0),
    )

    # Branch options for Cadastros
    db.execute(
        "INSERT OR IGNORE INTO branch_options (id, branch_id, label, path_id, position) "
        "VALUES (?, ?, ?, ?, ?)",
        ("opt-cad-campos", branch_cad, "Quero aprender sobre os campos da ficha", path_cad_campos, 0),
    )
    db.execute(
        "INSERT OR IGNORE INTO branch_options (id, branch_id, label, path_id, position) "
        "VALUES (?, ?, ?, ?, ?)",
        ("opt-cad-subabas", branch_cad, "Quero aprender sobre as sub-abas", path_cad_subabas, 1),
    )

    # =========================================================================
    # MÓDULO 3: Agenda (4 steps, linear)
    # =========================================================================
    mod3_id = "mod-agenda"
    path3_main = "path-agenda-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod3_id, "Agenda", "Programe reuniões e eventos — compartilhe com a equipe", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path3_main, mod3_id, "Principal", True),
    )

    steps_mod3 = [
        ("step-agenda-1", "text", "# Módulo: Agenda\n\nNa Agenda você programa reuniões e eventos. Foi criada para equipes, facilitando compartilhamento.\n\n**Funcionalidades:**\n- 📅 Assinar agenda DOit para outros apps (Google Calendar, etc)\n- 🖨️ Relatório em PDF\n- ➕ Criar eventos\n- Visualização: Mês, Semana ou Dia"),
        ("step-agenda-2", "text", "# Minha Agenda\n\n**Caminho:** Agenda → Minha Agenda\n\nSeus compromissos pessoais. Você pode:\n- Alterar visualização (mês/semana/dia)\n- Compartilhar com outros usuários (eles poderão ver e criar compromissos)\n- Trocar a cor da agenda\n\n💡 **Para compartilhar:** Suas Iniciais → Pref. Pessoais → Agenda → Compartilhar. Pesquise e selecione os usuários (só precisa fazer uma vez)."),
        ("step-agenda-3", "text", "# Agendas Públicas\n\n**Caminho:** Agenda → Públicas\n\nVisualize agendas compartilhadas como:\n- Disponibilidade da sala de reuniões\n- Agenda de outro colaborador\n\n**Para ativar/desativar:** Clique no botão 'Agendas' (canto superior esquerdo) e marque como 'Ativa' as que quiser ver.\n\n**Para criar/editar agendas públicas:** Agenda → Setup → Públicas"),
        ("step-agenda-4", "text", "# Recados e Setup\n\n### Recados\n**Caminho:** Agenda → Recados\n\nHistórico de recados enviados e recebidos. Comunicação rápida unidirecional (sem resposta).\n\n### Aba Lista\n**Caminho:** Agenda → Lista\n\nMesmos eventos em formato listagem, com filtros avançados e exportação Excel.\n\n✅ Módulo Agenda concluído!"),
    ]

    for i, (step_id, ctype, content) in enumerate(steps_mod3):
        db.execute(
            "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, mod3_id, path3_main, i, "content"),
        )
        db.execute(
            "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"c-{step_id}", step_id, ctype, content, 0),
        )

    # =========================================================================
    # MÓDULO 4: Projetos (5 steps main, branching at step 3)
    # =========================================================================
    mod4_id = "mod-projetos"
    path4_main = "path-projetos-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod4_id, "Projetos", "Gestão completa de projetos — horas, despesas, equipe e tarefas", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path4_main, mod4_id, "Principal", True),
    )

    # Step 1
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-proj-1", mod4_id, path4_main, 0, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-proj-1", "step-proj-1", "text", "# Módulo: Projetos\n\nOnde moram os projetos com todas as informações do escritório. Aqui você pode:\n\n- 🏗️ Apontar horas\n- 💰 Vincular despesas a projetos\n- 📊 Visualizar custos\n- 📦 Criar pedidos\n\n**Três visões disponíveis:**\n- **Meus Projetos** — Projetos onde você está na equipe interna\n- **Líder** — Projetos onde você é líder\n- **Todos** — Visão completa (Diretoria/Financeiro)", 0),
    )

    # Step 2
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-proj-2", mod4_id, path4_main, 1, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-proj-2", "step-proj-2", "text", "# Sub-abas Comuns\n\nTodas as visões (Meus Projetos, Líder, Todos) compartilham:\n\n- **Geral** — Listagem com busca avançada, relatórios PDF/Excel\n- **Horas** — Horas lançadas (suas ou de todos, conforme a aba)\n- **Despesas** — Despesas vinculadas ao projeto\n- **Ficha** — Visão detalhada do projeto (abre ao clicar no ID)\n- **Atas de Reunião** — Atas criadas nos projetos\n- **E-mails** — E-mails vinculados aos projetos\n\n⚠️ Certifique-se de estar na aba correta para a visualização desejada!", 0),
    )

    # Step 3 (BRANCH step)
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-proj-3", mod4_id, path4_main, 2, "branch"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-proj-3", "step-proj-3", "text", "# Ficha do Projeto\n\nA ficha abre ao clicar no ID de um projeto. Campos principais:\n\n- **Nome, Status, Categoria** (Arquitetura, Interiores, etc)\n- **Datas:** Início, Execução, Término\n- **Cliente:** Busque no Cadastro com a lupa\n- **Endereço do Projeto e de Cobrança**\n- **Reuniões/Atividades/Visitas** (em horas contratadas)\n\n👇 O que deseja aprender agora?", 0),
    )

    # Branch for Projetos
    branch_proj = "branch-proj-ficha"
    db.execute(
        "INSERT OR IGNORE INTO branches (id, step_id) VALUES (?, ?)",
        (branch_proj, "step-proj-3"),
    )

    # Path A: Horas e Despesas
    path_proj_horas = "path-proj-horas"
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, parent_branch_id, name, is_main) "
        "VALUES (?, ?, ?, ?, ?)",
        (path_proj_horas, mod4_id, branch_proj, "Horas e Despesas", False),
    )

    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-proj-horas-1", mod4_id, path_proj_horas, 0, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-proj-horas-1", "step-proj-horas-1", "text", "# Lançar Horas\n\n**Caminho:** Projeto → Horas → ícone ➕\n\nPreencha:\n- **Atividade:** Descrição breve\n- **Projeto:** Selecione o projeto (ou o do escritório para processos internos)\n- **Etapas:** Escolha conforme configurado\n- **Hs:** Horas (ou use Data Início/Fim)\n- **Data Início e Data Fim:** O sistema calcula automaticamente\n\n💡 Você também pode lançar horas pela Dashboard (Start/Stop) ou pelo módulo Tarefas.", 0),
    )

    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-proj-horas-2", mod4_id, path_proj_horas, 1, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-proj-horas-2", "step-proj-horas-2", "text", "# Lançar Despesas\n\n**Caminho:** Projeto → Despesas → ícone ➕\n\nPreencha:\n- **Data:** Quando ocorreu\n- **Profissional:** Quem realizou\n- **Projeto:** Vincule ao projeto\n- **De/Para:** Quem pagou\n- **Tipo de Despesa:** Cartão, Dinheiro, etc\n- **Total:** Valor\n- **Arquivo:** Comprovante (opcional)\n- ☐ Marque se o escritório deve reembolsar\n\n**Status de cobrança (colunas P e C):**\n- 🔘 Não classificado → ❌ Não cobrar → 🟢 Cobrar\n\n✅ Horas e despesas concluído!", 0),
    )

    # Path B: Equipe Interna e Tarefas
    path_proj_equipe = "path-proj-equipe"
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, parent_branch_id, name, is_main) "
        "VALUES (?, ?, ?, ?, ?)",
        (path_proj_equipe, mod4_id, branch_proj, "Equipe Interna e Tarefas", False),
    )

    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-proj-equipe-1", mod4_id, path_proj_equipe, 0, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-proj-equipe-1", "step-proj-equipe-1", "text", "# Equipe Interna\n\n**Caminho:** Projeto → Ficha → Equipe Interna\n\nTodos os participantes do projeto. Sem estar na equipe, não acessa pela aba 'Meus Projetos'.\n\n**Ações:**\n- ➕ Adicionar membros (qualquer membro da equipe pode)\n- Alterar função de cada membro\n- ☑️ Apontar Líder (acessa Etapas e Tarefas)\n- ✉️ Enviar e-mail para equipe ativa\n- 👥 Adicionar equipe padrão (Setup → Equipe)\n\n💡 **$ Venda:** Preencha o valor/hora de cada profissional para cobranças de HT.", 0),
    )

    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, ?)",
        ("step-proj-equipe-2", mod4_id, path_proj_equipe, 1, "content"),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        ("c-proj-equipe-2", "step-proj-equipe-2", "text", "# Etapas e Tarefas\n\n### Etapas (Ficha → Etapas)\nVisão prévia das tarefas que serão geradas. Clique ✅ para gerar.\n\n### Tarefas (Ficha → Tarefas)\nOnde as tarefas são delegadas. Aparece na Dashboard do responsável.\n\n**Dica: Delegar em massa:**\n1. Filtre por Etapa\n2. No filtro Responsável, use '=' (mostra só sem responsável)\n3. Selecione um responsável → 'Atualizar todos?'\n4. Clique ✅ para enviar\n\n⚠️ Erro 'responsável obrigatório'? Use filtro '*' no Responsável.\n\n✅ Equipe e tarefas concluído!", 0),
    )

    # Branch options for Projetos
    db.execute(
        "INSERT OR IGNORE INTO branch_options (id, branch_id, label, path_id, position) "
        "VALUES (?, ?, ?, ?, ?)",
        ("opt-proj-horas", branch_proj, "Como lançar horas e despesas", path_proj_horas, 0),
    )
    db.execute(
        "INSERT OR IGNORE INTO branch_options (id, branch_id, label, path_id, position) "
        "VALUES (?, ?, ?, ?, ?)",
        ("opt-proj-equipe", branch_proj, "Como usar Equipe Interna e Tarefas", path_proj_equipe, 1),
    )

    # =========================================================================
    # MÓDULO 5: Tarefas (3 steps, linear)
    # =========================================================================
    mod5_id = "mod-tarefas"
    path5_main = "path-tarefas-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod5_id, "Tarefas", "Gerenciamento completo de tarefas — calendário, lista e andamento", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path5_main, mod5_id, "Principal", True),
    )

    steps_mod5 = [
        ("step-tarefas-1", "text", "# Módulo: Tarefas\n\nGerenciamento completo de tarefas do escritório.\n\n**Visualizações:**\n- 📅 **Calendário** — Por Responsável ou por Projeto (eixo vertical)\n- 📋 **Lista** — Formato listagem com filtros avançados\n- 📝 **Ficha** — Detalhes da tarefa\n- ⏱️ **Andamento** — Tarefas com cronômetro ativo\n\n**Ações rápidas:**\n- 📋 Duplicar\n- ✏️ Editar\n- ✅ Concluir\n- 🗑️ Apagar"),
        ("step-tarefas-2", "text", "# Criar e Concluir Tarefas\n\n### Criar Tarefa\nClique ➕ no Calendário ou Lista. Preencha:\n- Nome, Prioridade, Responsável\n- Data início, fim e prazo\n- Relacionamentos: vincule a cadastro ou projeto + etapa\n\n### Concluir Tarefa (4 formas)\n1. Dashboard → ícone ☐\n2. Calendário → clique na barra → ✅\n3. Lista → ícone ☐\n4. Ficha → ícone ✅\n\n💡 Só o responsável pode concluir a tarefa."),
        ("step-tarefas-3", "text", "# Horas e Participantes\n\n### Sub-aba: Horas\nResumo de horas lançadas na tarefa. Clique ➕ para lançar horas.\n\n### Sub-aba: Participantes\nAdicione outros usuários para lançar horas na mesma tarefa.\n\n⚠️ Mesmo com participantes, apenas o **responsável** pode concluir a tarefa.\n\n### Aba: Andamento\nVeja em tempo real quais tarefas estão com cronômetro ativo (Start/Stop).\n\n✅ Módulo Tarefas concluído!"),
    ]

    for i, (step_id, ctype, content) in enumerate(steps_mod5):
        db.execute(
            "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, mod5_id, path5_main, i, "content"),
        )
        db.execute(
            "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"c-{step_id}", step_id, ctype, content, 0),
        )

    # =========================================================================
    # MÓDULO 6: E-mail (3 steps, linear)
    # =========================================================================
    mod6_id = "mod-email"
    path6_main = "path-email-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod6_id, "E-mail", "Atalho para envio de e-mails — modelos, setup e histórico", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path6_main, mod6_id, "Principal", True),
    )

    steps_mod6 = [
        ("step-email-1", "text", "# Módulo: E-mail\n\n⚠️ **Importante:** O DOit é um **atalho para envio** de e-mails. Ele **não recebe** e-mails. Não substitui seu provedor (Gmail, Outlook, etc).\n\n**Abas disponíveis:**\n- **Meus E-mails** — Enviados por você via DOit\n- **Todos E-mails** — Enviados por todos os usuários\n- **Ficha** — Detalhes de um e-mail específico\n- **Modelos** — Templates reutilizáveis\n- **Setup** — Configuração de contas"),
        ("step-email-2", "text", "# Modelos de E-mail\n\nTemplates prontos para agilizar envios recorrentes.\n\n**Exemplos:** Propostas, contratos, felicitações, cobranças.\n\n**Criar modelo:**\n1. E-mail → Modelos → Meus Modelos → ➕\n2. Edite nome, assunto e corpo\n3. Marque como Público ☑️ se quiser compartilhar\n4. Tranque 🔒 para impedir edições de outros\n\n**Usar modelo:**\nClique no ícone ✉️ ao lado do modelo → rascunho gerado automaticamente."),
        ("step-email-3", "text", "# Setup de E-mail\n\n**Caminho:** E-mail → Setup\n\nAqui ficam todos os e-mails cadastrados no sistema para envio. Cada provedor tem configurações técnicas específicas (SMTP, porta, etc).\n\n💡 **Precisa de ajuda?** Clique na **Dona Lourdes** (ícone de suporte) para contatar nossa equipe.\n\n✅ Módulo E-mail concluído!"),
    ]

    for i, (step_id, ctype, content) in enumerate(steps_mod6):
        db.execute(
            "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, mod6_id, path6_main, i, "content"),
        )
        db.execute(
            "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"c-{step_id}", step_id, ctype, content, 0),
        )

    # =========================================================================
    # MÓDULO 7: Documentos e Listas (3 steps, linear)
    # =========================================================================
    mod7_id = "mod-documentos"
    path7_main = "path-documentos-main"

    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, ?, ?)",
        (mod7_id, "Documentos e Listas", "Arquivos centralizados e listas de envio de e-mail", "published", 1),
    )
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path7_main, mod7_id, "Principal", True),
    )

    steps_mod7 = [
        ("step-docs-1", "text", "# Módulo: Documentos\n\nReúne **todos os arquivos** do DOit em um só lugar.\n\n**Filtros disponíveis:** ID Relacionado, Tipo, Nome, Descrição, Versão, Data, Criado Por\n\n**Abas:**\n- **Todos** — Todos os documentos\n- **Cadastros** — Documentos de fichas de cadastro\n- **Projetos** — Documentos de projetos\n- **Atas de Reunião** — Anexos de atas"),
        ("step-docs-2", "text", "# Módulo: Listas\n\nCriação e manutenção de **listas de envio de e-mail**.\n\n**Criar lista:** Listas → Minhas Listas → ➕\n\n**Adicionar cadastros à lista:**\n1. Vá em Cadastro → Lista 2\n2. Aplique filtros desejados\n3. Clique no ícone ✉️\n4. Busque a lista criada\n5. Pronto! Cadastros adicionados.\n\n**Público vs Privado:** Marque ☑️ para compartilhar com outros usuários."),
        ("step-docs-3", "text", "# Resumo Final\n\nVocê completou o treinamento básico do DOit! 🎉\n\n**Módulos aprendidos:**\n1. ✅ Dashboard — Sua visão geral\n2. ✅ Cadastros — Coração do sistema\n3. ✅ Agenda — Eventos e reuniões\n4. ✅ Projetos — Gestão completa\n5. ✅ Tarefas — Produtividade\n6. ✅ E-mail — Comunicação\n7. ✅ Documentos e Listas\n\n💡 Para dúvidas, clique na **Dona Lourdes** no canto inferior direito do DOit.\n\n✅ Treinamento concluído!"),
    ]

    for i, (step_id, ctype, content) in enumerate(steps_mod7):
        db.execute(
            "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (step_id, mod7_id, path7_main, i, "content"),
        )
        db.execute(
            "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"c-{step_id}", step_id, ctype, content, 0),
        )

    # =========================================================================
    # COMMIT & SUMMARY
    # =========================================================================
    db.commit()
    db.close()

    print("\n✅ Dados reais do manual DOit inseridos com sucesso!\n")
    print("=" * 55)
    print("  RESUMO DO SEED")
    print("=" * 55)
    print(f"  👤 Usuário admin: admin@doit.com")
    print(f"  📦 Módulos criados: 7 (todos published)")
    print(f"     1. Dashboard (3 steps)")
    print(f"     2. Cadastros (3 main + branch → 2+2 steps)")
    print(f"     3. Agenda (4 steps)")
    print(f"     4. Projetos (3 main + branch → 2+2 steps)")
    print(f"     5. Tarefas (3 steps)")
    print(f"     6. E-mail (3 steps)")
    print(f"     7. Documentos e Listas (3 steps)")
    print(f"  🔀 Ramificações: 2")
    print(f"     - Cadastros: Campos da Ficha / Sub-abas")
    print(f"     - Projetos: Horas e Despesas / Equipe e Tarefas")
    print(f"  📝 Total de steps: 27")
    print("=" * 55)


if __name__ == "__main__":
    seed()
