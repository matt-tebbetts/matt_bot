from pathlib import Path

def get_project_root(project_root_name="Matt_Bot"):
    """Finds the project root by searching for the folder name."""
    current_dir = Path(__file__).resolve().parent
    for parent in current_dir.parents:
        if parent.name == project_root_name:
            return parent
    raise RuntimeError(f"Project root folder '{project_root_name}' not found")
