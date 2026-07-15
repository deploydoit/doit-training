# -*- coding: utf-8 -*-
"""Remove todas as imagens base64 inline do texto e substitui por emojis
ou imagens separadas no banco. O Streamlit Cloud não renderiza base64 inline."""
import sys
sys.path.insert(0, '.')
import sqlite3
from uuid import uuid4

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

# ===== AGENDA POS 0: Módulo Agenda (tem visualizacao inline) =====
content_s0 = """\u0023\u0023 Módulo: Agenda

Gerencie compromissos e eventos do escritório.

**Duas áreas principais:**

**Minha Agenda** — Compromissos que deve participar:
- Reuniões, visitas de obra, treinamentos

**Agendas Públicas** — Compartilhadas com toda equipe:
- Sala de reunião, Férias, Visitas de obra

Na agenda pública, você também visualiza a agenda de outros usuários que compartilharam com você.

---

*Observações:*

*Visualizações: Mensal | Semanal | Diária. Use o botão "Hoje" para voltar ao dia atual rapidamente.*

*Integração Google Agenda:*
- *Eventos do DOit aparecem no Google Agenda*
- *Eventos do Google Agenda aparecem no DOit*

*Mais adiante neste módulo, você aprenderá a configurar a agenda do DOit com a do Google.*
"""
conn.execute("UPDATE step_contents SET content_data=? WHERE id='c_agenda_s0'", (content_s0,))
# Readicionar visualizacao.png como imagem separada
conn.execute("DELETE FROM step_contents WHERE step_id='agenda_s0' AND content_type='image'")
conn.execute("""INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order)
    VALUES (?, 'agenda_s0', 'image', 'media/agenda/visualizacao.png', 'Visualizações', 1)""", (str(uuid4()),))


# ===== AGENDA POS 1: Criar um Evento (tem star, salvar, salvareenviar, criarata, lancarhoras) =====
content_s1 = """\u0023\u0023 Criar um Evento

Clique no ícone ⭐ na Agenda para criar.

**Campos do evento:**
- **Nome** — Ex: "Treinamento DOit", "Reunião de Equipe", "Visita de Obra"
- **Local** — Vinculado a um cadastro (endereço buscado da base de cadastros, com endereço criado)
- **Projeto** — Relacione a um projeto específico (para atividades internas, use o projeto com nome do escritório)
- **Etapa** — Vincule a uma etapa: Administrativo, Treinamento, Proposta, Arquitetura...
- **Data/Hora** — Início, término, opção de dia inteiro
- **Repetição** — Reuniões semanais, alinhamentos recorrentes
- **Descrição** — Pautas, links, observações
- **Agenda** — Selecione as agendas que devem fazer parte desse evento, de outros colaboradores ou pública
- **Contatos** — Externos: Clientes, fornecedores, parceiros participantes

---

*Observação: nenhum campo é de preenchimento obrigatório, mas para lançar horas ou ata de reunião, é obrigatório o projeto preenchido.*
"""
conn.execute("UPDATE step_contents SET content_data=? WHERE id='c_agenda_s1'", (content_s1,))
# Garantir imagens separadas: criarevento, salvar, salvareenviar, lancarhoras, criarata
conn.execute("DELETE FROM step_contents WHERE step_id='agenda_s1' AND content_type='image'")
imgs_s1 = [
    ('media/agenda/criarevento.png', 'Tela de criar evento', 1),
    ('media/agenda/salvar.png', 'Botão Salvar', 2),
    ('media/agenda/salvareenviar.png', 'Botão Salvar e Enviar', 3),
    ('media/agenda/lancarhoras.png', 'Lançar horas', 4),
    ('media/agenda/criarata.png', 'Criar ata de reunião', 5),
]
for path, alt, order in imgs_s1:
    conn.execute("""INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order)
        VALUES (?, 'agenda_s1', 'image', ?, ?, ?)""", (str(uuid4()), path, alt, order))


# ===== AGENDA POS 2: Agenda Pública (tem ativarpublicas inline) =====
content_pub = """\u0023\u0023 Agenda Pública

Além da sua agenda pessoal, o DOit possui as **Agendas Públicas** — agendas compartilhadas visíveis para toda a equipe. É aqui também que você encontra as agendas de outros colaboradores que compartilharam com você.

Um mesmo evento pode aparecer mais de uma vez se estiver vinculado a duas ou mais agendas ativas. Cada exibição aparece com a cor da respectiva agenda.

**Ativar ou desativar agendas:**

Toque em "Agendas" para escolher quais deseja manter ativas (visíveis). Para deixar de ver uma agenda, basta desativá-la. Nessa lista você encontra:
- As agendas públicas do escritório
- As agendas de colaboradores que compartilharam com você

**Sobre as agendas públicas:**

São personalizáveis em nome e cor. Servem para garantir que as principais atividades do escritório fiquem visíveis para todos.

**Exemplos de uso:**
- **Férias** — crie o evento na agenda do colaborador e marque também na agenda Férias
- **Sala de reunião** — reserve o horário da sala física marcando nessa agenda
- **Visita a obra** — crie o evento na sua agenda e marque também aqui, assim todos veem quem está em obra

Esses são apenas alguns exemplos. Em **Agenda → Setup** (disponível para quem tiver acesso) é possível criar, editar e personalizar as agendas públicas.
"""
conn.execute("UPDATE step_contents SET content_data=? WHERE id='1e4c0b58-be50-4940-a1be-b784799dc349'", (content_pub,))
conn.execute("DELETE FROM step_contents WHERE step_id='bc195355-3921-4546-978a-ca93cf3045c6' AND content_type='image'")
conn.execute("""INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order)
    VALUES (?, 'bc195355-3921-4546-978a-ca93cf3045c6', 'image', 'media/agenda/ativarpublicas.png', 'Ativar agendas', 1)""", (str(uuid4()),))


# ===== AGENDA POS 3: Compartilhar (tem star, selecionartodos, selecionaralguns inline) =====
content_comp = """\u0023\u0023 Compartilhar sua Agenda

1. Clique nas suas iniciais (canto superior direito)
2. Pref. Pessoais → Agenda → Compartilhar
3. Toque na estrelinha ⭐
4. Pesquise e selecione colaboradores:
   - Para marcar todos de uma só vez, use o ícone de seleção total
   - Para selecionar apenas alguns, marque individualmente

**Ao compartilhar:**
- Outros podem visualizar seus eventos
- Outros podem criar eventos na sua agenda
- Útil para equipes administrativas de agendamento
"""
conn.execute("UPDATE step_contents SET content_data=? WHERE id=(SELECT id FROM step_contents WHERE step_id='agenda_s2' AND content_type='text')", (content_comp,))
conn.execute("DELETE FROM step_contents WHERE step_id='agenda_s2' AND content_type='image'")
conn.execute("""INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order)
    VALUES (?, 'agenda_s2', 'image', 'media/agenda/compartilhar.png', 'Tela de compartilhar agenda', 1)""", (str(uuid4()),))


# ===== AGENDA POS 4: Apagar evento (tem lixeira inline) =====
content_apagar = """\u0023\u0023 Apagar evento

**Opção 1 — Pela ficha do evento:**
1. Toque no evento para abrir a ficha
2. Role para baixo
3. Clique no ícone 🗑️

**Opção 2 — Pela lista:**
1. Acesse **Agenda → Lista**
2. Encontre o evento
3. Clique no ícone 🗑️ ao final da barra

*Atenção: a exclusão é permanente!*
"""
conn.execute("UPDATE step_contents SET content_data=? WHERE id='9d3d57a0-485b-4d74-8516-f644a248fba5'", (content_apagar,))


# ===== AGENDA POS 5: Integração Google (tem star inline) =====
r = conn.execute("SELECT id, content_data FROM step_contents WHERE id='461c2f87-ed4f-434b-a07f-73e30a4b0e0e'").fetchone()
if r:
    import re
    # Substituir todas as tags <img...> por ⭐
    clean = re.sub(r'<img[^>]+>', '⭐', r['content_data'])
    conn.execute("UPDATE step_contents SET content_data=? WHERE id=?", (clean, r['id']))


conn.commit()
print("Todas as imagens base64 inline removidas e substituídas por emojis/imagens separadas")
conn.close()
