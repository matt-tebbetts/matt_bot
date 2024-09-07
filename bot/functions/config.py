import json
import os

# get game prefixes
def get_game_info():

    # find games.json
    games_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'files', 'games.json'))

    # load
    with open(games_file_path, 'r') as file:
        games_data = json.load(file)
    
    game_info = {}
    for game_name, game_data in games_data["games"].items():
        game_info[game_data["prefix"].lower()] = {
            "game_name": game_name,
            "emoji": game_data.get("emoji", ""),
            "scoring_type": game_data.get("scoring_type", ""),
            "bonuses": game_data.get("bonuses", {})
        }
        print(f"game name is {game_name} and game_data is {game_data}")
        print(f"game_info is {game_info}")
    return game_info

get_game_info()