import json
import os

# get game prefixes
def get_game_prefixes():

    # find games.json
    games_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'files', 'games.json'))

    # load
    with open(games_file_path, 'r') as file:
        games_data = json.load(file)
    game_prefixes = [game["prefix"] for game in games_data["games"].values()]
    return game_prefixes
