import sqlite3
import json

db_path = r'C:\Users\miche\AppData\Roaming\Code\User\workspaceStorage\2e8e425df437b4d7a0eff38282a049fd\state.vscdb'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT value FROM ItemTable WHERE key = 'chat/selectedTools'")
result = cursor.fetchone()

if result:
    data = json.loads(result[0])
    print('=== ToolSet Entries ===')
    for entry in data.get('toolSetEntries', []):
        print(f'  {entry[0]}: {entry[1]}')
    
    print('\n=== Checking for st3-workflow toolset ===')
    has_st3 = any('st3-workflow' in str(entry[0]) for entry in data.get('toolSetEntries', []))
    print(f'Has st3-workflow toolset: {has_st3}')
    
conn.close()
