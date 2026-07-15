# -*- coding: utf-8 -*-
"""Restaura ícones reais (star, lixeira) no texto e ajusta tamanhos de imagem."""
import sys
sys.path.insert(0, '.')
import sqlite3
import base64

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

# Carregar ícones pequenos como base64
with open('media/agenda/star.png', 'rb') as f:
    star_b64 = base64.b64encode(f.read()).decode()
with open('media/lixeira.png', 'rb') as f:
    lixeira_b64 = base64.b64encode(f.read()).decode()

star_html = f'<img src="data:image/png;base64,{star_b64}" style="width:18px;height:18px;vertical-align:middle;">'
lixeira_html = f'<img src="data:image/png;base64,{lixeira_b64}" style="width:18px;height:18px;vertical-align:middle;">'

# Substituir emojis pelos ícones reais em todas as etapas
rows = conn.execute("SELECT id, content_data FROM step_contents WHERE content_type='text' AND content_data LIKE '%\u2b50%'").fetchall()
for r in rows:
    new = r['content_data'].replace('\u2b50', star_html)
    conn.execute("UPDATE step_contents SET content_data=? WHERE id=?", (new, r['id']))
    print(f"  Star restaurado em {r['id']}")

rows = conn.execute("SELECT id, content_data FROM step_contents WHERE content_type='text' AND content_data LIKE '%\U0001f5d1\ufe0f%'").fetchall()
for r in rows:
    new = r['content_data'].replace('\U0001f5d1\ufe0f', lixeira_html)
    conn.execute("UPDATE step_contents SET content_data=? WHERE id=?", (new, r['id']))
    print(f"  Lixeira restaurada em {r['id']}")

conn.commit()
print("\nÍcones restaurados!")
conn.close()
