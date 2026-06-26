import sqlite3

db = r"C:\Users\yaito\AppData\Local\Ollama\db.sqlite"
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute(
    """
    SELECT id, role, substr(content,1,800), model_name, created_at
    FROM messages
    WHERE id >= 1135
    ORDER BY id
    """
)
for row in cur.fetchall():
    print(f"\n=== msg {row[0]} role={row[1]} model={row[3]} at={row[4]} ===")
    print(row[2])
con.close()
