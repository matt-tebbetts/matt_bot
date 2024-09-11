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