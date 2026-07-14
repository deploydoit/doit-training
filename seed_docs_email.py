"""Adiciona módulos Documentos e E-mail baseados no Manual do Usuário."""
import sys
sys.path.insert(0, '.')
from models.database import Database


def seed():
    db = Database("training.db")
    db.initialize()

    _mod_documentos(db)
    _mod_email(db)

    db.commit()
    db.close()
    print("✅ Módulos Documentos e E-mail adicionados!")


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


def _mod_documentos(db):
    p = _m(db, "documentos", "Documentos",
        "Centralize todos os arquivos do DOit com filtros e organização")

    _s(db, "documentos", p, 0, """# Módulo: Documentos

Centraliza **todos os arquivos** que existem no DOit em um único lugar.

**Filtros disponíveis:**
- ID Relacionado
- Tipo de documento
- Nome do Arquivo
- Descrição
- Versão
- Data
- Criado Por

**4 abas para facilitar a navegação:**

| Aba | O que mostra |
|---|---|
| **Todos** | Todos os documentos do sistema |
| **Cadastros** | Arquivos adicionados na Ficha de cadastros |
| **Projetos** | Arquivos adicionados a projetos |
| **Atas de Reunião** | Arquivos anexados em atas |

Todas as abas permitem os mesmos filtros de pesquisa.
""")

    _s(db, "documentos", p, 1, """# Adicionando Documentos

Os documentos podem ser adicionados em diversos locais:

**Na Ficha do Cadastro** (Cadastro → Ficha → Documentos):
- Comprovantes de residência, RG, contratos
- Marque como principal ✅ para aparecer ao abrir o cadastro
- Restrinja acesso por usuário se necessário

**No Projeto** (Projeto → Ficha → Documentos):
- Propostas, plantas, renders, contratos do projeto
- Restrinja acesso clicando no ícone 🔒
- Defina **data de validade** → aparece em "Documentos a Expirar" na Dashboard

**Em Atas de Reunião:**
- Fotos, PDFs, planilhas da reunião
- Podem ser incorporados ao corpo da ata

**Dicas:**
- 📌 Documento com data de validade = alerta automático na Dashboard
- 🔒 Restrição de acesso = clique no cadeado e selecione quem pode ver
- ✅ Documento principal = aparece em destaque ao abrir o registro

✅ Módulo Documentos concluído!
""")


def _mod_email(db):
    p = _m(db, "email", "E-mail",
        "Envie e-mails pelo DOit, crie modelos e acompanhe o histórico")

    _s(db, "email", p, 0, """# Módulo: E-mail

O DOit funciona como **atalho para envio de e-mails** — ele envia usando seu provedor, mas não recebe.

⚠️ **O DOit NÃO substitui seu provedor de e-mail** (Gmail, Outlook). Ele usa o provedor como meio para enviar.

**Abas do módulo:**

| Aba | O que mostra |
|---|---|
| **Meus E-mails** | E-mails enviados por VOCÊ pelo DOit |
| **Todos E-mails** | E-mails de todos os usuários (depende do acesso) |
| **Ficha** | Detalhes do e-mail selecionado (remetente, destinatário, corpo) |
| **Modelos** | Templates reutilizáveis |
| **Setup** | Configuração de contas de e-mail |

**Envio de e-mails pelo DOit:**
- A partir de cadastros (e-mails do cliente)
- A partir de projetos (cobranças, atas)
- A partir de listas de e-mail
- Rascunhos ficam salvos até serem enviados
""")

    _s(db, "email", p, 1, """# Modelos de E-mail

Modelos são templates prontos para agilizar e-mails frequentes.

**Exemplos de uso:**
- Propostas comerciais
- Contratos
- Felicitações de aniversário
- Cobranças de etapas

**Tipos de modelo:**
- **Meus Modelos** — Criados por você (privados por padrão)
- **Modelos Públicos** — Compartilhados com toda equipe

**Criar um modelo:**
1. Vá em E-mail → Modelos → Meus Modelos
2. Clique ➕
3. Edite nome, assunto e corpo do modelo
4. Marque como **Público** ✅ se quiser compartilhar

**Usar um modelo:**
- Clique no ícone ✉️ ao lado do modelo
- Um rascunho de e-mail é criado com o conteúdo do template
- Personalize e envie

**Proteger modelo contra edições:**
- Clique no ícone 🔒 na coluna de proteção
- Outros usuários poderão usar, mas não editar
""")

    _s(db, "email", p, 2, """# Setup e Listas de E-mail

**Setup** (E-mail → Setup):
- Configure contas de e-mail para envio
- Cada provedor tem configurações específicas (SMTP)
- Precisa de ajuda? Contate o suporte pela Dona Lourdes 👵

**Listas de E-mail** (Módulo Listas):
Envie e-mails em massa para grupos filtrados.

**Criar lista:**
1. Listas → Minhas Listas → ➕
2. Dê um nome à lista
3. Vá em Cadastros → Lista 2
4. Aplique filtros desejados (ex: todos fornecedores de SP)
5. Clique no ícone ✉️ → selecione a lista criada
6. Os cadastros filtrados são adicionados à lista

**Tipos de lista:**
- **Privada** — Só você vê
- **Pública** ✅ — Toda equipe pode usar

**Exportar contatos:** Na aba Contatos da lista, clique no ícone Excel 📊

✅ Módulo E-mail concluído!
""")


if __name__ == "__main__":
    seed()
