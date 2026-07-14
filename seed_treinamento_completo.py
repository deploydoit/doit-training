"""Popula o banco com conteúdo completo baseado no treinamento Dias 1-2 + Manual."""
import sys
sys.path.insert(0, '.')
from models.database import Database


def seed():
    db = Database("training.db")
    db.initialize()

    # Limpar tudo
    db.execute("DELETE FROM modules")
    db.commit()

    _mod_acesso(db)
    _mod_dashboard(db)
    _mod_agenda(db)
    _mod_cadastro(db)
    _mod_projetos(db)
    _mod_tarefas(db)
    _mod_atas(db)

    # Admin
    db.execute(
        "INSERT OR IGNORE INTO users (id, name, email, is_first_visit, is_admin) "
        "VALUES (?, ?, ?, ?, ?)",
        ("admin-1", "Administrador", "admin@doit.com", False, True),
    )
    db.commit()
    db.close()
    print("✅ Treinamento completo criado — 7 módulos!")


def _m(db, mid, title, desc):
    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, 'published', 1)", (mid, title, desc))
    pid = f"{mid}_main"
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) "
        "VALUES (?, ?, 'Principal', ?)", (pid, mid, True))
    return pid


def _s(db, mid, pid, pos, txt):
    sid = f"{mid}_s{pos}"
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, 'content')", (sid, mid, pid, pos))
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, 'text', ?, 0)", (f"c_{sid}", sid, txt))


def _mod_acesso(db):
    p = _m(db, "acesso", "Acesso ao Sistema", "Como acessar o DOit, login e primeiros passos")
    _s(db, "acesso", p, 0, """# Acesso ao Sistema DOit

O DOit é uma plataforma **100% online**. Você não precisa instalar nada.

**Como acessar:**
1. Abra seu navegador (Chrome, Firefox, Safari)
2. Digite o endereço do sistema fornecido pela empresa
3. Informe seu **usuário** e **senha**
4. Clique em Entrar

**Vantagens:**
- Acesse de qualquer lugar com internet
- Funciona em computador, tablet ou celular
- Não ocupa espaço no seu computador
- Atualizações são automáticas

💡 **Dica:** Salve o endereço nos favoritos do navegador para acesso rápido.
""")
    db.commit()


def _mod_dashboard(db):
    p = _m(db, "dashboard", "Dashboard", "Seu painel gerencial com resumo de tudo que acontece no escritório")
    _s(db, "dashboard", p, 0, """# Dashboard — Seu Painel Gerencial

Ao fazer login, você cai na **Dashboard** — um resumo de tudo que está acontecendo no escritório.

À medida que o sistema é alimentado, os indicadores são **atualizados automaticamente**.

**O que você encontra aqui:**
- 🔔 Notificações (prazos, aprovações, alterações)
- 📅 Agenda (compromissos futuros)
- 📌 Datas Importantes (aniversários, contratações)
- 💬 Recados (lembretes entre usuários)
- ✅ Tarefas (pendências com Start/Stop)
- 💰 Financeiro (contas a vencer/vencidas)
- 📊 Faturamento (gráficos de NFs emitidas)
- 📄 Documentos a Expirar (alertas de vencimento)
""")

    _s(db, "dashboard", p, 1, """# Notificações

As notificações exibem alertas dos seus projetos:

- ⏰ Prazos de etapas próximos do vencimento
- 👤 Alteração de líderes de projetos
- ✅ Aprovação de orçamentos
- ⚠️ Extrapolação de horas previstas
- 📋 Demais ocorrências dos projetos

A visualização depende das suas **permissões** e dos projetos aos quais você está vinculado.
""")

    _s(db, "dashboard", p, 2, """# Tarefas na Dashboard

Mostra todas as tarefas **pendentes atribuídas a você**.

**Ordenação:** Primeiro por prioridade, depois por prazo.
**Limite:** Máximo 10 tarefas simultâneas.

**Como usar o Start/Stop:**
- ▶️ **Start** — Começa a contabilizar tempo dedicado à tarefa
- ⏹️ **Stop** — Para a contagem. Aparece uma caixa para:
  - Ajustar data/hora de início e fim manualmente
  - Adicionar descrição do que foi feito
- ☑️ **Concluir** — Finaliza a tarefa com todas as horas registradas

💡 Se esqueceu de parar o Start, ao clicar Stop você pode **corrigir o horário**.

As tarefas também são um dos métodos de **lançamento de horas** no sistema.
""")

    _s(db, "dashboard", p, 3, """# Recados, Financeiro e Documentos

**Recados** 💬
- Lembretes internos entre usuários (NÃO é chat)
- O destinatário não responde — é comunicação unidirecional
- Exemplos: "Retornar para fornecedor X", "Verificar cadastro 123"

**Financeiro** 💰 (requer acesso ao módulo)
- Contas vencidas
- Contas a vencer
- Pendências financeiras

**Faturamento** 📊 (requer acesso ao módulo)
- Gráficos com base nas NFs emitidas
- Evolução financeira do mês

**Documentos a Expirar** 📄
- Documentos com data de vencimento próxima
- Aparecem **20 dias antes** do vencimento
- Ficam visíveis até **10 dias após**
- Podem estar vinculados a: Cadastros, Projetos ou Reuniões
""")
    db.commit()


def _mod_agenda(db):
    p = _m(db, "agenda", "Agenda e Eventos", "Gerencie compromissos, crie eventos e integre com Google Agenda")
    _s(db, "agenda", p, 0, """# Módulo: Agenda

Gerencie compromissos e eventos do escritório.

**Duas áreas principais:**

📅 **Minha Agenda** — Seus compromissos pessoais:
- Reuniões, visitas de obra, treinamentos

📅 **Agendas Públicas** — Compartilhadas com toda equipe:
- Sala de reunião, Férias, Visitas de obra

**Visualizações:** Mensal | Semanal | Diária
Use o botão **"Hoje"** para voltar ao dia atual rapidamente.

**Integração Google Agenda:**
- Eventos do DOit aparecem no Google Agenda
- Eventos do Google Agenda aparecem no DOit
""")

    _s(db, "agenda", p, 1, """# Criar um Evento

Clique no ícone ➕ na Agenda para criar.

**Campos do evento:**
- **Nome** — Ex: "Treinamento DOit", "Reunião de Equipe", "Visita de Obra"
- **Local** — Vinculado a um cadastro (endereço buscado automaticamente)
- **Projeto** — Relacione a um projeto específico (para atividades internas, use o projeto administrativo)
- **Etapa** — Vincule a uma etapa: Administrativo, Treinamento, Proposta, Arquitetura
- **Data/Hora** — Início, término, opção de dia inteiro
- **Repetição** — Reuniões semanais, alinhamentos recorrentes
- **Descrição** — Pautas, links, observações
- **Agenda** — Pessoal ou pública
- **Contatos** — Clientes, fornecedores, parceiros participantes

**Controle de Horas:** Eventos vinculados a projetos contabilizam horas automaticamente!
""")

    _s(db, "agenda", p, 2, """# Salvar, Enviar e Compartilhar

**Ao finalizar o evento, duas opções:**
- **Salvar** — Cria apenas dentro do DOit
- **Salvar e Enviar Convites** — Envia e-mail para os contatos vinculados

**Compartilhar sua Agenda:**
1. Clique nas suas iniciais (canto superior direito)
2. **Pref. Pessoais** → Agenda → Compartilhar
3. Pesquise e selecione colaboradores

Ao compartilhar:
- Outros podem **visualizar** seus eventos
- Outros podem **criar** eventos na sua agenda
- Útil para equipes administrativas de agendamento

**Personalizar:** Na mesma tela, altere a cor da sua agenda e quantidade de dias na Dashboard.

✅ Módulo Agenda concluído!
""")
    db.commit()


def _mod_cadastro(db):
    p = _m(db, "cadastro", "Cadastros", "Gerencie clientes, fornecedores, colaboradores e contatos")
    _s(db, "cadastro", p, 0, """# Módulo: Cadastro — O Coração do DOit

Aqui ficam **todas as pessoas e empresas** do sistema:
- 👤 Clientes
- 🏢 Fornecedores
- 👥 Colaboradores
- 🏗️ Prestadores de serviço

**Ações rápidas:**
- ➕ Criar cadastro
- 🔍 Busca Avançada (Bairro, CEP, Cidade, Contatos, Documento, País, UF)
- 🖨️ Relatórios PDF/Excel
- ✉️ Criar Listas de E-mail

**Duas listas para buscar:**
- **Lista 1** — Filtros básicos: ID, Nome, Apelido, E-mail, Telefone
- **Lista 2** — Tudo da Lista 1 + Origem, Classificação, Anotações, UF
""")

    _s(db, "cadastro", p, 1, """# Ficha do Cadastro

Clique no **ID** de qualquer cadastro para abrir a ficha completa.

**Campos principais:**
| Campo | O que é |
|-------|---------|
| Origem | Como conheceu seus serviços (ex: "Instagram 2023") |
| Classificação | Categorias: Fornecedor, Cliente VIP, Piso... |
| Info Cadastrais | Nome, Apelido, Website |
| E-mails | Múltiplos, com marcação de principal ● |
| Telefones | Múltiplos, com marcação de principal ● |
| Documentos | CPF/CNPJ (validado!), Instagram, IE |
| Datas | Fundação, Aniversário, Contratação |
| Anotações | Campo livre para qualquer info |

**Sub-abas (parte inferior da tela):**
Contatos | Endereços | Documentos | Compromissos | Tarefas | E-mail | Projetos
""")

    _s(db, "cadastro", p, 2, """# Dicas de Cadastro

**Tornar cadastro privado:**
1. Clique no ícone de cadeado 🔓
2. Selecione quem terá acesso
3. Salve → cadeado fecha
4. Para reverter: clique no cadeado → "Tornar Público"

**Vincular contatos:**
- Sub-aba Contatos → indique relações: Esposo/a, Sócio/a, Vendedor

**Endereços:**
- Múltiplos endereços por cadastro
- Marque o principal com ✅
- Categorias: Obra, Cobrança, Antigo

**Documentos anexados:**
- Comprovantes, RG, contratos
- Marque principal com ✅ (aparece ao abrir o cadastro)
- Restrinja acesso por usuário se necessário

**Setup (Cadastro → Setup):**
- Classificações personalizadas
- Tipos de documento (Federal = CPF/CNPJ, Estadual = RG/IE)
- Categorias de endereço, datas, telefones, relações

✅ Módulo Cadastros concluído!
""")
    db.commit()


def _mod_projetos(db):
    p = _m(db, "projetos", "Projetos", "Crie projetos, vincule clientes, controle horas e despesas")
    _s(db, "projetos", p, 0, """# Módulo: Projetos

Concentra **todas as informações** dos projetos:
- Controle de horas e despesas
- Reuniões e visitas
- Documentos
- Informações financeiras

**Três áreas (depende do seu acesso):**

| Aba | Quem vê | O que mostra |
|-----|---------|--------------|
| **Meus Projetos** | Todos da equipe | Projetos onde você participa |
| **Líder** | Líderes | Projetos que você lidera |
| **Todos** | Diretoria/Financeiro | Todos os projetos |

Cada aba tem sub-abas: **Geral, Horas, Despesas, Ficha, Atas de Reunião, E-mails**
""")

    _s(db, "projetos", p, 1, """# Criar um Projeto

Crie pela aba **Líder** ou **Todos** (depende da permissão).

**Informações básicas:**
- **Nome** — Identificação do projeto
- **Status** — Em andamento, Em aprovação, Concluído
- **Categoria** — Arquitetura, Interiores, Reforma
- **Data de Início** — Assinatura do contrato
- **Data de Execução** — Início do desenvolvimento
- **Data de Entrega** — Prazo ou conclusão efetiva
- **Descrição** — Briefing e observações

**Vincular Cliente:**
- Busque com a lupa 🔍 no módulo Cadastro
- Sistema preenche automaticamente: telefone, e-mail, endereços

**Controle Contratado:**
- **Reuniões** — Horas contratadas para reuniões
- **Atividades** — Horas para desenvolvimento
- **Visitas** — Quantidade de visitas contratadas

Esses indicadores são **descontados automaticamente** conforme o uso.
""")

    _s(db, "projetos", p, 2, """# Lançar Horas e Despesas

**Horas** (Projeto → Horas → ➕):
- **Atividade** — Descrição breve (ex: "Revisão de planta")
- **Descrição** — Texto livre
- **Projeto** — Selecione (ou projeto administrativo para processos internos)
- **Etapas** — Conforme configurado no projeto
- **Hs** — Horas utilizadas (ou use Data Início/Fim)

💡 Pela "Meus Projetos" vê só SUAS horas. Pela "Líder"/"Todos" vê da equipe toda.

**Despesas** (Projeto → Despesas → ➕):
- **Data** — Quando ocorreu
- **Profissional** — Quem realizou
- **Projeto** — Projeto relacionado
- **Descrição** — Ex: "Deslocamento para visita de obra"
- **Pago por** — Quem pagou
- **Tipo** — Uber/Táxi, Alimentação, Hospedagem, Impressão
- **Valor** — Quanto custou
- **Arquivo** — Anexe comprovante
- **Reembolso** ☑️ — Marca que o financeiro deve reembolsar

**Controle de cobrança (colunas P e C):**
- **P** (Profissional) — Pendente/Reembolsado
- **C** (Cliente) — Não cobrar / Cobrar
""")

    _s(db, "projetos", p, 3, """# Equipe Interna e Setup

**Equipe Interna** (Projeto → Ficha → Equipe Interna):
- ➕ Adicione membros e defina a **função** de cada um
- ✅ Marque o **Líder** (acesso a Etapas e Tarefas)
- ✉️ Envie e-mail para toda equipe ativa
- 👥 Adicione equipe padrão do Setup

⚠️ Sem estar na equipe interna, o usuário não vê o projeto em "Meus Projetos".

**Setup do Projeto** (Projeto → Setup):
- **Categorias** — Tipos de projeto
- **Funções** — Funções da equipe interna
- **Etapas** — Etapas padrão para novos projetos
- **Despesas** — Categorias e unidades
- **Integração** — Classificação financeira automática
- **Equipe** — Equipe padrão + valor/hora
- **Status** — Personalizar status, cores, ordem
- **Detalhes** — Campos customizáveis (Terreno, Área, TA%, etc.)

✅ Módulo Projetos concluído!
""")
    db.commit()


def _mod_tarefas(db):
    p = _m(db, "tarefas", "Tarefas", "Crie, delegue e controle tarefas com Start/Stop")
    _s(db, "tarefas", p, 0, """# Módulo: Tarefas

Gerenciamento completo de tarefas. Se delegada a você, aparece na Dashboard.

**Visualizações:**
- 📅 **Calendário** — Por Responsável ou Projeto × Tempo
- 📋 **Lista** — Listagem com filtros avançados
- 📄 **Ficha** — Detalhes completos
- ⏱️ **Andamento** — Tarefas com Start/Stop ativo agora

**Criar tarefa:** ➕ no Calendário ou Lista
- Nome, Prioridade, Responsável
- Data início/fim, Prazo
- Vincule a Cadastro, Projeto e Etapa

**Concluir tarefa (4 formas):**
1. Dashboard → ☑️
2. Calendário → clique na barra → ✅
3. Lista → ícone ☑️
4. Ficha → ícone ✅

⚠️ Só o **responsável** pode concluir!

**Delegar em massa:**
1. Ficha do Projeto → Etapas → Gere tarefas ✅
2. Ficha → Tarefas → Filtre por Etapa + Responsável "="
3. Atribua responsável → "Atualizar todos?" → Sim
4. Clique ✅ para enviar às Dashboards

✅ Módulo Tarefas concluído!
""")
    db.commit()


def _mod_atas(db):
    p = _m(db, "atas", "Atas de Reunião", "Registre reuniões, visitas, controle horas e envie por e-mail")
    _s(db, "atas", p, 0, """# Atas de Reunião

Registre reuniões, visitas e alinhamentos vinculados ao projeto.

**Criar ata:** Projeto → Ficha → Atas de Reunião → ➕

**Campos:**
- **Assunto** — Tema principal
- **Responsável** — Quem registra
- **Data/Hora** — Início e fim (calcula horas automaticamente)
- **Local** — Onde ocorreu
- **Visita** ☑️ — Contabiliza no controle de visitas do projeto

**Corpo da ata (texto livre):**
- Decisões tomadas
- Pendências
- Observações e histórico

**Participantes:**
- **Internos** — Colaboradores do escritório
- **Externos** — Clientes, fornecedores (precisam ter cadastro)

**Documentos:**
- Anexe fotos, PDFs, planilhas
- Podem ser incorporados ao corpo da ata
""")

    _s(db, "atas", p, 1, """# Envio e Cobrança de Visitas

**Enviar ata:**
- **Salvar** — Apenas dentro do DOit
- **Enviar por E-mail** — Gera e-mail com conteúdo da ata
  - Participantes com e-mail são colocados em cópia automaticamente
- **Exportar PDF** — Contém dados, participantes, conteúdo e anexos

**Cobrança de Visitas:**
1. Configure o valor unitário da visita no projeto (ex: R$ 200,00)
2. Marque visitas para cobrança
3. São encaminhadas ao financeiro para faturamento

**Integração Agenda → Ata:**
Se um evento da Agenda estiver vinculado a um projeto, é possível **gerar uma ata diretamente** a partir dele — o sistema reaproveita as informações preenchidas.

**Controle automático:**
- Horas da reunião → descontadas do saldo contratado
- Visitas → contabilizadas automaticamente

✅ Módulo Atas concluído!
""")
    db.commit()


if __name__ == "__main__":
    seed()
