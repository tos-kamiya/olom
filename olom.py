import argparse
import curses
from dataclasses import dataclass, field
import random
import re
from typing import Any, Callable, List, Optional, Tuple

ColorPair = Any  # int or Tuple[int, int]

# Constants
FIELD_WIDTH = 10  # Width of the game field (number of columns)
PIECE_WIDTH = 3  # Width of each piece (number of blocks in a single piece)
PIECE_BLOCKS = 4  # Total number of blocks in a piece
MIN_RECT_WIDTH = 4  # Minimum width of a rectangle to clear

# Symbols for display
PIECE_PICTURE = dict(enumerate("0123456789X"))  # Active piece symbols
FIELD_PICTURE = dict(enumerate(".123456789X"))  # Static field symbols

# Game configuration
GAME_SPEED = 200  # Frame interval in milliseconds
MESSAGE_SHOW_DURATION = 15  # Duration for messages to be displayed (frames)

# Color configuration
BOLD_THRESHOLD = 7  # Threshold for bold display
ADDITIONAL_COLOR_PAIRS: List[ColorPair] = [
    (curses.COLOR_GREEN, curses.COLOR_BLACK),  # Active piece color
    (curses.COLOR_BLUE, curses.COLOR_BLACK),  # Next piece color
]


@dataclass
class GameState:
    """
    Represents the state of the game.

    Attributes:
        game_field (List[int]): The current state of the game field (columns).
        piece_queue (List[optional[List[int]]]): Queue of upcoming pieces.
        piece_col (int): Horizontal position of the active piece.
        piece_pos (int): Vertical position of the active piece.
        score (int): Current game score.
        piece_drop_pos (int): Starting vertical drop position of the active piece.
        pieces_dropped (int): Total number of pieces dropped.
    """

    game_field: List[int] = field(default_factory=lambda: [0] * FIELD_WIDTH)
    piece_queue: List[Optional[List[int]]] = field(default_factory=list)
    piece_col: int = 0
    piece_pos: int = 9
    score: int = 0
    piece_drop_pos: int = 9
    pieces_dropped: int = 0


@dataclass
class Message:
    """
    Represents a temporary message to be displayed in the game.

    Attributes:
        text (str): The message text to display.
        time_left (int): Remaining time (in frames) before the message disappears.
    """

    text: str = ""
    time_left: int = MESSAGE_SHOW_DURATION


def get_random_piece_generator(width: int, blocks: int) -> Callable[[], List[int]]:
    """
    Creates a random piece generator.

    Args:
        width (int): The width of the game field.
        blocks (int): The number of blocks in a single piece.

    Returns:
        Callable[[], List[int]]: A function that generates a random piece.
    """

    def gen_piece_random() -> List[int]:
        """
        Generate a new random piece.

        Returns:
            List[int]: A list representing the piece (block counts per column).
        """
        cells = [0] * width
        for _ in range(blocks):
            i = random.randrange(width)
            cells[i] += 1
        # Remove leading and trailing zeros
        while cells[0] == 0:
            cells.pop(0)
        while cells[-1] == 0:
            cells.pop()
        return cells

    return gen_piece_random


def get_pattern_piece_generator(
    piece_pattern: List[List[int]],
) -> Callable[[], List[int]]:
    """
    Creates a piece generator based on a predefined pattern.

    Args:
        piece_pattern (List[List[int]]): A list of pieces (each represented as a list of blocks).

    Returns:
        Callable[[], List[int]]: A function that generates pieces in a fixed pattern.
    """
    assert len(piece_pattern) > 0, "Piece pattern must not be empty."
    pattern_index = 0

    def gen_piece_pattern() -> List[int]:
        """
        Generate the next piece in the pattern.

        Returns:
            List[int]: The next piece in the pattern.
        """
        nonlocal pattern_index
        piece = piece_pattern[pattern_index]
        pattern_index = (pattern_index + 1) % len(piece_pattern)
        return piece

    return gen_piece_pattern


def scan_piece_pattern(pattern: str) -> List[List[int]]:
    """
    Parse a string representation of a piece pattern into a list of pieces.

    Args:
        pattern (str): A string representing the piece pattern (e.g., "202,112").

    Returns:
        List[List[int]]: A list of pieces, each represented as a list of blocks.
    """
    assert re.match(r"^[0-9,]+$", pattern) is not None, "Invalid pattern format."

    piece_strs = pattern.split(",")
    pieces = []
    for s in piece_strs:
        piece = list(map(int, s))
        assert sum(piece) > 0, "Empty piece detected in pattern."
        pieces.append(piece)

    return pieces


def find_rect(game_field: List[int], min_length: int) -> Optional[Tuple[int, int]]:
    """
    Find a rectangle (a series of consecutive blocks of the same figure) in the game field.

    Args:
        game_field (List[int]): The current state of the game field.
        min_length (int): The minimum length of a rectangle to find.

    Returns:
        Optional[tuple[int, int]]: The start and end indices of the rectangle, or None if not found.
    """
    for c in range(len(game_field) - min_length + 1):
        v = game_field[c]
        if v > 0:
            d = c
            while d < len(game_field) and game_field[d] == v:
                d += 1
            if d - c >= min_length:
                return c, d
    return None


def draw_game(
    stdscr: curses.window,
    mode: str,
    state: GameState,
    message: Optional[Message],
    grayscale: bool = False,
) -> None:
    """
    Draw the current game state on the screen.

    Args:
        stdscr (curses.window): The curses screen object for rendering the game.
        mode (str): Current game mode (e.g., "pat" for pattern mode).
        state (GameState): The current game state, including the field and piece positions.
        message (Optional[Message]): A message to display on the screen (e.g., score updates).
        grayscale (bool): Whether to draw in grayscale mode (used for game-over display).
    """
    stdscr.clear()

    # Determine the color pairs to use
    num_colors = 1 + len(ADDITIONAL_COLOR_PAIRS)
    if grayscale:
        # Grayscale mode: all colors default to color pair 0
        color_pairs = [curses.color_pair(0)] * num_colors
    else:
        # Normal mode: use predefined color pairs
        color_pairs = [curses.color_pair(i) for i in range(num_colors)]

    # Draw the game mode at the top-left corner
    col = 0
    if mode:
        stdscr.addstr(0, col, mode)
        col += len(mode) + 1

    # Draw the next two pieces in the queue
    for i in range(2, 0, -1):
        piece = state.piece_queue[i]
        if piece is None:
            continue
        for v in piece:
            stdscr.addstr(0, col, PIECE_PICTURE[v], color_pairs[2])
            col += 1
        # Fill remaining space for alignment
        remaining_space = PIECE_WIDTH - len(piece)
        if remaining_space > 0:
            stdscr.addstr(0, col, " " * remaining_space)
            col += remaining_space
        col += 1

    # Draw the game field and the active piece
    draw_field(stdscr, state, col, color_pairs)

    # Draw the active piece's vertical position
    stdscr.addstr(0, col + FIELD_WIDTH + 1, f"{state.piece_pos}", color_pairs[1])

    # Draw the score or message
    if message is not None:
        stdscr.addstr(0, col + FIELD_WIDTH + 3, message.text)
    else:
        stdscr.addstr(0, col + FIELD_WIDTH + 3, f"S: {state.score}")

    stdscr.refresh()


def draw_field(
    stdscr: curses.window,
    state: GameState,
    col_offset: int,
    color_pairs: List[ColorPair],
) -> None:
    """
    Helper function to draw the game field and the active piece.

    Args:
        stdscr (curses.window): The curses screen object.
        state (GameState): The current game state, including the field and piece positions.
        col_offset (int): The horizontal offset for drawing the field.
        color_pairs (List[ColorPair]): Predefined color pairs for rendering.
    """
    for c in range(FIELD_WIDTH):
        # Determine if the current column is part of the active piece
        if state.piece_queue[
            0
        ] is not None and state.piece_col <= c < state.piece_col + len(
            state.piece_queue[0]
        ):
            # Active piece being placed
            v = state.game_field[c] + state.piece_queue[0][c - state.piece_col]
            attr = color_pairs[1] | (curses.A_BOLD if v >= BOLD_THRESHOLD else 0)
            stdscr.addstr(0, col_offset + c, PIECE_PICTURE.get(v, "*"), attr)
        else:
            # Static field values
            v = state.game_field[c]
            attr = color_pairs[0] | (curses.A_BOLD if v >= BOLD_THRESHOLD else 0)
            stdscr.addstr(0, col_offset + c, FIELD_PICTURE.get(v, "*"), attr)


def fix_piece(state: GameState) -> None:
    """
    Fix the active piece in the game field once it reaches the bottom.

    Args:
        state (GameState): The current game state.
    """
    piece_queue = state.piece_queue
    if piece_queue[0] is not None:
        for c in range(FIELD_WIDTH):
            if state.piece_col <= c < state.piece_col + len(piece_queue[0]):
                # Add the active piece's blocks to the game field
                state.game_field[c] += piece_queue[0][c - state.piece_col]


def clear_rects(state: GameState) -> Optional[Message]:
    """
    Clear rectangles (consecutive blocks of the same value) from the game field.

    Args:
        state (GameState): The current game state.

    Returns:
        Optional[Message]: A message showing the score gained, or None if no rectangles were cleared.
    """
    game_field = state.game_field

    rect_found = False
    message_text = ""
    while True:
        r = find_rect(game_field, MIN_RECT_WIDTH)
        if r is None:
            break

        rect_found = True
        c, d = r
        num = game_field[c]

        # Clear the rectangle
        for j in range(c, d):
            game_field[j] = 0

        # Calculate and update the score
        width = d - c - MIN_RECT_WIDTH + 1
        score_add = num * width**3
        state.score += score_add
        message_text += f"+{score_add} "

    if rect_found:
        # Apply gravity to the game field
        for i in range(len(game_field)):
            if game_field[i] > 0:
                game_field[i] -= 1

    return Message(text=message_text.strip()) if message_text else None


def check_game_over(game_field: List[int]) -> bool:
    """
    Check if the game is over.

    Args:
        game_field (List[int]): The game field.

    Returns:
        bool: True if the game is over, False otherwise.
    """
    return any(v >= 11 for v in game_field)


def update_game(
    state: GameState, key: int, clock_tick: int, piece_generator
) -> Optional[Message]:
    """
    Update the game state based on user input and the game clock.

    Args:
        state (GameState): The current game state.
        key (int): The key pressed by the user.
        clock_tick (int): The current game clock tick.

    Returns:
        Optional[Message]: A message representing the result of the update, or None.
    """
    message = None

    piece_queue = state.piece_queue
    if piece_queue[0] is not None:
        # Handle user input for moving or dropping the piece
        if key in [curses.KEY_LEFT, ord("a")] and state.piece_col > 0:  # Move left
            state.piece_col -= 1
        elif key in [
            curses.KEY_RIGHT,
            ord("d"),
        ] and state.piece_col < FIELD_WIDTH - len(
            piece_queue[0]
        ):  # Move right
            state.piece_col += 1
        elif key in [curses.KEY_DOWN, ord("s")]:  # Drop piece immediately
            state.piece_pos = 0

    # Handle automatic piece movement based on clock
    if clock_tick % 5 == 0:
        if piece_queue[0] is None:
            # Load the next piece from the queue and generate a new piece
            piece_queue.pop(0)
            piece_queue.append(piece_generator())
            state.piece_col = 0
            state.piece_pos = state.piece_drop_pos
        else:
            if state.piece_pos == 0:  # Piece has reached the bottom
                fix_piece(state)
                message = clear_rects(state)
                piece_queue[0] = None  # Mark the active piece as "used"
                state.pieces_dropped += 1

                # Adjust drop position speed after every 80 pieces
                if state.pieces_dropped % 80 == 0 and state.piece_drop_pos >= 5:
                    state.piece_drop_pos -= 1
            else:
                state.piece_pos -= 1  # Move piece down by one step

    return message


def update_message(message: Optional[Message]) -> Optional[Message]:
    """
    Update the message state (reduce its time left).

    Args:
        message (Optional[Message]): The current message.

    Returns:
        Optional[Message]: The updated message (or None if time has expired).
    """
    if message is not None:
        if message.time_left > 0:
            message.time_left -= 1
            if message.time_left == 0:
                message = None
    return message


@dataclass
class Config:
    mode: str = ""
    piece_generator: Optional[Callable[[], List[int]]] = None


config = Config()


def curses_main(stdscr) -> None:
    """
    Main game loop.

    Args:
        stdscr: The curses screen object.
    """
    # Initialize curses settings
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(GAME_SPEED)

    # Initialize color pairs
    curses.start_color()
    for i, (fg, bg) in enumerate(ADDITIONAL_COLOR_PAIRS):
        curses.init_pair(i + 1, fg, bg)

    clock_tick = 0  # Game clock tick counter

    # Initialize game state
    pg = config.piece_generator
    assert pg is not None
    state: GameState = GameState(piece_queue=[pg(), pg(), pg()])
    message: Optional[Message] = None

    # Main game loop
    while True:
        # Draw the game state
        draw_game(stdscr, config.mode, state, message)

        # Check for game over
        if check_game_over(state.game_field):
            break

        clock_tick += 1

        # Handle user input
        key = stdscr.getch()
        if key == 27 or key == ord("q"):  # Exit if ESC or 'q' is pressed
            return

        # Update the message state
        message = update_message(message)

        # Update the game state
        m = update_game(state, key, clock_tick, pg)
        if m is not None:
            message = m

    # Game over screen
    while True:
        draw_game(stdscr, config.mode, state, message, grayscale=True)

        # Update the message state
        message = update_message(message)

        # Wait for user to exit
        key = stdscr.getch()
        if key == 27 or key == ord("q"):  # Exit if ESC or 'q' is pressed
            return


def main():
    parser = argparse.ArgumentParser(description="One-Line Otimono Game")
    parser.add_argument(
        "--piece-pattern", "-p", type=str, help='Piece pattern (e.g. "202,112").'
    )
    args = parser.parse_args()

    if args.piece_pattern is not None:
        piece_pattern = scan_piece_pattern(args.piece_pattern)
        config.piece_generator = get_pattern_piece_generator(piece_pattern)
        config.mode = "pat"
    else:
        config.piece_generator = get_random_piece_generator(PIECE_WIDTH, PIECE_BLOCKS)

    curses.wrapper(curses_main)


if __name__ == "__main__":
    main()
