from pathlib import Path
import json
import os

ipc_file = Path.home() / 'AppData' / 'Local' / 'EdgeDLP' / 'extension_status.json'
print(f'IPC file path: {ipc_file}')
print(f'Directory exists: {ipc_file.parent.exists()}')
print(f'File exists: {ipc_file.exists()}')

if ipc_file.exists():
    try:
        with open(ipc_file, 'r') as f:
            content = json.load(f)
        print(f'Content: {content}')
    except Exception as e:
        print(f'Error reading file: {e}')
else:
    print('File does not exist')

