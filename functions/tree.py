import os

def print_tree(dir_path, indent="", file=None):
    # Get a list of items in the current directory, excluding files/folders starting with "." or "_"
    with os.scandir(dir_path) as entries:
        # Filter out files and directories starting with "." or "_"
        items = [entry for entry in entries if not entry.name.startswith('.') and not entry.name.startswith('_')]
        
        # Iterate through each item
        for idx, item in enumerate(items):
            # Print folder structure with indentation
            connector = "├── " if idx < len(items) - 1 else "└── "
            file.write(f"{indent}{connector}{item.name}\n")
            
            # If it's a directory, recurse into it
            if item.is_dir():
                sub_indent = "│   " if idx < len(items) - 1 else "    "
                print_tree(item.path, indent + sub_indent, file)

# Ensure the directory exists
output_dir = os.path.join(os.getcwd(), "../files")
os.makedirs(output_dir, exist_ok=True)

# Create or open the file structure.txt for writing
output_file_path = os.path.join(output_dir, "tree.txt")
with open(output_file_path, "w", encoding='utf-8') as f:
    print_tree(os.getcwd(), file=f)
print("Directory structure written to ../files/tree.txt")
