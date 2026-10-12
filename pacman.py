#/usr/bin/env python3
"""
PAC-MAN Terminal Arcade
A feature-complete, zero-dependency Python implementation of the classic Pac-man arcade game.
Engineered for Linux, macOS, and Windows terminals with ANSI color suport.
"""

import sys
import os 
import time
import math
import random
import json
import signal
import shutil
from typing import List, Tuple, Dict, Optional, Set

# ======================================================================
# CONSTANTS & CONFIGURATION
# ======================================================================

# Directions as (dx,dy)
DIR_UP = (0, -1)
DIR_DOWN = (0, 1)
DIR_LEFT = (-1, 0)
DIR_RIGHT = (1, 0)
DIR_NONE = (0, 0)

OPPOSITE_DIR = {
    DIR_UP: DIR_DOWN,
    DIR_DOWN: DIR_UP,
    DIR_LEFT: DIR_RIGHT,
    DIR_RIGHT: DIR_LEFT,
    DIR_NONE: DIR_NONE,
}

#Ghost Personalities / types
GHOST_BLINKY = "Blinky" # Red - The Chaser ("Shadow")
GHOST_PINKY = "Pinky" # Pink - The Ambusher ("Speedy")
GHOST_INKY = "Inky" # Cyan - The Flanker ("Bashful")
GHOST_CLYDE = "Clyde" # Orange - The Coward ("Pokey")

# Ghost States
MODE_SCATTER = "SCATTER" 
MODE_CHASE = "CHASE"
MODE_FRIGHTENED = "FRIGHTENED"
MODE_EATEN = "EATEN"

# ANSI Colors
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"

COLOR_BLUE = "\033[38;5;33m"   # Neon blue walls
COLOR_DOOR = "\033[38;5;218m"  # Ghost house door
COLOR_YELLOW = "\033[38;5;226m" # Pac-Man & energizer
COLOR_PELLET = "\033[38;5;222m" # Pale warm pellet
COLOR_RED = "\033[38;5;196m" # Blinky
COLOR_PINK = "\033[38;5;213m" # Pinky
COLOR_CYAN = "\033[38;5;51m" # Inky
COLOR_ORANGE = "\033[38;5;208m" # Clyde
COLOR_FRIGHT_BLUE = "\033[38;5;27m" # Frightened ghost
COLOR_FRIGHT_WHITE = "\033[38;5;231m" # Flashing white ghost
COLOR_EYES = "\033[38;5;231m" # Ghost eyes
COLOR_FRUIT = "\033[38;5;197m" #Fruit bonus
COLOR_WHITE = "\033[38;5;231m"
COLOR_SCORE = "\033[38;5;220m"

# Classic 28x31 Maze Layout
# '#' = Wall, '.' = Pellet, '*' = Energizer, ' ' = Empty path / House, '-' = Door
CLASSIC_MAZE = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#*####.#####.##.#####.####*#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.##### ## #####.######",
    "     #.##### ## #####.#     ",
    "     #.##          ##.#     ",
    "     #.## ###--### ##.#     ",
    "######.## #      # ##.######",
    "      .   #      #   .      ",
    "######.## #      # ##.######",
    "     #.## ######## ##.#     ",
    "     #.##          ##.#     ",
    "     #.## ######## ##.#     ",
    "######.## ######## ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#.####.#####.##.#####.####.#",
    "#*..##................##..*#",
    "###.##.##.########.##.##.###",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
]

# Fruits by level
FRUIT_TYPES =[
    ("Cheery","🍒", 100),
    ("Strawberry","🍓", 300),
    ("Orange","🍊", 500),
    ("Apple","🍎", 700),
    ("Melon", "🍈", 1000),
    ("Galaxian", "🛸", 2000),
    ("Bell", "🔔", 3000),
    ("Key", "🔑", 5000),
]
HIGHSCORE_FILE = os.path.expanduser("~/.pacman_terminal_highscore.json")


# ==============================================================================
# TERMINAL CONTROLLER
# ==============================================================================

class TerminalController:
    """Manages raw terminal mode, non-blocking keyboard input, and ANSI output."""
    def __init__(self, force_ascii: bool = False, enable_sound: bool = False):
        self.is_windows = (os.name == "nt")
        self.force_ascii = force_ascii
        self.enable_sound = enable_sound
        self.old_settings = None
        self._active = False

    def enter(self):
        """Prepare terminal for full-screen game display and raw keyboard input."""
        self._active = True
        if not self.is_windows:
            try:
                import termios, tty
                self.old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except Exception:
                pass
        else:
            try:
                os.system("")  # Enable ANSI virtual terminal processing on Windows
            except Exception:
                pass

        sys.stdout.write("\033[?25l\033[2J\033[H")
        sys.stdout.flush()

    def exit(self):
        """Restore normal terminal settings and show cursor."""
        if not self._active:
            return
        self._active = False
        sys.stdout.write(f"{COLOR_RESET}\033[?25h\033[2J\033[H")
        sys.stdout.flush()

        if not self.is_windows and self.old_settings:
            try:
                import termios
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass

    def get_key(self) -> Optional[str]:
        """Poll for a single keypress without blocking."""
        if self.is_windows:
            import msvcrt
            if msvcrt.kbhit():
                b = msvcrt.getch()
                if b in (b"\x00", b"\xe0"):
                    b2 = msvcrt.getch()
                    if b2 == b"H": return "UP"
                    elif b2 == b"P": return "DOWN"
                    elif b2 == b"K": return "LEFT"
                    elif b2 == b"M": return "RIGHT"
                else:
                    return b.decode("latin1", errors="ignore")
            return None
        else:
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    r, _, _ = select.select([sys.stdin], [], [], 0.04)
                    if r:
                        seq = sys.stdin.read(2)
                        if seq == "[A": return "UP"
                        elif seq == "[B": return "DOWN"
                        elif seq == "[C": return "RIGHT"
                        elif seq == "[D": return "LEFT"
                    return "ESC"
                return ch
            return None

    def bell(self):
        """Emit terminal sound if enabled."""
        if self.enable_sound:
            sys.stdout.write("\a")
            sys.stdout.flush()

    def render(self, buffer_str: str):
        """Double-buffered screen refresh without clearing flicker."""
        sys.stdout.write(f"\033[H{buffer_str}")
        sys.stdout.flush()


# ==============================================================================
# GAME ENTITIES
# ==============================================================================

class Pacman:
    def __init__(self, start_x: int = 13, start_y: int = 23):
        self.start_pos = (start_x, start_y)
        self.x = start_x
        self.y = start_y
        self.dir = DIR_LEFT
        self.desired_dir = DIR_LEFT
        self.speed = 8.5
        self.move_accumulator = 0.0
        self.mouth_open = True
        self.mouth_timer = 0.0
        self.alive = True

    def reset(self):
        self.x, self.y = self.start_pos
        self.dir = DIR_LEFT
        self.desired_dir = DIR_LEFT
        self.move_accumulator = 0.0
        self.mouth_open = True
        self.mouth_timer = 0.0
        self.alive = True

    def update_animation(self, dt: float):
        self.mouth_timer += dt
        if self.mouth_timer >= 0.14:
            self.mouth_timer = 0.0
            self.mouth_open = not self.mouth_open


class Ghost:
    def __init__(self, name: str, home_tile: Tuple[int, int], scatter_corner: Tuple[int, int],
                 start_pos: Tuple[int, int], start_in_house: bool, release_delay: float):
        self.name = name
        self.home_tile = home_tile
        self.scatter_corner = scatter_corner
        self.start_pos = start_pos
        self.start_in_house = start_in_house
        self.release_delay = release_delay

        self.x, self.y = start_pos
        self.dir = DIR_UP if start_in_house else DIR_LEFT
        self.mode = MODE_SCATTER
        self.in_house = start_in_house
        self.house_timer = 0.0
        self.speed = 7.5
        self.move_accumulator = 0.0
        self.target = scatter_corner

    def reset(self):
        self.x, self.y = self.start_pos
        self.dir = DIR_UP if self.start_in_house else DIR_LEFT
        self.mode = MODE_SCATTER
        self.in_house = self.start_in_house
        self.house_timer = 0.0
        self.move_accumulator = 0.0
        self.target = self.scatter_corner


# ==============================================================================
# MAIN GAME ENGINE
# ==============================================================================

class PacmanGame:
    def __init__(self, force_ascii: bool = False, fps: int = 20, enable_sound: bool = False):
        self.terminal = TerminalController(force_ascii=force_ascii, enable_sound=enable_sound)
        self.fps = fps
        self.dt = 1.0 / fps
        self.force_ascii = force_ascii

        self.maze_height = len(CLASSIC_MAZE)
        self.maze_width = len(CLASSIC_MAZE[0])
        self.tunnel_row = 14
        self.house_entrance = (13, 11)
        self.house_interior = (13, 14)

        self.grid: List[List[str]] = []
        self.pellets_left = 0
        self.total_pellets = 0

        self.pacman = Pacman(13, 23)
        self.ghosts: Dict[str, Ghost] = {}
        self._init_ghosts()

        self.score = 0
        self.high_score = self.load_high_score()
        self.level = 1
        self.lives = 3
        self.game_over = False
        self.paused = False

        self.wave_timer = 0.0
        self.wave_index = 0
        self.waves = [
            (7.0, 20.0),
            (7.0, 20.0),
            (5.0, 20.0),
            (5.0, float("inf")),
        ]
        self.current_global_mode = MODE_SCATTER

        self.frightened_timer = 0.0
        self.frightened_duration = 7.0
        self.ghosts_eaten_combo = 0
        self.floating_scores: List[Dict] = []

        self.fruit_active = False
        self.fruit_timer = 0.0
        self.fruit_tile = (13, 17)
        self.fruit_spawned_count = 0

        self.state = "TITLE"
        self.state_timer = 0.0
        self.frame_count = 0

        self.reset_maze()

    def _init_ghosts(self):
        self.ghosts = {
            GHOST_BLINKY: Ghost(GHOST_BLINKY, (13, 11), (27, 0), (13, 11), False, 0.0),
            GHOST_PINKY: Ghost(GHOST_PINKY, (13, 14), (0, 0), (13, 14), True, 0.5),
            GHOST_INKY: Ghost(GHOST_INKY, (11, 14), (27, 30), (11, 14), True, 4.0),
            GHOST_CLYDE: Ghost(GHOST_CLYDE, (15, 14), (0, 30), (15, 14), True, 8.0),
        }

    def reset_maze(self):
        self.grid = []
        self.pellets_left = 0
        self.total_pellets = 0
        for row in CLASSIC_MAZE:
            row_chars = list(row)
            self.grid.append(row_chars)
            for c in row_chars:
                if c in (".", "*"):
                    self.pellets_left += 1
                    self.total_pellets += 1

    def reset_round_positions(self):
        self.pacman.reset()
        for g in self.ghosts.values():
            g.reset()
        self.wave_timer = 0.0
        self.wave_index = 0
        self.current_global_mode = MODE_SCATTER
        self.frightened_timer = 0.0
        self.ghosts_eaten_combo = 0
        self.floating_scores.clear()
        self.state = "READY"
        self.state_timer = 2.0

    def start_new_game(self):
        self.score = 0
        self.level = 1
        self.lives = 3
        self.game_over = False
        self.fruit_active = False
        self.fruit_spawned_count = 0
        self.reset_maze()
        self.reset_round_positions()

    def load_high_score(self) -> int:
        try:
            if os.path.exists(HIGHSCORE_FILE):
                with open(HIGHSCORE_FILE, "r") as f:
                    data = json.load(f)
                    return int(data.get("high_score", 0))
        except Exception:
            pass
        return 10000

    def save_high_score(self):
        try:
            with open(HIGHSCORE_FILE, "w") as f:
                json.dump({"high_score": self.high_score}, f)
        except Exception:
            pass

    def is_walkable(self, x: int, y: int, is_ghost: bool = False, allows_door: bool = False) -> bool:
        if y == self.tunnel_row:
            x = x % self.maze_width
        if not (0 <= y < self.maze_height and 0 <= x < self.maze_width):
            return False
        cell = self.grid[y][x]
        if cell == "#":
            return False
        if cell == "-":
            return is_ghost and allows_door
        return True

    def get_valid_directions(self, x: int, y: int, current_dir: Tuple[int, int],
                             is_ghost: bool = False, allows_door: bool = False,
                             can_reverse: bool = False) -> List[Tuple[int, int]]:
        valid = []
        opp = OPPOSITE_DIR[current_dir]
        for d in [DIR_UP, DIR_LEFT, DIR_DOWN, DIR_RIGHT]:
            if not can_reverse and d == opp:
                continue
            nx = x + d[0]
            ny = y + d[1]
            if ny == self.tunnel_row:
                nx = nx % self.maze_width
            if self.is_walkable(nx, ny, is_ghost=is_ghost, allows_door=allows_door):
                valid.append(d)
        return valid

    def update_ghost_target(self, ghost: Ghost):
        if ghost.mode == MODE_EATEN:
            ghost.target = self.house_entrance
            return

        if ghost.mode == MODE_SCATTER:
            ghost.target = ghost.scatter_corner
            return

        px, py = self.pacman.x, self.pacman.y
        pdir = self.pacman.dir

        if ghost.name == GHOST_BLINKY:
            ghost.target = (px, py)
        elif ghost.name == GHOST_PINKY:
            dx, dy = pdir
            ghost.target = (px + 4 * dx, py + 4 * dy)
        elif ghost.name == GHOST_INKY:
            blinky = self.ghosts[GHOST_BLINKY]
            dx, dy = pdir
            p_ahead = (px + 2 * dx, py + 2 * dy)
            ghost.target = (2 * p_ahead[0] - blinky.x, 2 * p_ahead[1] - blinky.y)
        elif ghost.name == GHOST_CLYDE:
            dist = math.hypot(ghost.x - px, ghost.y - py)
            ghost.target = (px, py) if dist > 8.0 else ghost.scatter_corner

    def choose_ghost_direction(self, ghost: Ghost) -> Tuple[int, int]:
        allows_door = (ghost.in_house or ghost.mode == MODE_EATEN)
        valid_dirs = self.get_valid_directions(ghost.x, ghost.y, ghost.dir,
                                               is_ghost=True, allows_door=allows_door)

        if not valid_dirs:
            opp = OPPOSITE_DIR[ghost.dir]
            nx, ny = ghost.x + opp[0], ghost.y + opp[1]
            if ny == self.tunnel_row:
                nx = nx % self.maze_width
            if self.is_walkable(nx, ny, is_ghost=True, allows_door=allows_door):
                return opp
            return DIR_NONE

        if ghost.mode == MODE_FRIGHTENED:
            return random.choice(valid_dirs)

        tx, ty = ghost.target
        best_dir = valid_dirs[0]
        min_dist = float("inf")

        for d in valid_dirs:
            nx = ghost.x + d[0]
            ny = ghost.y + d[1]
            if ny == self.tunnel_row:
                nx = nx % self.maze_width
            dist_sq = (nx - tx) ** 2 + (ny - ty) ** 2
            if dist_sq < min_dist:
                min_dist = dist_sq
                best_dir = d

        return best_dir

    def handle_input(self):
        key = self.terminal.get_key()
        if not key:
            return

        if key in ("q", "Q"):
            self.game_over = True
            return

        if key in ("p", "P"):
            if self.state == "PLAYING":
                self.paused = not self.paused
            return

        if self.state == "TITLE":
            if key in (" ", "\r", "\n", "w", "s", "a", "d", "UP", "DOWN", "LEFT", "RIGHT"):
                self.start_new_game()
            return

        if self.state == "GAME_OVER":
            if key in ("r", "R", " ", "\r", "\n"):
                self.start_new_game()
            return

        if self.state != "PLAYING" or self.paused:
            return

        if key in ("w", "W", "UP"):
            self.pacman.desired_dir = DIR_UP
        elif key in ("s", "S", "DOWN"):
            self.pacman.desired_dir = DIR_DOWN
        elif key in ("a", "A", "LEFT"):
            self.pacman.desired_dir = DIR_LEFT
        elif key in ("d", "D", "RIGHT"):
            self.pacman.desired_dir = DIR_RIGHT

    def update_wave_cycle(self, dt: float):
        if self.frightened_timer > 0.0:
            self.frightened_timer -= dt
            if self.frightened_timer <= 0.0:
                self.frightened_timer = 0.0
                for g in self.ghosts.values():
                    if g.mode == MODE_FRIGHTENED:
                        g.mode = self.current_global_mode
            return

        scatter_dur, chase_dur = self.waves[self.wave_index]
        self.wave_timer += dt

        if self.current_global_mode == MODE_SCATTER:
            if self.wave_timer >= scatter_dur:
                self.wave_timer = 0.0
                self.current_global_mode = MODE_CHASE
                self._reverse_active_ghosts()
        elif self.current_global_mode == MODE_CHASE:
            if self.wave_timer >= chase_dur and chase_dur != float("inf"):
                self.wave_timer = 0.0
                if self.wave_index < len(self.waves) - 1:
                    self.wave_index += 1
                self.current_global_mode = MODE_SCATTER
                self._reverse_active_ghosts()

        for g in self.ghosts.values():
            if g.mode not in (MODE_FRIGHTENED, MODE_EATEN):
                g.mode = self.current_global_mode

    def _reverse_active_ghosts(self):
        for g in self.ghosts.values():
            if not g.in_house and g.mode not in (MODE_FRIGHTENED, MODE_EATEN):
                opp = OPPOSITE_DIR[g.dir]
                nx, ny = g.x + opp[0], g.y + opp[1]
                if ny == self.tunnel_row:
                    nx = nx % self.maze_width
                if self.is_walkable(nx, ny, is_ghost=True):
                    g.dir = opp

    def trigger_energizer(self):
        self.terminal.bell()
        self.score += 50
        if self.score > self.high_score:
            self.high_score = self.score
        self.frightened_timer = max(2.5, self.frightened_duration - (self.level - 1) * 0.8)
        self.ghosts_eaten_combo = 0

        for g in self.ghosts.values():
            if g.mode != MODE_EATEN and not g.in_house:
                g.mode = MODE_FRIGHTENED
                opp = OPPOSITE_DIR[g.dir]
                nx, ny = g.x + opp[0], g.y + opp[1]
                if ny == self.tunnel_row:
                    nx = nx % self.maze_width
                if self.is_walkable(nx, ny, is_ghost=True):
                    g.dir = opp

    def update_pacman(self, dt: float):
        self.pacman.update_animation(dt)

        if self.pacman.desired_dir != self.pacman.dir:
            test_x = self.pacman.x + self.pacman.desired_dir[0]
            test_y = self.pacman.y + self.pacman.desired_dir[1]
            if test_y == self.tunnel_row:
                test_x = test_x % self.maze_width
            if self.is_walkable(test_x, test_y):
                self.pacman.dir = self.pacman.desired_dir

        self.pacman.move_accumulator += dt * self.pacman.speed
        while self.pacman.move_accumulator >= 1.0:
            self.pacman.move_accumulator -= 1.0

            nx = self.pacman.x + self.pacman.dir[0]
            ny = self.pacman.y + self.pacman.dir[1]
            if ny == self.tunnel_row:
                nx = nx % self.maze_width

            if self.is_walkable(nx, ny):
                self.pacman.x = nx
                self.pacman.y = ny

                cell = self.grid[ny][nx]
                if cell == ".":
                    self.grid[ny][nx] = " "
                    self.score += 10
                    self.pellets_left -= 1
                    if self.score > self.high_score:
                        self.high_score = self.score
                    self._check_fruit_spawn()
                elif cell == "*":
                    self.grid[ny][nx] = " "
                    self.pellets_left -= 1
                    self.trigger_energizer()
                    self._check_fruit_spawn()

                if self.fruit_active and (nx, ny) == self.fruit_tile:
                    fruit_name, fruit_sym, fruit_pts = self.get_fruit_info()
                    self.score += fruit_pts
                    if self.score > self.high_score:
                        self.high_score = self.score
                    self.fruit_active = False
                    self.floating_scores.append({
                        "x": nx, "y": ny, "text": f"+{fruit_pts}", "timer": 1.0
                    })
                    self.terminal.bell()

                if self.pellets_left <= 0:
                    self.state = "LEVEL_CLEAR"
                    self.state_timer = 2.0
                    return

    def _check_fruit_spawn(self):
        eaten = self.total_pellets - self.pellets_left
        if (eaten == 70 or eaten == 170) and not self.fruit_active:
            self.fruit_active = True
            self.fruit_timer = 9.5
            self.fruit_spawned_count += 1

    def get_fruit_info(self) -> Tuple[str, str, int]:
        idx = min(self.level - 1, len(FRUIT_TYPES) - 1)
        return FRUIT_TYPES[idx]

    def update_fruit(self, dt: float):
        if self.fruit_active:
            self.fruit_timer -= dt
            if self.fruit_timer <= 0.0:
                self.fruit_active = False

    def update_ghosts(self, dt: float):
        eaten_pellets = self.total_pellets - self.pellets_left

        for ghost in self.ghosts.values():
            if ghost.in_house:
                ghost.house_timer += dt
                can_leave = (ghost.house_timer >= ghost.release_delay) or \
                            (ghost.name == GHOST_INKY and eaten_pellets >= 30) or \
                            (ghost.name == GHOST_CLYDE and eaten_pellets >= 60)
                if can_leave:
                    if ghost.x < 13:
                        ghost.x += 1
                    elif ghost.x > 14:
                        ghost.x -= 1
                    elif ghost.y > 11:
                        ghost.y -= 1
                        if ghost.y == 11:
                            ghost.in_house = False
                            ghost.dir = DIR_LEFT
                continue

            if ghost.mode == MODE_EATEN:
                current_speed = 14.0
            elif ghost.mode == MODE_FRIGHTENED:
                current_speed = 4.2
            elif ghost.name == GHOST_BLINKY and self.pellets_left <= 20:
                current_speed = 8.5
            else:
                current_speed = 7.2 + min(1.5, (self.level - 1) * 0.3)

            ghost.speed = current_speed
            self.update_ghost_target(ghost)

            ghost.move_accumulator += dt * ghost.speed
            while ghost.move_accumulator >= 1.0:
                ghost.move_accumulator -= 1.0

                if ghost.mode == MODE_EATEN and (ghost.x, ghost.y) == self.house_entrance:
                    ghost.x, ghost.y = self.house_interior
                    ghost.in_house = True
                    ghost.mode = self.current_global_mode
                    ghost.house_timer = 0.0
                    ghost.release_delay = 0.5
                    break

                new_dir = self.choose_ghost_direction(ghost)
                ghost.dir = new_dir

                nx = ghost.x + ghost.dir[0]
                ny = ghost.y + ghost.dir[1]
                if ny == self.tunnel_row:
                    nx = nx % self.maze_width

                allows_door = (ghost.mode == MODE_EATEN or ghost.in_house)
                if self.is_walkable(nx, ny, is_ghost=True, allows_door=allows_door):
                    ghost.x = nx
                    ghost.y = ny

    def check_collisions(self):
        px, py = self.pacman.x, self.pacman.y
        for ghost in self.ghosts.values():
            if (ghost.x, ghost.y) == (px, py):
                if ghost.mode == MODE_FRIGHTENED:
                    self.ghosts_eaten_combo += 1
                    pts = 200 * (2 ** (self.ghosts_eaten_combo - 1))
                    self.score += pts
                    if self.score > self.high_score:
                        self.high_score = self.score
                    ghost.mode = MODE_EATEN
                    self.floating_scores.append({
                        "x": px, "y": py, "text": f"+{pts}", "timer": 0.9
                    })
                    self.terminal.bell()
                elif ghost.mode in (MODE_CHASE, MODE_SCATTER):
                    self.state = "DYING"
                    self.state_timer = 1.4
                    self.terminal.bell()
                    return

    def update_floating_scores(self, dt: float):
        for item in self.floating_scores:
            item["timer"] -= dt
        self.floating_scores = [item for item in self.floating_scores if item["timer"] > 0.0]

    def render_frame(self) -> str:
        lines = []

        fruit_name, fruit_sym, _ = self.get_fruit_info()
        lines.append(f"{COLOR_BOLD}{COLOR_WHITE}1UP        HIGH SCORE       LEVEL {self.level:02d}{COLOR_RESET}")
        lines.append(f"{COLOR_SCORE}{self.score:06d}{COLOR_WHITE}     {COLOR_YELLOW}{self.high_score:06d}{COLOR_WHITE}          {fruit_sym} {fruit_name}{COLOR_RESET}")

        ghost_map: Dict[Tuple[int, int], Ghost] = {}
        for g in self.ghosts.values():
            ghost_map[(g.x, g.y)] = g

        floating_map: Dict[Tuple[int, int], str] = {}
        for item in self.floating_scores:
            floating_map[(item["x"], item["y"])] = item["text"]

        pac_pos = (self.pacman.x, self.pacman.y)
        fruit_pos = self.fruit_tile if self.fruit_active else None

        wall_color = COLOR_BLUE
        if self.state == "LEVEL_CLEAR" and int(self.state_timer * 6) % 2 == 1:
            wall_color = COLOR_WHITE

        for y in range(self.maze_height):
            row_str = []
            for x in range(self.maze_width):
                pos = (x, y)

                if pos in floating_map:
                    text = floating_map[pos]
                    row_str.append(f"{COLOR_BOLD}{COLOR_SCORE}{text[:2]}{COLOR_RESET}")
                    continue

                if pos == pac_pos and self.state in ("PLAYING", "READY", "PAUSED"):
                    char = ("C " if self.pacman.mouth_open else "O ") if self.force_ascii else ("ᗧ " if self.pacman.mouth_open else "O ")
                    row_str.append(f"{COLOR_BOLD}{COLOR_YELLOW}{char}{COLOR_RESET}")
                    continue

                if pos in ghost_map:
                    g = ghost_map[pos]
                    row_str.append(self._get_ghost_render_str(g))
                    continue

                if fruit_pos and pos == fruit_pos:
                    sym = "F " if self.force_ascii else fruit_sym
                    row_str.append(f"{COLOR_FRUIT}{sym}{COLOR_RESET}")
                    continue

                cell = self.grid[y][x]
                if cell == "#":
                    block = "##" if self.force_ascii else "██"
                    row_str.append(f"{wall_color}{block}{COLOR_RESET}")
                elif cell == "-":
                    door = "--" if self.force_ascii else "══"
                    row_str.append(f"{COLOR_DOOR}{door}{COLOR_RESET}")
                elif cell == ".":
                    pellet = ". " if self.force_ascii else "· "
                    row_str.append(f"{COLOR_PELLET}{pellet}{COLOR_RESET}")
                elif cell == "*":
                    flash = (self.frame_count // 4) % 2 == 0
                    color = COLOR_YELLOW if flash else COLOR_WHITE
                    sym = "* " if self.force_ascii else "● "
                    row_str.append(f"{COLOR_BOLD}{color}{sym}{COLOR_RESET}")
                else:
                    row_str.append("  ")

            lines.append("".join(row_str))

        lives_str = ("C " if self.force_ascii else "ᗧ ") * max(0, self.lives - 1)
        lines.append(f"{COLOR_WHITE}LIVES: {COLOR_YELLOW}{lives_str:<8}{COLOR_WHITE} [WASD/ARROWS: Move  P: Pause  Q: Quit]{COLOR_RESET}")

        banner = None
        if self.state == "TITLE":
            banner = [
                f"{COLOR_YELLOW}╔════════════════════════════════╗{COLOR_RESET}",
                f"{COLOR_YELLOW}║      P A C - M A N             ║{COLOR_RESET}",
                f"{COLOR_YELLOW}║      Terminal Arcade           ║{COLOR_RESET}",
                f"{COLOR_WHITE}║                                ║{COLOR_RESET}",
                f"{COLOR_WHITE}║    Press SPACE / ENTER to Start║{COLOR_RESET}",
                f"{COLOR_YELLOW}╚════════════════════════════════╝{COLOR_RESET}",
            ]
        elif self.state == "READY":
            banner = [
                f"{COLOR_BOLD}{COLOR_YELLOW}       R E A D Y !        {COLOR_RESET}"
            ]
        elif self.paused:
            banner = [
                f"{COLOR_BOLD}{COLOR_WHITE}   * * * P A U S E D * * *{COLOR_RESET}",
                f"{COLOR_WHITE}    Press P to resume     {COLOR_RESET}"
            ]
        elif self.state == "GAME_OVER":
            banner = [
                f"{COLOR_BOLD}{COLOR_RED}    G A M E   O V E R     {COLOR_RESET}",
                f"{COLOR_WHITE}  Press R to Play Again   {COLOR_RESET}",
                f"{COLOR_WHITE}  Press Q to Exit         {COLOR_RESET}",
            ]
        elif self.state == "LEVEL_CLEAR":
            banner = [
                f"{COLOR_BOLD}{COLOR_WHITE}   L E V E L   C L E A R !{COLOR_RESET}"
            ]

        if banner:
            start_y = 16
            for i, b_line in enumerate(banner):
                target_idx = start_y + i
                if target_idx < len(lines):
                    pad = max(0, (56 - 28) // 2)
                    lines[target_idx] = " " * pad + b_line

        return "\n".join(lines) + "\n"

    def _get_ghost_render_str(self, ghost: Ghost) -> str:
        if ghost.mode == MODE_EATEN:
            sym = "oo" if self.force_ascii else '""'
            return f"{COLOR_EYES}{sym}{COLOR_RESET}"

        if ghost.mode == MODE_FRIGHTENED:
            if self.frightened_timer <= 2.0 and int(self.frightened_timer * 6) % 2 == 1:
                color = COLOR_FRIGHT_WHITE
            else:
                color = COLOR_FRIGHT_BLUE
            sym = "M " if self.force_ascii else "ᗣ "
            return f"{COLOR_BOLD}{color}{sym}{COLOR_RESET}"

        sym = "M " if self.force_ascii else "ᗣ "
        if ghost.name == GHOST_BLINKY:
            return f"{COLOR_BOLD}{COLOR_RED}{sym}{COLOR_RESET}"
        elif ghost.name == GHOST_PINKY:
            return f"{COLOR_BOLD}{COLOR_PINK}{sym}{COLOR_RESET}"
        elif ghost.name == GHOST_INKY:
            return f"{COLOR_BOLD}{COLOR_CYAN}{sym}{COLOR_RESET}"
        elif ghost.name == GHOST_CLYDE:
            return f"{COLOR_BOLD}{COLOR_ORANGE}{sym}{COLOR_RESET}"
        return f"{COLOR_WHITE}{sym}{COLOR_RESET}"

    def run(self):
        """Executes real-time arcade loop."""
        def handle_signal(sig, frame):
            self.terminal.exit()
            self.save_high_score()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        self.terminal.enter()
        last_time = time.time()

        try:
            while not self.game_over:
                now = time.time()
                elapsed = now - last_time
                if elapsed < self.dt:
                    time.sleep(self.dt - elapsed)
                    now = time.time()

                dt = now - last_time
                last_time = now
                self.frame_count += 1

                self.handle_input()

                if self.state == "TITLE":
                    pass
                elif self.state == "READY":
                    self.state_timer -= dt
                    if self.state_timer <= 0.0:
                        self.state = "PLAYING"
                elif self.state == "PLAYING":
                    if not self.paused:
                        self.update_wave_cycle(dt)
                        self.update_pacman(dt)
                        self.update_fruit(dt)
                        self.update_ghosts(dt)
                        self.check_collisions()
                        self.update_floating_scores(dt)
                elif self.state == "DYING":
                    self.state_timer -= dt
                    if self.state_timer <= 0.0:
                        self.lives -= 1
                        if self.lives > 0:
                            self.reset_round_positions()
                        else:
                            self.state = "GAME_OVER"
                            self.save_high_score()
                elif self.state == "LEVEL_CLEAR":
                    self.state_timer -= dt
                    if self.state_timer <= 0.0:
                        self.level += 1
                        self.reset_maze()
                        self.reset_round_positions()
                elif self.state == "GAME_OVER":
                    pass

                frame_str = self.render_frame()
                self.terminal.render(frame_str)

        finally:
            self.terminal.exit()
            self.save_high_score()
            print(f"\n{COLOR_BOLD}Thanks for playing PAC-MAN! Final Score: {self.score}{COLOR_RESET}")


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Terminal PAC-MAN Arcade Game")
    parser.add_argument("--ascii", action="store_true", help="Force plain 7-bit ASCII characters (no Unicode)")
    parser.add_argument("--fps", type=int, default=20, help="Target game loop frame rate (default: 20)")
    parser.add_argument("--sound", action="store_true", help="Enable terminal bell audio feedback")
    parser.add_argument("--test", action="store_true", help="Run automated headless validation test")
    args = parser.parse_args()

    if args.test:
        print("Running headless game simulation test...")
        game = PacmanGame(force_ascii=args.ascii, fps=args.fps)
        game.start_new_game()
        for _ in range(60):
            game.update_pacman(game.dt)
            game.update_ghosts(game.dt)
            game.check_collisions()
        print(f"Simulation completed successfully! Score: {game.score}, Pac-Man at ({game.pacman.x}, {game.pacman.y})")
        return

    game = PacmanGame(force_ascii=args.ascii, fps=args.fps, enable_sound=args.sound)
    game.run()


if __name__ == "__main__":
    main()
