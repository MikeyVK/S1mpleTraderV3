import sqlite3
import json

db_path = r'C:\Users\miche\AppData\Roaming\Code\User\workspaceStorage\2e8e425df437b4d7a0eff38282a049fd\state.vscdb'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Search for relevant keys
cursor.execute('''SELECT key, value FROM ItemTable 
                  WHERE key LIKE '%mcp%' OR key LIKE '%tool%' OR key LIKE '%permission%' 
                  OR key LIKE '%approval%' OR key LIKE '%copilot.chat%'
                  LIMIT 50''')

for row in cursor.fetchall():
    print(f'\n=== {row[0]} ===')
    try:
        data = json.loads(row[1])
        print(json.dumps(data, indent=2))
    except:
        print(row[1][:200])
