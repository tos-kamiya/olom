import curses
import random
from dataclasses import dataclass, field
from typing import List, Optional

# Constants
FIELD_WIDTH = 10  # Width of the game field
PIECE_WIDTH = 3   # Width of each piece
PIECE_SIZE = 4    # Number of blocks in a piece
MIN_RECT_WIDTH = 4  # Minimum width of a rectangle to be cleared

# Symbols for display
PIECE_PICTURE = dict(enumerate("0123456789X"))
FIELD_PICTURE = dict(enumerate(".123456789X"))

# Game configuration
GAME_SPEED = 200  # Frame interval in milliseconds
MESSAGE_SHOW_DURATION = 15  # Duration for messages to be displayed

# Color configuration
BOLD_THRESHOLD = 7
ADDITIONAL_COLOR_PAIRS = [
    (curses.COLOR_GREEN, curses.COLOR_BLACK),  # Active piece color
    (curses.COLOR_BLUE, curses.COLOR_BLACK),   # Next piece color
]

@dataclass
class GameState:
    """
    Represents the state of the game.
    """
    game_field: List[int] = field(default_factory=lambda: [0] * FIELD_WIDTH)
    piece_queue: List[Optional[List[int]]] = field(default_factory=list)  # Queue of upcoming pieces
    piece_col: int = 0  # Current horizontal position of the active piece
    piece_pos: int = 9  # Current vertical position of the active piece
    score: int = 0  # Current score
    piece_drop_pos: int = 9  # Starting drop position
    pieces_dropped: int = 0  # Total number of dropped pieces


@dataclass
class Message:
    """
    Represents a temporary message to be displayed in the game.
    """
    text: str = ""  # The message text
    time_left: int = MESSAGE_SHOW_DURATION  # Remaining time before the message disappears


def generate_piece() -> List[int]:
    """
    Generate a new random piece.

    Returns:
        List[int]: A list representing the piece.
    """
    cells = [0] * PIECE_WIDTH
    for _ in range(PIECE_SIZE):
        i = random.randrange(PIECE_WIDTH)
        cells[i] += 1
    while cells[0] == 0:
        cells.pop(0)
    while cells[-1] == 0:
        cells.pop()
    return cells


def find_rect(game_field: List[int], min_length: int) -> Optional[tuple[int, int]]:
    """
    Find a rectangle (a series of consecutive blocks of the same figure) in the game field.

    Args:
        game_field (List[int]): The game field.
        min_length (int): The minimum length of a rectangle to find.

    Returns:
        Optional[tuple[int, int]]: Start and end indices of the rectangle, or None if not found.
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


def draw_game(stdscr, state: GameState, message: Optional[Message], grayscale: bool = False) -> None:
    """
    Draw the current game state.

    Args:
        stdscr: The curses screen object.
        state (GameState): The current game state.
        message (Optional[Message]): A message to display, if any.
        grayscale (bool): Whether to draw in grayscale mode (for game over).
    """
    stdscr.clear()

    num_colors = 1 + len(ADDITIONAL_COLOR_PAIRS)
    if grayscale:
        color_pairs = [curses.color_pair(0)] * num_colors
    else:
        color_pairs = [curses.color_pair(i) for i in range(num_colors)]

    col = 0
    piece_queue = state.piece_queue

    # Draw the next two pieces
    for i in range(2, 0, -1):
        piece = piece_queue[i]
        if piece is None:
            continue
        for v in piece:
            stdscr.addstr(0, col, PIECE_PICTURE[v], color_pairs[2])
            col += 1
        r = PIECE_WIDTH - len(piece)
        if r > 0:
            stdscr.addstr(0, col, " " * r)
            col += r
        col += 1

    # Draw the field and the active piece
    for c in range(FIELD_WIDTH):
        if piece_queue[0] is not None and state.piece_col <= c < state.piece_col + len(piece_queue[0]):
            # Active piece being placed
            v = state.game_field[c] + piece_queue[0][c - state.piece_col]
            attr = color_pairs[1] | (curses.A_BOLD if v >= BOLD_THRESHOLD else 0)
            stdscr.addstr(0, col + c, PIECE_PICTURE.get(v, "*"), attr)
        else:
            # Static field values
            v = state.game_field[c]
            attr = color_pairs[0] | (curses.A_BOLD if v >= BOLD_THRESHOLD else 0)
            stdscr.addstr(0, col + c, FIELD_PICTURE.get(v, "*"), attr)
    col += FIELD_WIDTH + 1

    # Draw the piece position
    stdscr.addstr(0, col, f"{state.piece_pos}", color_pairs[1])
    col += 2

    # Draw the score or message
    if message is not None:
        stdscr.addstr(0, col, message.text)
    else:
        stdscr.addstr(0, col, f"S: {state.score}")

    stdscr.refresh()


def fix_piece(state: GameState) -> None:
    """
    Fix active piece in the game field.

    Args:
        state (GameState): The current game state.
    """
    piece_queue = state.piece_queue
    if piece_queue[0] is not None:
        for c in range(FIELD_WIDTH):
            if state.piece_col <= c < state.piece_col + len(piece_queue[0]):
                state.game_field[c] += piece_queue[0][c - state.piece_col]


def clear_rects(state: GameState) -> Optional[Message]:
    """
    Clear rectangles (rectangles of consecutive blocks) from the game field.

    Args:
        state (GameState): The current game state.

    Returns:
        Optional[Message]: A message representing the score gained, or None if no rectangles were cleared.
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

        for j in range(c, d):
            game_field[j] = 0

        w = d - c - MIN_RECT_WIDTH + 1
        score_add = num * w ** 3
        state.score += score_add
        message_text += f"+{score_add}"

    if rect_found:
        for i in range(len(game_field)):
            if game_field[i] > 0:
                game_field[i] -= 1

    if message_text:
        return Message(text=message_text)


def check_game_over(game_field: List[int]) -> bool:
    """
    Check if the game is over.

    Args:
        game_field (List[int]): The game field.

    Returns:
        bool: True if the game is over, False otherwise.
    """
    return any(v >= 11 for v in game_field)


def update_game(state: GameState, key: int, clock_tick: int) -> Optional[Message]:
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
        if key in [curses.KEY_LEFT, ord('a')] and state.piece_col > 0:  # Move left
            state.piece_col -= 1
        elif key in [curses.KEY_RIGHT, ord('d')] and state.piece_col < FIELD_WIDTH - len(piece_queue[0]):  # Move right
            state.piece_col += 1
        elif key in [curses.KEY_DOWN, ord('s')]:  # Drop piece immediately
            state.piece_pos = 0

    # Handle automatic piece movement based on clock
    if clock_tick % 5 == 0:
        if piece_queue[0] is None:
            # Load the next piece from the queue and generate a new piece
            piece_queue.pop(0)
            piece_queue.append(generate_piece())
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
    state: GameState = GameState(
        piece_queue=[generate_piece(), generate_piece(), generate_piece()]
    )
    message: Optional[Message] = None

    # Main game loop
    while True:
        # Draw the game state
        draw_game(stdscr, state, message)

        # Check for game over
        if check_game_over(state.game_field):
            break

        clock_tick += 1

        # Handle user input
        key = stdscr.getch()
        if key == 27 or key == ord('q'):  # Exit if ESC or 'q' is pressed
            return

        # Update the message state
        message = update_message(message)

        # Update the game state
        m = update_game(state, key, clock_tick)
        if m is not None:
            message = m

    # Game over screen
    while True:
        draw_game(stdscr, state, message, grayscale=True)

        # Wait for user to exit
        key = stdscr.getch()
        if key == 27 or key == ord('q'):  # Exit if ESC or 'q' is pressed
            return


# Run the game using curses
def main():
    curses.wrapper(curses_main)


if __name__ == "__main__":
    main()
