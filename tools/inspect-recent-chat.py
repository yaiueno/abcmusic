import sqlite3

db = r"C:\Users\yaito\AppData\Local\Ollama\db.sqlite"
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute(
    """
    SELECT id, role, substr(content,1,300), substr(thinking,1,200), model_name, created_at
    FROM messages
    WHERE chat_id = (SELECT chat_id FROM messages WHERE id = 1136)
    ORDER BY id DESC
    LIMIT 15
    """
)
for row in cur.fetchall():
    print("---")
    print(row)
con.close()
