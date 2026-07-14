# -*- coding: utf-8 -*-
"""Cria módulo 'Boas Práticas & Dicas' com acentos corretos e layout didático.

Conteúdo extraído das macros do Intercom, adaptado para treinamento.
"""

import sys
sys.path.insert(0, '.')

from uuid import uuid4
from models.database import Database


def _s(db, module_id, path_id, position, text_content):
    """Cria uma etapa de conteúdo texto."""
    step_id = str(uuid4())
    content_id = str(uuid4())
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, 'content')",
        (step_id, module_id, path_id, position),
    )
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, 'text', ?, 0)",
        (content_id, step_id, text_content),
    )
    return step_id


def create_boas_praticas_module(db):
    """Cria o módulo Boas Práticas & Dicas com conteúdo acentuado."""

    mid = "boas-praticas"
    pid = f"{mid}_main"

    # Limpar se já existe
    db.execute("DELETE FROM modules WHERE id = ?", (mid,))
    db.commit()

    db.execute(
        "INSERT INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, 'published', 1)",
        (mid, "Boas Práticas e Dicas", "Dicas operacionais para Projetos, Agenda, E-mail e Financeiro"),
    )
    db.execute(
        "INSERT INTO paths (id, module_id, name, is_main) VALUES (?, ?, 'Principal', ?)",
        (pid, mid, True),
    )

    pos = 0

    # --- INTRODUÇÃO ---
    _s(db, mid, pid, pos, """## Boas Práticas e Dicas

Este módulo reúne dicas operacionais do dia a dia no DOit.

São procedimentos comuns que todo usuário deve conhecer para trabalhar com mais agilidade.

**Áreas cobertas:**

- Projetos — criar, gerenciar equipe, cobranças, pedidos, atas
- Agenda — eventos, lançamento de horas, sincronização
- E-mail — modelos, listas
- Financeiro — relatórios, NFs
""")
    pos += 1

    # ==========================================
    # PROJETOS
    # ==========================================

    _s(db, mid, pid, pos, """## Como criar um Projeto

1. Acesse **Projeto → Todos → Geral**
2. Clique na estrelinha ao final da tarja laranja
3. O DOit abrirá a ficha do novo projeto
4. Preencha as informações e salve

*Dica: verifique se as etapas padrão estão configuradas em Setup antes de criar projetos novos.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como designar o Líder do Projeto

1. Acesse **Projeto → Todos → Geral**
2. Entre na ficha do projeto
3. Vá na sub-aba **Equipe Interna**
4. Marque a caixinha na coluna **Líder** ao lado do colaborador

*O líder tem acesso privilegiado e recebe notificações de andamento.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Equipe Padrão — adicionar membro

Para incluir um usuário na Equipe Padrão (entra automaticamente em novos projetos):

1. Acesse **Projeto → Setup → Equipe**
2. Clique na estrelinha
3. Insira: nome, Valor de Venda e Função
4. Salve

**Para incluir também em projetos antigos:**

Clique no **+** ao lado do nome do usuário. O DOit incluirá automaticamente na Equipe Interna de todos os projetos existentes.

*Se o usuário participa apenas de alguns projetos anteriores, inclua manualmente em cada um.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Equipe Interna — adicionar membro a um projeto

1. Acesse **Projetos → Todos (Líder) → Ficha**
2. Na sub-aba **Equipe Interna**, clique no ícone de adicionar
3. Selecione um ou mais membros

*Dica: para adicionar em todos os projetos de uma vez, use a Equipe Padrão em Setup.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como criar Pedidos

1. Acesse **Projeto → Pedidos → Todos**
2. Clique na estrelinha
3. Insira o nome do projeto no pop-up
4. Preencha: descrição, fornecedor, endereços de entrega e cobrança
5. Na sub-aba **Itens**, clique na estrelinha para adicionar cada item
6. Preencha: Referência, Descrição, Quantidade e Valor Unitário

**Calcular TA e RT:**

- Clique em "Calcular TA" e depois "Calcular RT"
- Informe a porcentagem ou valor base
- As taxas ficam disponíveis na aba **$** da ficha do pedido
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como cobrar Horas Técnicas (HTs)

1. Acesse **Projeto → Cobrança → Projetos**
2. Filtre pelo projeto
3. Clique no valor na coluna **HTs**
4. Clique em **OK** para gerar a cobrança
5. Clique no ícone de envelope para enviar o e-mail

**Para remover horas desta cobrança:**

- Clique no ID da cobrança gerada
- Na aba inferior, clique no ícone vermelho ao lado das horas
- Elas voltam para Cobranças e podem ser cobradas depois
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como cobrar TAs (Taxas Administrativas)

1. Acesse **Projeto → Cobrança → Projetos**
2. Filtre o projeto e clique no valor na coluna **TAs**
3. Clique **OK** para gerar
4. Clique no envelope para enviar e-mail

**Cobrar parcialmente:**

- Clique no ID da cobrança
- Remova as TAs que não quer cobrar agora (ícone vermelho)
- As removidas voltam para cobrança futura
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como cobrar Etapas (ETs)

1. Acesse **Projeto → Cobrança → Projetos**
2. Filtre o projeto
3. Clique no valor na coluna **ETs**
4. Confirme com **OK**
5. Clique no envelope para gerar o e-mail

**Remover lançamentos:**

- Em **Projeto → Cobrança → ETs**, clique no ID
- Use o ícone vermelho para retirar itens
- Os valores permanecem para cobrança futura
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como cobrar Despesas que o cliente reembolsa (RDs)

1. Acesse **Projeto → Cobrança → Projetos**
2. Filtre o projeto
3. Clique no valor na coluna **RDs**
4. Confirme com **OK**
5. Clique no envelope para e-mail

*Mesma lógica: clique no ID para remover itens que não quer cobrar agora.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como registrar despesa para reembolso

Para registrar uma despesa que o escritório irá reembolsar:

1. Acesse **Projeto → Todos → Despesas**
2. Clique na estrelinha
3. Preencha:
   - **Profissional** — quem será reembolsado
   - **Projeto** — projeto relacionado
   - **Descrição** — o que foi a despesa
   - **De/Para** — nome da pessoa
   - **Tipo de despesa** — classificação
   - **Total** — valor
   - **Arquivo** — anexo de NF (opcional)
4. Marque: **"O escritório deve pagar/reembolsar essa despesa"**
5. Clique em **Salvar**
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como criar Ata de Reunião

**Opção 1 — Pela lista de reuniões:**

1. Acesse **Projeto → Todos → Reuniões**
2. Clique na estrelinha e selecione o projeto
3. Preencha: Assunto, Local, Hora Início/Fim
4. Se for visita, marque "Visita"
5. Para cobrar a visita: deixe a bolinha laranja
6. Salve

**Opção 2 — A partir de um evento na Agenda:**

1. Acesse **Agenda → Pessoal/Pública**
2. Clique no evento e depois em **"Criar ata de reunião"**
3. Preencha e salve
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como editar TA/RT já calculada

Se precisar corrigir uma TA ou RT após o cálculo:

1. Na ficha do pedido, clique na aba **$**
2. Exclua o lançamento de TA ou RT (ícone de lixeira)
3. Confirme a exclusão
4. Volte para a aba **Itens**
5. Agora o DOit permite editar ou recalcular

*A exclusão só remove o lançamento — o pedido permanece intacto.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Como ocultar Status de projetos

Para esconder projetos de determinado status da listagem:

1. Abra **Projeto** e clique em **Setup**
2. Vá em **Status**
3. Marque o status na coluna do olhozinho
4. Volte para a lista

Os projetos com esse status ficam invisíveis.

*Útil para esconder projetos concluídos ou cancelados.*
""")
    pos += 1

    # ==========================================
    # AGENDA
    # ==========================================

    _s(db, mid, pid, pos, """## Agenda — Criar evento pessoal

1. Acesse **Agenda → Minha Agenda**
2. Clique na estrelinha ao final da barra laranja
3. Preencha os campos do evento
4. Clique em **Salvar**

*Sua agenda pessoal só é visível para você.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Agenda — Criar evento em agenda pública

1. Acesse **Agenda → Públicas**
2. Clique na estrelinha
3. Selecione a agenda pública desejada
4. Preencha os campos
5. Clique em **Salvar**

*Eventos públicos ficam visíveis para todos que ativaram aquela agenda.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Agenda — Apagar evento

1. Acesse **Agenda → Lista**
2. Encontre o evento
3. Clique na lixeirinha ao final da barra

*Atenção: a exclusão é permanente!*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Agenda — Lançar horas a partir de evento

1. Acesse **Agenda → Pessoal/Pública**
2. Clique no evento para abrir a ficha
3. Clique em **"Lançar horas"**
4. Preencha: atividade, quantidade de horas
5. Clique em **Salvar**

As horas aparecerão em **Projeto → Todos → Atividades**.

*O lançamento não é automático — é necessário clicar em "Lançar horas".*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Agenda — Sincronizar com iPhone

**Pelo app DOit:**

1. Baixe o app: https://apps.apple.com/br/app/doit/id1194145966
2. Faça login
3. Menu lateral → Agendas
4. Clique na engrenagem
5. Selecione a agenda e clique no ícone de nuvem

**Pelo navegador do iPhone:**

1. Acesse o DOit pelo Safari
2. Clique em "Versão Clássica"
3. Menu lateral → Agenda → Pessoal ou Pública
4. Clique no ícone de calendário
5. O iPhone abrirá a tela para cadastrar no Calendar
""")
    pos += 1

    # ==========================================
    # E-MAIL
    # ==========================================

    _s(db, mid, pid, pos, """## E-mail — Criar modelos

1. Acesse **E-mail → Modelos → Meus Modelos**
2. Clique na estrelinha
3. Preencha o modelo
4. Clique em **Salvar**

**Tornar público:** marque a caixinha na coluna "Público"

**Manter privado:** deixe marcada a caixinha com o cadeado
""")
    pos += 1

    _s(db, mid, pid, pos, """## E-mail — Criar lista de e-mail

1. Acesse o módulo **Listas** e clique na estrelinha
2. Nomeie sua lista
3. Acesse **Cadastro → Lista 2**
4. Filtre pela classificação (ex: Cliente)
5. Clique no ícone de envelope
6. Selecione a lista no pop-up
7. Marque "evitar duplicados" se necessário
8. Clique em **Salvar**

*Após salvar, clique na notificação no canto inferior direito para ver a lista completa.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## E-mail — Atualizar senha

Quando trocar a senha do e-mail no provedor, atualize no DOit:

1. Clique nas suas iniciais (canto superior direito)
2. Acesse **Preferências**
3. Aba **E-mail**
4. Clique em **"Enter Email Password"**
5. Insira a nova senha
6. Aguarde "Success"

*Sem essa atualização, o envio de e-mails pelo DOit para de funcionar.*
""")
    pos += 1

    # ==========================================
    # FINANCEIRO
    # ==========================================

    _s(db, mid, pid, pos, """## Financeiro — Relatório com múltiplas contas

1. Acesse **Financeiro → Contas**
2. Na coluna com ícone de lupa, selecione as contas
3. Acesse **Financeiro → aba ícone Lupa**
4. Todas as contas selecionadas aparecem juntas
5. Aplique filtros
6. Gere PDF ou planilha pelos ícones

*Útil para consolidar a visão financeira do escritório.*
""")
    pos += 1

    _s(db, mid, pid, pos, """## Financeiro — Emitir NF de Serviço

1. No Financeiro, clique no ícone de ferramenta do lançamento
2. No pop-up, clique em **"Faturar"**
3. O DOit redireciona para a ficha da NF
4. Preencha: Código, informações complementares
5. Clique em **"Escolher Endereço"** (Destinatário)
6. Clique no botão de emitir

*Se o cadastro tem apenas um endereço, ele é preenchido automaticamente.*

**Pré-requisito:** Certificado digital A1 (PFX + senha) configurado.
""")
    pos += 1

    _s(db, mid, pid, pos, """## Financeiro — Emitir NF avulsa

Para emitir NF sem amarração com estoque:

1. Acesse **Faturamento → Saída → Lista**
2. Clique na estrelinha
3. Insira o ID do pedido
4. Clique em **"Procurar"** — o DOit mostra prévia
5. Clique em **"Criar"**
6. Preencha: CFOP, Origem dos produtos, etc.
7. Emita normalmente

*Quando a mercadoria for enviada, emita uma NF de remessa para baixar do estoque.*
""")
    pos += 1

    # ==========================================
    # CONCLUSÃO
    # ==========================================

    _s(db, mid, pid, pos, """## Módulo concluído!

Você agora conhece as principais dicas operacionais do DOit.

**Resumo:**

- **Projetos** — criar, equipe, pedidos, cobranças, atas
- **Agenda** — eventos, horas, sincronização mobile
- **E-mail** — modelos, listas, senha
- **Financeiro** — relatórios, emissão de NF

*Consulte este módulo sempre que precisar relembrar algum procedimento.*
""")

    db.commit()
    print(f"  Módulo '{mid}' criado com {pos + 1} etapas.")


def main():
    db = Database("training.db")
    db.initialize()

    print("Recriando módulo Boas Práticas com acentos e layout corretos...")
    create_boas_praticas_module(db)

    db.close()
    print("Concluído!")


if __name__ == "__main__":
    main()
