import sqlite3
import json

db_path = r'C:\Users\miche\AppData\Roaming\Code\User\workspaceStorage\2e8e425df437b4d7a0eff38282a049fd\state.vscdb'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get current selectedTools or create default structure
cursor.execute("SELECT value FROM ItemTable WHERE key = 'chat/selectedTools'")
result = cursor.fetchone()

if result:
    data = json.loads(result[0])
else:
    data = {
        'version': 2,
        'toolSetEntries': [],
        'toolEntries': []
    }

# Add st3-workflow MCP tools
st3_tools = [
    'mcp_st3-workflow_transition_phase',
    'mcp_st3-workflow_force_phase_transition',
    'mcp_st3-workflow_safe_edit_file',
    'mcp_st3-workflow_git_status',
    'mcp_st3-workflow_git_add_or_commit',
    'mcp_st3-workflow_git_checkout',
    'mcp_st3-workflow_git_restore',
    'mcp_st3-workflow_git_list_branches',
    'mcp_st3-workflow_close_issue',
    'mcp_st3-workflow_get_work_context',
    'mcp_st3-workflow_health_check',
    'mcp_st3-workflow_run_quality_gates',
    'mcp_st3-workflow_run_tests',
    'mcp_st3-workflow_scaffold_design_doc',
    'mcp_st3-workflow_search_documentation'
]

# Add each tool with true permission
for tool in st3_tools:
    # Check if tool already exists
    exists = False
    for entry in data['toolEntries']:
        if entry[0] == tool:
            entry[1] = True
            exists = True
            break
    if not exists:
        data['toolEntries'].append([tool, True])

# Update or insert
if result:
    cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'chat/selectedTools'", (json.dumps(data),))
else:
    cursor.execute("INSERT INTO ItemTable (key, value) VALUES ('chat/selectedTools', ?)", (json.dumps(data),))

conn.commit()
print(f'Added {len(st3_tools)} st3-workflow tools to whitelist')
conn.close()
