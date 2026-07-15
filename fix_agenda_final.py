# -*- coding: utf-8 -*-
"""Renumera etapas da Agenda e cria Lista, Setup e Recados."""
import sys
sys.path.insert(0, '.')
import sqlite3
from uuid import uuid4

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

# 1. Renumerar para sequência contínua (0,1,2,3,4,5)
steps_ordered = conn.execute("""
    SELECT id FROM steps WHERE module_id='agenda'
    ORDER BY position
""").fetchall()

# Mover tudo para posição alta temporária
for i, s in enumerate(steps_ordered):
    conn.execute("UPDATE steps SET position=? WHERE id=?", (1000 + i, s['id']))
conn.commit()

# Agora atribuir posições corretas (0 a N)
for i, s in enumerate(steps_ordered):
    conn.execute("UPDATE steps SET position=? WHERE id=?", (i, s['id']))
conn.commit()

# Verificar
print("Posições renumeradas:")
rows = conn.execute("""
    SELECT s.position, sc.content_data FROM steps s
    JOIN step_contents sc ON sc.step_id=s.id
    WHERE s.module_id='agenda' AND sc.content_type='text'
    ORDER BY s.position
""").fetchall()
for r in rows:
    title = r['content_data'].strip().split("\n")[0].replace('#','').strip()[:40]
    print(f"  pos{r['position']} | {title}")

# 2. Obter path_id e próxima posição
path_row = conn.execute("SELECT id FROM paths WHERE module_id='agenda' AND is_main=1").fetchone()
pid = path_row['id']
next_pos = len(steps_ordered)

# 3. Criar etapa: Lista
step_id = str(uuid4())
content_id = str(uuid4())
content_lista = """## Lista

A aba **Lista** exibe todos os eventos da sua agenda em formato de tabela.

**Útil para:**
- Visualizar eventos de um período específico
- Filtrar por projeto, contato ou agenda
- Localizar rapidamente um evento para editar ou excluir

Use os filtros na barra laranja para refinar a busca por data, nome ou projeto.
"""
conn.execute("INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, 'content')",
    (step_id, 'agenda', pid, next_pos))
conn.execute("INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) VALUES (?, ?, 'text', ?, 0)",
    (content_id, step_id, content_lista))
print(f"  + Lista (pos{next_pos})")
next_pos += 1

# 4. Criar etapa: Setup
step_id = str(uuid4())
content_id = str(uuid4())
content_setup = """## Setup

Em **Agenda \u2192 Setup** (disponível para quem tiver acesso) é possível personalizar:

- **Agendas Públicas** — criar, renomear, alterar cores
- **Tipos de evento** — categorizar eventos
- **Permissões** — definir quem pode criar ou editar agendas públicas

*Observação: alterações no Setup afetam toda a equipe.*
"""
conn.execute("INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, 'content')",
    (step_id, 'agenda', pid, next_pos))
conn.execute("INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) VALUES (?, ?, 'text', ?, 0)",
    (content_id, step_id, content_setup))
print(f"  + Setup (pos{next_pos})")
next_pos += 1

# 5. Criar etapa: Recados
step_id = str(uuid4())
content_id = str(uuid4())
content_recados = """## Recados

Sistema de lembretes internos entre usuários. Não é um chat.

**Como funciona:**
- Ao enviar, o destinatário recebe uma notificação
- Não é possível responder — comunicação unidirecional
- Use para avisos rápidos e lembretes

*Exemplos: solicitação de retorno para fornecedor, avisos de prazos, lembretes operacionais.*
"""
conn.execute("INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, 'content')",
    (step_id, 'agenda', pid, next_pos))
conn.execute("INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) VALUES (?, ?, 'text', ?, 0)",
    (content_id, step_id, content_recados))
print(f"  + Recados (pos{next_pos})")

conn.commit()
conn.close()
print("\nConcluído!")
