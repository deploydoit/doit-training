"""Remove todos os emojis do conteúdo dos módulos de treinamento."""
import sys
import re
sys.path.insert(0, '.')
from models.database import Database


def remove_emojis(text):
    """Remove emojis and emoji-like characters from text."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2600-\u26FF"          # misc symbols
        "\u2700-\u27BF"          # dingbats
        "\u200d"                 # zero width joiner
        "\ufe0f"                 # variation selector
        "]+", flags=re.UNICODE)
    
    # Also remove common emoji shortcodes used in the content
    text = emoji_pattern.sub('', text)
    
    # Remove standalone emoji characters that might be missed
    common_emojis = [
        '📅', '📌', '💬', '✅', '📄', '🔔', '⏰', '👤', '⚠️', '📋',
        '📊', '💰', '📈', '🏢', '📐', '💼', '➕', '🔍', '🖨️', '✉️',
        '📅', '☑️', '✏️', '🗑️', '⏱️', '▶️', '⏹️', '☕', '🚫',
        '📝', '📤', '📥', '🔄', '🏦', '💡', '🔓', '🔒', '👥',
        '👤', '🏗️', '🏢', '📋', '📊', '🖨️', '📄', '📌', '💬',
        '✅', '⚠️', '⏰', '🔔', '💰', '📈', '📐', '💼', '➕',
        '🔍', '✉️', '☑️', '✏️', '🗑️', '⏱️', '▶️', '⏹️',
        '📝', '📤', '📥', '🔄', '🏦', '🔓', '🔒', '👥', '🏗️',
    ]
    for emoji in common_emojis:
        text = text.replace(emoji, '')
    
    # Clean up double spaces left behind
    text = re.sub(r'  +', ' ', text)
    # Clean up lines that start with space after emoji removal
    text = re.sub(r'\n ', '\n', text)
    
    return text


def main():
    db = Database("training.db")
    db.initialize()
    
    # Get all step contents
    cursor = db.execute("SELECT id, content_data FROM step_contents")
    rows = cursor.fetchall()
    
    updated = 0
    for row in rows:
        original = row["content_data"]
        cleaned = remove_emojis(original)
        if cleaned != original:
            db.execute(
                "UPDATE step_contents SET content_data = ? WHERE id = ?",
                (cleaned, row["id"])
            )
            updated += 1
    
    db.commit()
    db.close()
    print(f"Emojis removidos de {updated} etapas.")


if __name__ == "__main__":
    main()
