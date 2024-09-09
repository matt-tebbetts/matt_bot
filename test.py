import os
import json

print("Script started")

def try_read_json(file_path, encoding):
    print(f"Attempting to read with {encoding} encoding")
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            content = file.read()
            print(f"Successfully read file with {encoding} encoding")
            print("File contents:")
            print(content)
            data = json.loads(content)
            print(f"Successfully parsed JSON")
            print(f"Number of items in JSON: {len(data)}")
            print("JSON structure:")
            print(json.dumps(data, indent=2))
            return True
    except UnicodeDecodeError as e:
        print(f"Failed to read file with {encoding} encoding: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON with {encoding} encoding: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def main():
    print("Entering main function")
    # Construct the path to games.json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    games_file_path = os.path.abspath(os.path.join(current_dir, 'files', 'games.json'))

    print(f"Attempting to read: {games_file_path}")

    if not os.path.exists(games_file_path):
        print(f"Error: File does not exist at {games_file_path}")
        return

    print("\nTrying UTF-8 encoding:")
    utf8_success = try_read_json(games_file_path, 'utf-8')

    if not utf8_success:
        print("\nTrying ISO-8859-1 encoding:")
        iso_success = try_read_json(games_file_path, 'iso-8859-1')

        if not iso_success:
            print("\nFailed to read file with both UTF-8 and ISO-8859-1 encodings")

if __name__ == "__main__":
    main()
    print("Script finished")