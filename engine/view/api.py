import os

from engine import Game


def get_game_view(game: Game):
    """Get the game view object for the given game object."""
    selected_viewer = os.getenv('AICONTEST_VIEW', 'pygame')

    if 'pygame' in selected_viewer:  # Simple 2D Viewer
        from view.pygameview import PygameView
        return PygameView(game)
    elif 'recorder' in selected_viewer:  # Record and replay viewer
        from view.recorder import RecorderGameView
        return RecorderGameView(game)
    else:
        raise ValueError('Unknown viewer: ' + selected_viewer)


class GameView:
    """The game view interface."""

    game: Game
    """The game object that this view is observing."""

    def __init__(self, game: Game):
        """Initialize the game view from a game object."""
        self.game = game

    def update(self, game_round: int):
        """Update the game view at the start of a new round and after any player makes a move (several times per round).

        You can read the new state from self.game. This call should not block."""
        pass
