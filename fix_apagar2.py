# -*- coding: utf-8 -*-
"""Adiciona ícone da lixeira na etapa Apagar evento."""
import sys
sys.path.insert(0, '.')
import sqlite3
import base64

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

with open('media/lixeira.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
lixeira = f'<img src="data:image/png;base64,{b64}" style="height:18px;width:auto;vertical-align:middle;display:inline-block;">'

r = conn.execute("""SELECT sc.id FROM step_contents sc JOIN steps s ON sc.step_id=s.id
    WHERE s.id='55940d5e-b743-4a56-9285-11f9712e5938' AND sc.content_type='text'""").fetchone()

content = f"""## Apagar evento

**Opção 1 — Pela ficha do evento:**
1. Toque no evento para abrir a ficha
2. Role para baixo
3. Clique no ícone {lixeira}

**Opção 2 — Pela lista:**
1. Acesse **Agenda \u2192 Lista**
2. Encontre o evento
3. Clique no ícone {lixeira} ao final da barra

*Atenção: a exclusão é permanente!*
"""

conn.execute("UPDATE step_contents SET content_data=? WHERE id=?", (content, r['id']))
conn.commit()
print("Ícone de lixeira adicionado em Apagar evento")
conn.close()
