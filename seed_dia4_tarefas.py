"""Atualiza módulo Tarefas com conteúdo detalhado do Dia 4."""
import sys
sys.path.insert(0, '.')
from models.database import Database


def seed():
    db = Database("training.db")
    db.initialize()

    # Remover módulo tarefas antigo
    db.execute("DELETE FROM modules WHERE id = 'tarefas'")
    db.commit()

    # Criar módulo expandido
    mid = "tarefas"
    pid = f"{mid}_main"
    db.execute(
        "INSERT INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, 'published', 1)",
        (mid, "Tarefas", "Crie, delegue, controle horas com Start/Stop e gerencie cronogramas"))
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, 'Principal', ?)",
        (pid, mid, True))

    _s(db, mid, pid, 0, """# Módulo de Tarefas — Visão Geral

O módulo de Tarefas gerencia todas as atividades da equipe:
- ➕ Criação de tarefas
- 👤 Delegação de atividades
- ⏱️ Controle de horas trabalhadas
- 📅 Acompanhamento de cronogramas
- 📊 Monitoramento do andamento dos projetos

É um dos **principais meios de lançamento de horas** no sistema.

**4 visualizações:**

| Visualização | O que mostra |
|---|---|
| 📅 **Calendário** | Cronograma visual (por Responsável, Projeto, Dia, Semana) |
| 📋 **Lista** | Listagem com filtros avançados (principal tela de busca) |
| 📄 **Ficha** | Detalhes da tarefa selecionada |
| ⏱️ **Andamento** | Quem está trabalhando agora (Start/Stop ativo) |

**Permissões:**
- Usuários comuns → veem só suas tarefas
- Líderes → veem tarefas dos projetos que lideram
- Acesso total → veem todas as tarefas do escritório
""")

    _s(db, mid, pid, 1, """# Criar uma Tarefa Manual

Para atividades que **não fazem parte do fluxo padrão** dos projetos (solicitações extraordinárias, demandas pontuais).

**Como criar:** ➕ no Calendário ou Lista

**Campos:**

| Campo | Descrição |
|---|---|
| **Nome** | Ex: "Modelagem 3D", "Revisão de Projeto" |
| **Tipo** | Documento, Agenda, Reunião, Ligação, Outros |
| **Prioridade** | Alta → Média → Baixa → Não especificada |
| **Responsável** | Quem vai executar (padrão: quem criou) |
| **Data início/fim** | Período de execução |
| **Prazo** | Data limite |
| **Dia Inteiro** ☑️ | Sistema considera 8 horas automaticamente |

💡 **Prioridade afeta a Dashboard:** tarefas Alta aparecem primeiro, depois Média, Baixa. Sem prioridade → ordena por prazo.
""")

    _s(db, mid, pid, 2, """# Relacionamentos e Descrição

**Relacionamentos obrigatórios:**

| Campo | Para que serve |
|---|---|
| **Cadastro** | Vincule cliente/fornecedor (informativo) |
| **Projeto** | ⚠️ **Obrigatório!** Horas são contabilizadas aqui |
| **Etapa** | Ex: Levantamento, Estudo Preliminar, Executivo |

Sem projeto vinculado, **não há controle correto de horas**.

**Descrição:**
- Campo livre para instruções e informações importantes

**Follow-up:**
- Registre atualizações e evolução do trabalho
- Funciona como histórico da execução

**Participantes:**
- **Responsável** → Controle total: lança horas, finaliza, reabre
- **Participantes** → Visualizam e lançam horas, mas **NÃO podem concluir**
""")

    _s(db, mid, pid, 3, """# Start/Stop — Lançamento de Horas

O principal método de registrar horas trabalhadas.

**Iniciando:**
1. Localize sua tarefa na Dashboard ou no módulo Tarefas
2. Clique em ▶️ **Start**
3. O sistema começa a contar o tempo automaticamente

**⚠️ Importante — NÃO é controle de ponto!**
O objetivo é medir tempo efetivamente dedicado às atividades dos projetos.

**Pausas:**
- ☕ Pequenas (água, banheiro, conversa rápida) → **não precisa pausar**
- 🚫 Longas (reunião não relacionada, ausência significativa) → **pause**

**Encerrando:**
1. Clique em ⏹️ **Stop**
2. O sistema permite:
   - ✏️ Ajustar horários (se esqueceu de parar)
   - 📝 Inserir observações (problemas, interrupções)
3. Confirme → horas ficam registradas

💡 **Dica:** Se esqueceu o Start ligado, ao clicar Stop você pode corrigir o período antes de salvar.
""")

    _s(db, mid, pid, 4, """# Concluir e Reabrir Tarefas

**Concluir ≠ Parar cronômetro!**
Parar o Stop apenas encerra o lançamento de horas. Para **finalizar definitivamente:**

**4 formas de concluir:**
1. Dashboard → ☑️
2. Calendário → clique na barra → ✅
3. Lista → ícone ☑️
4. Ficha → ícone ✅

**Após conclusão:**
- Tarefa sai das pendências
- Não é possível registrar novas horas

**Reabrir tarefa concluída por engano:**
1. Módulo Tarefas → aba **Lista**
2. Localize a tarefa (use filtros)
3. Remova a marcação de concluída
4. Tarefa volta ao normal para novos lançamentos
""")

    _s(db, mid, pid, 5, """# Delegação Automática por Projeto

Além da criação manual, o sistema gera tarefas **automaticamente** a partir da estrutura do projeto.

**Passo a passo:**

**1. Selecione as etapas** (Projeto → Ficha → Etapas)
- Mantenha apenas as etapas que serão usadas naquele projeto
- Remova as desnecessárias para não poluir o cronograma

**2. Gere as tarefas** (clique no botão de geração ✅)
- O sistema cria automaticamente todas as tarefas das etapas selecionadas
- Exemplos: Reunião de Aproximação, Levantamento, Estudo Preliminar, Executivo, Apresentação, Renderização

**3. Delegue:**

**Opção A — Mesmo responsável para todas:**
- Selecione responsável → aplique para todas → defina data inicial
- Sistema define prazos automaticamente

**Opção B — Responsáveis diferentes:**
- Defina responsável individualmente por tarefa
- Use filtro asterisco (*) para ver apenas preenchidas
- Defina data inicial → sistema delega automaticamente

**Resultado:**
- Tarefas ficam com status **Pendente**
- Responsáveis recebem na **Dashboard**
- Start/Stop liberado para lançamento
- Cronograma reflete a distribuição

✅ Módulo Tarefas concluído!
""")

    db.commit()
    db.close()
    print("✅ Módulo Tarefas atualizado com conteúdo completo do Dia 4!")


def _s(db, mid, pid, pos, txt):
    sid = f"{mid}_s{pos}"
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, 'content')", (sid, mid, pid, pos))
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, 'text', ?, 0)", (f"c_{sid}", sid, txt))


if __name__ == "__main__":
    seed()
