import sqlite3
import json

db_path = r'C:\Users\miche\AppData\Roaming\Code\User\workspaceStorage\2e8e425df437b4d7a0eff38282a049fd\state.vscdb'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT value FROM ItemTable WHERE key = 'chat/selectedTools'")
result = cursor.fetchone()

if result:
    data = json.loads(result[0])
    
    # Add the st3-workflow MCP server as a toolset
    toolset_name = 'SimpleTraderV3/.vscode/mcp.json: st3-workflow'
    
    # Check if it already exists
    exists = False
    for entry in data.get('toolSetEntries', []):
        if entry[0] == toolset_name:
            entry[1] = True
            exists = True
            break
    
    if not exists:
        data['toolSetEntries'].append([toolset_name, True])
    
    # Update database
    cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'chat/selectedTools'", (json.dumps(data),))
    conn.commit()
    print(f'Added st3-workflow toolset to whitelist')
    print(f'Toolset name: {toolset_name}')
else:
    print('ERROR: No chat/selectedTools found')

conn.close()
