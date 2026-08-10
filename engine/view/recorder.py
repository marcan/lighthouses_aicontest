import bz2
import gzip
import json
import os
import pathlib
import pickle
import tempfile
import time

from engine import Game
from view.api import GameView

recorder_file_path = (os.getenv('AICONTEST_RECORDER_OUTPUT') or
                      str(pathlib.Path(tempfile.gettempdir()).joinpath('last-game.jsonl.gz')))


class RecorderGameView(GameView):
    """A utility to record and play back games, implemented as a GameView.

    Select it to record a game and execute this file to replay it.

    Note that this saves internal data structures, so it may not be compatible with future versions of the game engine.
    """

    def __init__(self, game: Game):
        super().__init__(game)

        # Connect to the output
        if recorder_file_path.startswith('tcp://'):
            import socket  # Useful for real-time playback with an external viewer
            host, port = recorder_file_path.split('/')[2].split(':')
            self.f = socket.create_connection((host, int(port)))
        elif recorder_file_path.endswith('.gz'):
            self.f = gzip.GzipFile(recorder_file_path, 'wb')
        else:
            self.f = open(recorder_file_path, 'wb')

        # Json lines is much more compatible with external tools,
        # but pickle is lossless (meaning that it can replay using the embedded viewer)
        self.is_jsonl = '.jsonl' in recorder_file_path

        # Save the initial state
        self.update(0)

    def update(self, game_round: int):
        self.game.round = game_round
        if self.is_jsonl:
            safe_json = class_to_safe_json(self.game)
            self.f.write(json.dumps(safe_json).encode('utf-8'))
            self.f.write(b'\n')
        else:
            pickle.dump(self.game, self.f)

    def __del__(self):
        self.f.close()
        print('Game recorded to', recorder_file_path)


def class_to_safe_json(obj: any, visited=None, path="/") -> any:
    if visited is None:
        visited = {}

    obj_id = id(obj)
    if obj_id in visited:
        return {'__cycle__': visited[obj_id]}

    if isinstance(obj, (list, tuple, set, frozenset)):
        return [class_to_safe_json(_v, visited, f"{path}[{i}]") for i, _v in enumerate(obj)]

    if not hasattr(obj, "__dict__"):
        return obj  # If it's not an object with __dict__, return the object itself

    visited[obj_id] = path

    result = {}
    for key, value in obj.__dict__.items():
        new_path = f"{path}{key}"
        # print(new_path, '==>', value)
        if isinstance(value, (list, tuple, set, frozenset)):
            result[key] = list(class_to_safe_json(_v, visited, f"{new_path}[{i}]/") for i, _v in enumerate(value))
        elif isinstance(value, dict):
            result[key] = \
                {str(_k): class_to_safe_json(_v, visited, f"{new_path[:-1]}/{_k}/") for _k, _v in value.items()}
        else:
            result[key] = class_to_safe_json(value, visited, f"{new_path}/")

    return result


if __name__ == '__main__':
    from view.api import get_game_view

    if '.jsonl' in recorder_file_path:
        raise ValueError('Cannot replay a jsonl file directly. Use the pickle format instead.')

    replay_sleep_ms = int(os.getenv('AICONTEST_RECORDER_REPLAY_SLEEP_MS', '100'))

    f = bz2.BZ2File(recorder_file_path, 'rb')

    # Create the initial game and view
    g = pickle.load(f)
    view = get_game_view(g)

    # Replay the game
    last_round = 0
    while True:
        try:
            game2 = pickle.load(f)
        except EOFError:
            break

        # Need to "copy" the attributes because the view holds the original game reference
        for k, v in game2.__dict__.items():
            setattr(g, k, v)

        if g.round != last_round:  # New round, sleep before updating the view
            time.sleep(replay_sleep_ms / 100000)
            last_round = g.round

        view.update(g.round)
