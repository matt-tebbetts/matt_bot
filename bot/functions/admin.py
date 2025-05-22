import os
import json

# read json
def read_json(filepath, default_data=[]):

    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(filepath, 'w') as file:
            json.dump(default_data, file)
        return default_data

# write json
def write_json(filepath, data):
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w') as file:
        json.dump(data, file, indent=4)

# get default channel id
def get_default_channel_id(guild_name):
    config_path = f"files/guilds/{guild_name}/config.json"
    try:
        config = read_json(config_path)
        channel_id = config.get("default_channel_id")
        if channel_id is not None:
            return int(channel_id)
        else:
            print(f"admin.py: default_channel_id not found in config.json for guild '{guild_name}'")
    except FileNotFoundError:
        print(f"admin.py: config.json not found for guild '{guild_name}'")
    except json.JSONDecodeError:
        print(f"admin.py: Error decoding config.json for guild '{guild_name}'")
    except ValueError:
        print(f"admin.py: Invalid channel ID in config.json for guild '{guild_name}'")
    return None

def direct_path_finder(*relative_path_parts: str) -> str:
    """
    Constructs an absolute path by joining the project root directory with the relative path parts.

    :param relative_path_parts: The parts of the relative path to join.
    :return: The absolute path.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(project_root, *relative_path_parts)