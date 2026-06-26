import sqlite3

db = r"C:\Users\yaito\AppData\Local\Ollama\db.sqlite"
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("tables:", tables)
for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [c[1] for c in cur.fetchall()]
    print(f"\n{t} cols:", cols)
    cur.execute(f"SELECT * FROM {t} LIMIT 5")
    rows = cur.fetchall()
    for row in rows:
        print(" ", row)
con.close()
