import os
from pathlib import Path

# List potential alternative path formats
dir_paths = [
    r"c:\Users\Emmanuel Anthony\OneDrive\Documenti\PythonProjects\petroleum-data-ai\data\raw",
    r"c:\Users\EMMANU~1\OneDrive\Documenti\PythonProjects\petroleum-data-ai\data\raw",
    r"c:\Users\EmmanuelAnthony\OneDrive\Documenti\PythonProjects\petroleum-data-ai\data\raw",
]

# Check each directory for the file
found = False
for dir_path in dir_paths:
    path = Path(dir_path)
    if path.exists():
        file_path = path / "Volve production data.xlsx"
        if file_path.exists():
            print(f"File found at: {file_path}")
            found = True
            break
        else:
            print(f"Directory found but no Excel file: {dir_path}")

if not found:
    print("Could not locate the file. Please make sure it's placed in data/raw/")