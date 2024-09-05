from pathlib import Path

def print_tree(dir_path, indent="", file=None):
    for item in dir_path.iterdir():
        if item.name.startswith('.') or item.name.startswith('_'):
            continue
        connector = "├── " if item != list(dir_path.iterdir())[-1] else "└── "
        file.write(f"{indent}{connector}{item.name}\n")
        if item.is_dir():
            sub_indent = "│   " if item != list(dir_path.iterdir())[-1] else "    "
            print_tree(item, indent + sub_indent, file)

# Get the absolute path of the project root
project_root = Path(__file__).parent.parent

# Define paths relative to the project root
output_file_path = project_root / 'files' / 'structure.txt'

# Ensure the output file is written to the "files" folder
with open(output_file_path, "w", encoding="utf-8") as f:
    print_tree(Path.cwd(), file=f)

print(f"Directory structure written to {output_file_path}")
