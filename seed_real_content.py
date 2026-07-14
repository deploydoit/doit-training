"""Popula o banco com conteúdo real baseado no Manual do Usuário DOit."""
import sys
sys.path.insert(0, '.')
from models.database import Database


def seed():
    db = Database("training.db")
    db.initialize()

    # Limpar tudo antes
    db.execute("DELETE FROM modules")
    db.commit()

    _create_module_dashboard(db)
    _create_module_agenda(db)
    _create_module_cadastro(db)
    _create_module_projeto(db)
    _create_module_tarefas(db)

    # Admin user
    db.execute(
        "INSERT OR IGNORE INTO users (id, name, email, is_first_visit, is_admin) "
        "VALUES (?, ?, ?, ?, ?)",
        ("admin-1", "Administrador", "admin@doit.com", False, True),
    )
    db.commit()
    db.close()
    print("✅ Conteúdo real do DOit criado!")
    print("   - 5 módulos baseados no Manual do Usuário")


def _add_module(db, mod_id, title, desc):
    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, 'published', 1)",
        (mod_id, title, desc),
    )
    path_id = f"{mod_id}_main"
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, ?, ?)",
        (path_id, mod_id, "Principal", True),
    )
    return path_id


def _add_step(db, mod_id, path_id, pos, content):
    step_id = f"{mod_id}_step_{pos}"
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, 'content')",
        (step_id, mod_id, path_id, pos),
    )
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, 'text', ?, 0)",
        (f"c_{step_id}", step_id, content),
    )


def _create_module_dashboard(db):
    path = _add_module(db, "mod-dashboard", "Dashboard",
        "Entenda sua tela inicial: agenda, tarefas, recados e documentos")

    _add_step(db, "mod-dashboard", path, 0, """# Dashboard — Sua Tela Inicial

A Dashboard é um **resumo do que está acontecendo** no seu sistema. A visualização dos itens pode variar de acordo com o seu nível de acesso.

Aqui você encontra:
- 📅 **Agenda** — Eventos do dia e do dia seguinte
- 📌 **Datas Importantes** — Aniversários, contratações
- 💬 **Recados** — Comunicação rápida entre usuários
- ✅ **Tarefas** — Suas tarefas pendentes com Start/Stop
- 📄 **Documentos a Expirar** — Alertas de vencimento
""")

    _add_step(db, "mod-dashboard", path, 1, """# Campo: Agenda

Um resumo dos eventos que estão na sua agenda e nas agendas públicas que você ativou.

**Por padrão:** mostra o dia atual e o dia seguinte (máximo 5 dias).

**Para alterar a quantidade de dias:**
1. Clique nas suas iniciais (canto superior direito)
2. Vá em **Pref. Pessoais**
3. Acesse **Agenda**
4. Altere o campo "Dias dashboard"
""")

    _add_step(db, "mod-dashboard", path, 2, """# Campo: Tarefas

Quando uma tarefa é delegada a você, ela aparece na Dashboard.

**Ordenação:** Primeiro por prioridade, depois por prazo.
**Limite:** Máximo 10 tarefas simultâneas.

**Como usar:**
- ▶️ **Start** — Começa a contabilizar tempo na tarefa
- ⏹️ **Stop** — Para a contagem (pode ajustar horários manualmente)
- ☑️ **Concluir** — Finaliza a tarefa com todas as horas registradas

💡 **Dica:** Se esqueceu de parar o Start, ao clicar Stop você pode corrigir o horário antes de salvar.
""")

    _add_step(db, "mod-dashboard", path, 3, """# Campo: Recados

A ferramenta de recados serve como **comunicação rápida** entre usuários — não é esperada uma resposta.

**Como funciona:**
- Ao enviar um recado, o destinatário recebe uma **notificação** no ícone ao lado das suas iniciais
- O destinatário **não pode responder** (não é chat!)
- Use para avisos rápidos: "Verificar cadastro ID 123", "Checar ata de reunião"

⚠️ **Importante:** Recados não substituem WhatsApp ou Slack. São para comunicação unidirecional e rápida dentro do DOit.
""")

    _add_step(db, "mod-dashboard", path, 4, """# Campo: Documentos a Expirar

Mostra documentos com **data de vencimento** definida.

**Regra padrão:**
- Aparecem **20 dias antes** do vencimento
- Ficam visíveis até **10 dias após** o vencimento
- Esses prazos podem ser customizados

**Exemplos de uso:**
- RG prestes a vencer
- Contrato com data de expiração
- Certificado Digital próximo do vencimento

✅ Você completou o módulo Dashboard!
""")
    db.commit()


def _create_module_agenda(db):
    path = _add_module(db, "mod-agenda", "Agenda",
        "Programe reuniões, eventos e compartilhe sua agenda com a equipe")

    _add_step(db, "mod-agenda", path, 0, """# Módulo: Agenda

Na Agenda você pode **programar reuniões e eventos**. Foi criada para equipes, facilitando o compartilhamento.

**Ações disponíveis:**
- 📅 Assinar agenda DOit para visualizar em outros apps (Google Calendar, Outlook)
- 🖨️ Gerar relatório em PDF
- ➕ Criar um evento

**Visualizações:** Mês | Semana | Dia
""")

    _add_step(db, "mod-agenda", path, 1, """# Minha Agenda

**Em:** Agenda → Minha Agenda

É onde ficam **somente seus compromissos**. Você pode:
- Visualizar por mês, semana ou dia
- Criar eventos clicando no horário desejado
- Trocar a cor da sua agenda nas Preferências Pessoais

⚠️ Se compartilhar sua agenda com outros, eles poderão visualizar **e criar** compromissos em seu nome.
""")

    _add_step(db, "mod-agenda", path, 2, """# Agendas Públicas

**Em:** Agenda → Públicas

Aqui você escolhe quais agendas compartilhadas quer visualizar:
- Sala de reuniões
- Agenda de outro colaborador
- Eventos do escritório

**Como ativar:**
1. Clique no botão "Agendas" (canto superior esquerdo)
2. Marque como "Ativa" ✅ as agendas que deseja ver

**Para criar/editar agendas públicas:**
Vá em Agenda → Setup → Públicas (depende do nível de acesso)
""")

    _add_step(db, "mod-agenda", path, 3, """# Compartilhar sua Agenda

**Em:** Suas iniciais → Pref. Pessoais → Agenda → Compartilhar

**Passo a passo:**
1. Clique nas suas iniciais (canto superior direito)
2. Clique em **Pref. Pessoais**
3. Vá na seção **Agenda**
4. Clique no ícone de compartilhamento
5. Pesquise e selecione os colaboradores

💡 **Dica:** Esse processo só precisa ser feito **uma única vez**. Nesta mesma tela você pode mudar a cor da sua agenda e a quantidade de dias na Dashboard.

✅ Módulo Agenda concluído!
""")
    db.commit()


def _create_module_cadastro(db):
    path = _add_module(db, "mod-cadastro", "Cadastros",
        "Gerencie clientes, fornecedores e contatos no coração do DOit")

    _add_step(db, "mod-cadastro", path, 0, """# Módulo: Cadastro

O módulo Cadastro é o **coração do DOit** — aqui ficam todas as informações de:
- 👤 Clientes
- 🏢 Fornecedores
- 👥 Colaboradores
- 🏗️ Prestadores de serviço

**Ações rápidas:**
- ➕ Criar um cadastro
- 🔍 Busca Avançada (Bairro, CEP, Cidade, Contatos, Documento, País, UF)
- 🖨️ Relatórios em PDF
- 📊 Relatórios em Excel
- ✉️ Criação de Listas de E-mail
""")

    _add_step(db, "mod-cadastro", path, 1, """# Listas de Cadastros

O DOit tem **duas listas** para buscar cadastros:

**Lista 1** — Filtros básicos:
- ID (número do cadastro)
- Nome
- Apelido
- E-mail
- Telefone

**Lista 2** — Todos os filtros da Lista 1 + extras:
- Origem
- Classificação
- Anotações
- UF (Estado)

💡 **Dica:** Use a Lista 2 quando precisar de filtros mais detalhados.
""")

    _add_step(db, "mod-cadastro", path, 2, """# Ficha do Cadastro

**Em:** Cadastro → clique no ID de qualquer cadastro

A ficha contém todos os dados do cadastro organizado em campos:

**Campos principais:**
- **Origem** — Como conheceu seus serviços (ex: "Nos viu no Instagram 2023")
- **Classificação** — Categorize: Fornecedor, Piso, Laminado... (personalizável)
- **Info Cadastrais** — Nome, Apelido, Website
- **E-mails** — Múltiplos, com marcação de principal
- **Telefones** — Múltiplos, com marcação de principal
- **Documentos** — CPF/CNPJ (validado automaticamente), Instagram, IE
- **Datas** — Fundação, Aniversário, etc.
- **Anotações** — Campo livre

**Sub-abas (parte inferior):**
Contatos | Endereços | Documentos | Compromissos | Tarefas | E-mail | Projetos
""")

    _add_step(db, "mod-cadastro", path, 3, """# Dicas Importantes de Cadastro

**Tornar um cadastro privado:**
1. Na Ficha, clique no ícone de cadeado 🔓
2. Selecione os usuários que terão acesso
3. Clique em "Salvar"
4. Para reverter: clique no cadeado → "Tornar Público"

**Classificações personalizadas:**
- Vá em Cadastro → Setup → Classificações
- Clique ➕ para criar novas (ex: "Fornecedor de Piso", "Cliente VIP")

**Documentos personalizados:**
- Vá em Cadastro → Setup → Documentos
- Defina quais aparecem por padrão em toda ficha
- Coluna **Federal** = documento federal (CPF/CNPJ)
- Coluna **Estadual** = documento estadual (RG/IE)

✅ Módulo Cadastros concluído!
""")
    db.commit()


def _create_module_projeto(db):
    path = _add_module(db, "mod-projeto", "Projetos",
        "Crie projetos, gerencie equipes, lance horas e despesas")

    _add_step(db, "mod-projeto", path, 0, """# Módulo: Projeto

O módulo de Projeto é onde moram seus projetos com **todas as informações**:
- Apontar horas
- Despesas vinculadas
- Custo do projeto
- Pedidos e cobranças

**Abas por nível de acesso:**
- **Meus Projetos** — Projetos onde você está na equipe interna
- **Líder** — Projetos onde você é o líder designado
- **Todos** — Visão completa (geralmente Diretoria/Financeiro)

Cada aba possui as sub-abas: Geral, Horas, Despesas, Ficha, Atas de Reunião e E-mails.
""")

    _add_step(db, "mod-projeto", path, 1, """# Ficha do Projeto

**Em:** Projeto → clique no ID de qualquer projeto

**Campos essenciais:**
- **Nome** — Nome do projeto (usado nos filtros)
- **Status** — Atualize conforme o projeto avança
- **Categoria** — Tipo de serviço (Arquitetura, Interiores, etc.)
- **Início / Execução / Término** — Datas-chave
- **Cliente** — Busque no Cadastro com a lupa 🔍
- **Endereço do Projeto** — Preenchido automaticamente se cliente tem 1 endereço
- **Endereço de Cobrança** — Idem

**Detalhes do Projeto (customizável):**
- Terreno (m²), Área Construída (m²)
- Distância (KM), Taxa de Administração (%)
- Custo Visita

**Controles de horas:**
- Reuniões (em horas) — Subtraído ao criar atas de reunião
- Atividades (em horas) — Subtraído ao lançar horas
- Visitas — Subtraído ao apontar visita em ata
""")

    _add_step(db, "mod-projeto", path, 2, """# Lançar Horas em Projetos

**Em:** Projeto → Horas → clique ➕

**Campos do formulário:**
- **Atividade** — Descrição breve (ex: "Revisão de planta")
- **Descrição** — Texto livre com mais detalhes
- **Projeto** — Selecione o projeto (ou o nome do escritório para processos internos)
- **Etapas** — Selecione conforme configurado no projeto
- **Hs** — Horas utilizadas (opcional se usar Data Início/Fim)
- **Data Início / Data Fim** — O sistema calcula as horas automaticamente

💡 **Dica:** Pela Aba "Meus Projetos" você vê apenas SUAS horas. Pela "Líder" ou "Todos" vê as de toda a equipe.
""")

    _add_step(db, "mod-projeto", path, 3, """# Equipe Interna e Tarefas

**Equipe Interna** (Projeto → Ficha → Equipe Interna):
- Adicione membros com ➕ e pesquise o usuário
- Defina a **função** de cada um no projeto
- Marque o **Líder** com ✅ (ganha acesso a Etapas e Tarefas)
- ✉️ Envie e-mail para toda equipe ativa

**Delegando Tarefas em Massa:**
1. Vá em Projeto → Ficha → Etapas → Gere tarefas com ✅
2. Em Projeto → Ficha → Tarefas:
   - Filtre por "Etapa"
   - No filtro "Responsável" use "=" (mostra só as sem responsável)
   - Atribua um responsável → "Deseja atualizar todos?" → Sim
   - Clique ✅ para enviar às Dashboards

✅ Módulo Projetos concluído!
""")
    db.commit()


def _create_module_tarefas(db):
    path = _add_module(db, "mod-tarefas", "Tarefas",
        "Crie, delegue, controle horas e conclua tarefas do seu dia a dia")

    _add_step(db, "mod-tarefas", path, 0, """# Módulo: Tarefas

Este módulo gerencia todas as tarefas do sistema. Se uma tarefa é designada a você, ela aparece na sua **Dashboard**.

**Visualizações:**
- 📅 **Calendário** — Por Responsável ou por Projeto (eixo vertical) x Tempo (eixo horizontal)
- 📋 **Lista** — Formato listagem com filtros avançados
- 📄 **Ficha** — Detalhes completos de uma tarefa
- ⏱️ **Andamento** — Tarefas com Start/Stop ativo em tempo real

**Ações rápidas em qualquer tarefa:**
- 📋 Duplicar
- ✏️ Editar
- ✅ Concluir
- 🗑️ Apagar
""")

    _add_step(db, "mod-tarefas", path, 1, """# Criar uma Tarefa

**Em:** Tarefas → Calendário ou Lista → clique ➕

**Campos disponíveis na Ficha da tarefa:**
- **Nome da tarefa** — Descrição clara do que precisa ser feito
- **Prioridade** — Define a ordem na Dashboard
- **Responsável** — Quem vai executar
- **Data Início / Data Fim** — Período de execução
- **Prazo** — Data limite para conclusão

**Relacionamentos:**
- Vincule a um **Cadastro** (cliente/fornecedor)
- Vincule a um **Projeto**
- Defina a **Etapa** do projeto

💡 Ao vincular a um projeto, as horas lançadas nessa tarefa contam para o projeto automaticamente.
""")

    _add_step(db, "mod-tarefas", path, 2, """# Concluir uma Tarefa

Existem **4 formas** de concluir uma tarefa:

1. **Dashboard** → Campo Tarefas → clique ☑️
2. **Calendário** → Clique na barra colorida → ícone ✅
3. **Lista** → Clique no ícone ☑️ da linha
4. **Ficha** → Clique no ícone ✅

⚠️ **Importante:** Apenas o **responsável** pela tarefa pode marcá-la como concluída!

**Sub-abas da Ficha:**
- **Horas** — Resumo de horas lançadas na tarefa (clique ➕ para lançar mais)
- **Participantes** — Outros usuários que podem lançar horas na mesma tarefa

✅ Módulo Tarefas concluído!
""")
    db.commit()


if __name__ == "__main__":
    seed()
