from pathlib import Path

def print_tree(dir_path, indent="", file=None):
    items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    for index, item in enumerate(items):
        if item.name.startswith('.') or item.name.startswith('_'):
            continue
        connector = "├── " if index != len(items) - 1 else "└── "
        file.write(f"{indent}{connector}{item.name}\n")
        if item.is_dir():
            sub_indent = "│   " if index != len(items) - 1 else "    "
            print_tree(item, indent + sub_indent, file)

# Get the absolute path of the project root (now we're in bot/functions/)
project_root = Path(__file__).parent.parent.parent

# Define paths relative to the project root
output_file_path = project_root / 'files' / 'images' / 'tree.txt'

# Ensure the output file is written to the "files" folder
with open(output_file_path, "w", encoding="utf-8") as f:
    print_tree(project_root, file=f)

print(f"Directory structure written to {output_file_path}")