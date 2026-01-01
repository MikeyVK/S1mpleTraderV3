import sqlite3
import json
import os

# Check global state database
global_path = r'C:\Users\miche\AppData\Roaming\Code\User\globalStorage\state.vscdb'

if os.path.exists(global_path):
    conn = sqlite3.connect(global_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT key FROM ItemTable WHERE key LIKE '%tool%' OR key LIKE '%mcp%' OR key LIKE '%permission%'")
    keys = cursor.fetchall()
    
    if keys:
        print('=== Global State Keys ===')
        for key in keys:
            print(f'  {key[0]}')
    else:
        print('No relevant keys found in global state')
    
    conn.close()
else:
    print('Global state.vscdb not found')
