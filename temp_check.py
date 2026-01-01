import sqlite3
import json

db_path = r'C:\Users\miche\AppData\Roaming\Code\User\workspaceStorage\2e8e425df437b4d7a0eff38282a049fd\state.vscdb'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT value FROM ItemTable WHERE key = 'chat/selectedTools'")
result = cursor.fetchone()

if result:
    data = json.loads(result[0])
    st3_tools = [tool for tool in data.get('toolEntries', []) if 'st3-workflow' in tool[0]]
    print(f'Found {len(st3_tools)} st3-workflow tools in database:')
    for tool in st3_tools[:5]:  # Show first 5
        print(f'  {tool[0]}: {tool[1]}')
    if len(st3_tools) > 5:
        print(f'  ... and {len(st3_tools) - 5} more')
else:
    print('No chat/selectedTools key found')
    
conn.close()
