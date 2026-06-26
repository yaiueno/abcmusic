import json
import sqlite3

db = r"C:\Users\yaito\AppData\Local\Ollama\db.sqlite"
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("SELECT id, role, content, thinking, created_at FROM messages WHERE id >= 1135 ORDER BY id")
rows = cur.fetchall()
con.close()

out = []
for r in rows:
    out.append({"id": r[0], "role": r[1], "content_len": len(r[2] or ""), "thinking_len": len(r[3] or ""), "created_at": r[4]})
    if r[1] == "tool":
        try:
            data = json.loads(r[2])
            out.append({"tool_results_count": len(data.get("results", []))})
            for i, res in enumerate(data.get("results", [])[:3]):
                out.append({"result": i, "title": res.get("title"), "url": res.get("url"), "content_preview": (res.get("content") or "")[:200]})
        except Exception as e:
            out.append({"parse_error": str(e)})

with open(r"c:\情報科学演習\gui-websearch-result.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("written", len(out), "entries")
