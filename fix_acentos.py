# -*- coding: utf-8 -*-
"""Corrige erros de acentuação em todo o conteúdo dos módulos.

- 'automáticamente' -> 'automaticamente' (acento indevido)
- 'contem' -> 'contém', 'Cobranca' -> 'Cobrança', etc.
- Conjunções 'é' que deveriam ser 'e'
- 'Pelá' -> 'Pela', 'calculá' -> 'calcula'
"""

import sys
sys.path.insert(0, '.')

import re
from models.database import Database


# Substituições de palavra inteira (regex word-boundary)
WORD_FIXES = {
    r'\bautomáticamente\b': 'automaticamente',
    r'\bcontem\b': 'contém',
    r'\bCobranca\b': 'Cobrança',
    r'\bIntegracao\b': 'Integração',
    r'\bunitario\b': 'unitário',
    r'\bPelá\b': 'Pela',
    r'\bcalculá\b': 'calcula',
}

# Substituições de trecho específico (conjunção 'é' -> 'e')
PHRASE_FIXES = {
    'agenda é quantidade': 'agenda e quantidade',
    'pessoas é empresas': 'pessoas e empresas',
    'Início é fim': 'Início e fim',
    'atualizações é evolução': 'atualizações e evolução',
    'Visualizam é lançam': 'Visualizam e lançam',
    'membros é defina': 'membros e defina',
    'Categorias é unidades': 'Categorias e unidades',
    'colunas P é C': 'colunas P e C',
    '**P** (Profissional)': '**P** (Profissional)',  # noop guard
}


def main():
    db = Database("training.db")
    db.initialize()

    rows = db.execute(
        "SELECT id, content_data FROM step_contents WHERE content_type = 'text'"
    ).fetchall()

    total = 0
    for row in rows:
        original = row["content_data"]
        new = original

        for pattern, repl in WORD_FIXES.items():
            new = re.sub(pattern, repl, new)

        for old, repl in PHRASE_FIXES.items():
            new = new.replace(old, repl)

        if new != original:
            db.execute(
                "UPDATE step_contents SET content_data = ? WHERE id = ?",
                (new, row["id"]),
            )
            total += 1

    db.commit()
    db.close()
    print(f"{total} etapas corrigidas.")


if __name__ == "__main__":
    main()
