# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

r = conn.execute("""SELECT sc.id FROM step_contents sc JOIN steps s ON sc.step_id=s.id
    WHERE s.id='55940d5e-b743-4a56-9285-11f9712e5938' AND sc.content_type='text'""").fetchone()

content = """## Apagar evento

**Opção 1 — Pela ficha do evento:**
1. Toque no evento para abrir a ficha
2. Role para baixo
3. Clique no ícone da lixeira

**Opção 2 — Pela lista:**
1. Acesse **Agenda \u2192 Lista**
2. Encontre o evento
3. Clique na lixeirinha ao final da barra

*Atenção: a exclusão é permanente!*
"""

conn.execute("UPDATE step_contents SET content_data=? WHERE id=?", (content, r['id']))
conn.commit()
print("Apagar evento corrigido")
conn.close()
