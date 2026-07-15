# -*- coding: utf-8 -*-
"""Reordena etapas da Agenda e corrige texto de Apagar evento."""
import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

# 1. Trocar posições: Agenda Pública (pos3) vira pos2, Compartilhar (pos2) vira pos3
conn.execute("UPDATE steps SET position=99 WHERE id='agenda_s2'")
conn.execute("UPDATE steps SET position=2 WHERE id='bc195355-3921-4546-978a-ca93cf3045c6'")
conn.execute("UPDATE steps SET position=3 WHERE id='agenda_s2'")
conn.commit()

# 2. Corrigir texto de Apagar evento (pos4)
content_apagar = """## Apagar evento

1. Acesse **Agenda \u2192 Lista**
2. Encontre o evento
3. Clique na lixeirinha ao final da barra

Outra op\u00e7\u00e3o: toque no evento para abrir a ficha. Rolando para baixo, voc\u00ea encontrar\u00e1 o \u00edcone da lixeira.

*Aten\u00e7\u00e3o: a exclus\u00e3o \u00e9 permanente!*
"""

r = conn.execute("""SELECT sc.id FROM step_contents sc JOIN steps s ON sc.step_id=s.id
    WHERE s.id='55940d5e-b743-4a56-9285-11f9712e5938' AND sc.content_type='text'""").fetchone()
conn.execute("UPDATE step_contents SET content_data=? WHERE id=?", (content_apagar, r['id']))
conn.commit()

# Verificar
rows = conn.execute("""
    SELECT s.position, sc.content_data
    FROM steps s JOIN step_contents sc ON sc.step_id=s.id
    WHERE s.module_id='agenda' AND sc.content_type='text'
    ORDER BY s.position
""").fetchall()
for r in rows:
    title = r['content_data'].strip().split("\n")[0].replace('#','').strip()[:50]
    print(f"pos{r['position']} | {title}")

conn.close()
print("\nConcluído!")
