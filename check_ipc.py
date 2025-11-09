from pathlib import Path
import json

ipc_file = Path.home() / 'AppData' / 'Local' / 'EdgeDLP' / 'extension_status.json'

print(f'IPC file path: {ipc_file}')
print(f'IPC file exists: {ipc_file.exists()}')
print(f'Parent directory exists: {ipc_file.parent.exists()}')

if ipc_file.exists():
    try:
        with open(ipc_file, 'r') as f:
            content = json.load(f)
            print(f'Content: {content}')
            print(f'Is risky domain: {content.get("is_risky_domain", False)}')
            print(f'Hostname: {content.get("hostname", "")}')
            print(f'Timestamp: {content.get("timestamp", 0)}')
    except Exception as e:
        print(f'Error reading IPC file: {e}')
else:
    print('IPC file does not exist - native host may not have written it yet')

