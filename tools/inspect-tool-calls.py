import sqlite3

db = r"C:\Users\yaito\AppData\Local\Ollama\db.sqlite"
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute(
    """
    SELECT tc.id, tc.message_id, tc.function_name, tc.function_arguments,
           substr(tc.function_result,1,200) as result_preview, m.model_name, m.created_at
    FROM tool_calls tc
    JOIN messages m ON m.id = tc.message_id
    WHERE tc.function_name = 'web_search'
    ORDER BY tc.id DESC
    LIMIT 10
    """
)
for row in cur.fetchall():
    print(row)
con.close()
