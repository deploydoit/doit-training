# -*- coding: utf-8 -*-
"""Substitui ícones base64 inline por URLs raw do GitHub (funciona no Cloud)."""
import sys
sys.path.insert(0, '.')
import sqlite3
import re

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

BASE_URL = "https://raw.githubusercontent.com/deploydoit/doit-training/main"
star_url = f"{BASE_URL}/media/agenda/star.png"
lixeira_url = f"{BASE_URL}/media/lixeira.png"

star_html = f'<img src="{star_url}" style="width:18px;height:18px;vertical-align:middle;">'
lixeira_html = f'<img src="{lixeira_url}" style="width:18px;height:18px;vertical-align:middle;">'

# Encontrar todas as etapas com tags <img src="data:image...
rows = conn.execute("""SELECT id, content_data FROM step_contents 
    WHERE content_type='text' AND content_data LIKE '%<img src="data:image%'""").fetchall()

print(f"Encontradas {len(rows)} etapas com base64 inline")

for r in rows:
    content = r['content_data']
    # Identificar qual ícone é (star ou lixeira) pelo contexto
    # Substituir TODAS as tags <img src="data:image..." por URL
    
    # Padrão: qualquer <img src="data:image/png;base64,..."> com style
    pattern = r'<img src="data:image/png;base64,[^"]+"\s*style="[^"]*">'
    
    matches = re.findall(pattern, content)
    for match in matches:
        # Determinar se é star ou lixeira pelo contexto ao redor
        idx = content.index(match)
        context = content[max(0, idx-50):idx+len(match)+50]
        
        if 'lixeir' in context.lower() or 'ícone' in context.lower() and 'lista' in context.lower():
            # É lixeira se está no contexto de apagar
            replacement = lixeira_html
        else:
            # Default: star (criar)
            replacement = star_html
        
        content = content.replace(match, replacement, 1)
    
    if content != r['content_data']:
        conn.execute("UPDATE step_contents SET content_data=? WHERE id=?", (content, r['id']))
        print(f"  Corrigido: {r['id']}")

conn.commit()

# Verificar que não sobrou nenhum base64
remaining = conn.execute("""SELECT COUNT(*) c FROM step_contents 
    WHERE content_type='text' AND content_data LIKE '%data:image%'""").fetchone()
print(f"\nBase64 inline restantes: {remaining['c']}")

conn.close()
print("Concluído!")
