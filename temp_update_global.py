import sqlite3
import json
import os

global_path = r'C:\Users\miche\AppData\Roaming\Code\User\globalStorage\state.vscdb'
conn = sqlite3.connect(global_path)
cursor = conn.cursor()

cursor.execute("SELECT value FROM ItemTable WHERE key = 'chat/selectedTools'")
result = cursor.fetchone()

if result:
    data = json.loads(result[0])
    print('=== Global ToolSet Entries ===')
    for entry in data.get('toolSetEntries', [])[:10]:
        print(f'  {entry[0]}: {entry[1]}')
    
    print(f'\nTotal toolsets: {len(data.get("toolSetEntries", []))}')
    
    # Check for st3-workflow
    has_st3 = any('st3-workflow' in str(entry[0]) for entry in data.get('toolSetEntries', []))
    print(f'Has st3-workflow: {has_st3}')
    
    if not has_st3:
        print('\n>>> Adding st3-workflow toolset to global state...')
        toolset_name = 'SimpleTraderV3/.vscode/mcp.json: st3-workflow'
        data['toolSetEntries'].append([toolset_name, True])
        
        # Also add individual tools
        st3_tools = [
            'mcp_st3-workflow_transition_phase',
            'mcp_st3-workflow_force_phase_transition',
            'mcp_st3-workflow_safe_edit_file',
            'mcp_st3-workflow_git_status',
            'mcp_st3-workflow_git_add_or_commit',
            'mcp_st3-workflow_close_issue',
            'mcp_st3-workflow_health_check'
        ]
        
        for tool in st3_tools:
            exists = any(entry[0] == tool for entry in data.get('toolEntries', []))
            if not exists:
                data['toolEntries'].append([tool, True])
        
        cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'chat/selectedTools'", (json.dumps(data),))
        conn.commit()
        print(f'✓ Added st3-workflow to global whitelist')
else:
    print('No global chat/selectedTools found')

conn.close()
