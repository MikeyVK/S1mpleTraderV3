import sqlite3

db_path = r'C:\Users\miche\AppData\Roaming\Code\User\workspaceStorage\2e8e425df437b4d7a0eff38282a049fd\state.vscdb'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Delete the chat/selectedTools key to reset permissions
cursor.execute("DELETE FROM ItemTable WHERE key = 'chat/selectedTools'")
conn.commit()
print(f'Deleted {cursor.rowcount} row(s)')
conn.close()
