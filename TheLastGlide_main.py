import os
import time
from time import sleep

try:
    import msvcrt
    WINDOWS = True
except ImportError:
    import sys, termios, tty, select
    WINDOWS = False

LEVELS_FILE = "levels.txt"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_key():
    if WINDOWS:
        return msvcrt.getch().decode('utf-8').lower()
    else:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                ch = sys.stdin.read(1)
            else:
                ch = ''
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch.lower()

def load_levels(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    raw_levels = [block for block in content.split("\n\n") if block.strip()]
    levels = []
    for block in raw_levels:
        level = [list(line) for line in block.splitlines()]
        levels.append(level)
    return levels

levels = load_levels(LEVELS_FILE)
original_levels = [[list(row) for row in level] for level in levels]

current_level = 0
field = []
height = 0
width = 0
portal_pairs = {'o': 'O', 'O': 'o', 'p': 'P', 'P': 'p', 'q': 'Q', 'Q': 'q'}
portal_links = {}
h_blocks = []
player_name = "GUEST"
level_start_time = None
move_count = 0

def place_player(x, y):
    field[y][x] = '@'

def find_player():
    for yy in range(len(field)):
        for xx in range(len(field[yy])):
            if field[yy][xx] == '@':
                return xx, yy
    return None

def find_portal_target(x, y):
    return portal_links.get((x, y), None)

def push_box(x, y, dx, dy):
    cx, cy = x, y
    if original_levels[current_level][cy][cx] == 'S':
        field[cy][cx] = 'S'
    else:
        if any((cx, cy) in hb["path"] for hb in h_blocks):
            field[cy][cx] = '*'
        else:
            field[cy][cx] = '.'

    while True:
        nx = cx + dx
        ny = cy + dy
        if ny < 0 or ny >= height or nx < 0 or nx >= width:
            break
        target = field[ny][nx]
        if target in ['#', '+', 'H']:
            break
        if target == '~':
            field[ny][nx] = '.'
            return nx, ny
        if target == 'X':
            break
        if target == '.':
            cx, cy = nx, ny
            continue
        if target == 'S':
            cx, cy = nx, ny
            break
        if target == '%':
            field[ny][nx] = '.'
            break
        if target in portal_pairs:
            dest = find_portal_target(nx, ny)
            if dest:
                cx, cy = dest
                continue
            break

    field[cy][cx] = '+'
    return cx, cy

def load_h_path():
    global h_blocks
    h_blocks = []
    visited = set()

    def dfs(x, y, path):
        if (x, y) in visited:
            return
        visited.add((x, y))
        path.append((x, y))
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if field[ny][nx] in ['*', 'H']:
                    dfs(nx, ny, path)

    for yy in range(height):
        for xx in range(width):
            if field[yy][xx] == 'H' and (xx, yy) not in visited:
                path = []
                dfs(xx, yy, path)
                if path:
                    h_blocks.append({"path": path, "index": 0, "forward": True})

def move_h_block():
    for block in h_blocks:
        path = block["path"]
        if not path:
            continue
        idx = block["index"]
        forward = block["forward"]
        hx, hy = path[idx]

        if (hx, hy) in path:
            field[hy][hx] = '*'
        else:
            field[hy][hx] = '.'

        if forward:
            idx += 1
            if idx >= len(path):
                idx = len(path) - 2 if len(path) >= 2 else 0
                block["forward"] = False
        else:
            idx -= 1
            if idx < 0:
                idx = 1 if len(path) >= 2 else 0
                block["forward"] = True

        block["index"] = idx
        nx, ny = path[idx]
        target = field[ny][nx]

        if target == '@':
            dx = nx - hx
            dy = ny - hy
            px, py = nx + dx, ny + dy
            if 0 <= px < width and 0 <= py < height and field[py][px] == '.':
                field[py][px] = '@'
                field[ny][nx] = 'H'
            else:
                field[ny][nx] = 'H'
        elif target == '+':
            dx = nx - hx
            dy = ny - hy
            bx, by = nx + dx, ny + dy
            if 0 <= bx < width and 0 <= by < height and field[by][bx] == '.':
                field[by][bx] = '+'
                field[ny][nx] = 'H'

def show_field():
    clear_screen()
    print(f"Level {current_level + 1} / {len(levels)}")
    print("Controls: w/a/s/d = move, r = reset, q = quit, Enter = move H blocks")
    print("'.' = Air '#' = Wall '+' = Box '~' = Lava 'S' = Slime '%' = One-Time 'o/O/p/P/q/Q' = Portals 'H' = moving Block '*' = H-path")
    for line in field:
        print(''.join(line))

def load_level(level_number):
    global field, height, width, current_level, portal_links, level_start_time, move_count
    current_level = level_number
    field = [list(row) for row in original_levels[current_level]]
    height = len(field)
    width = len(field[0]) if height > 0 else 0
    level_start_time = time.time()
    move_count = 0
    portal_links = {}
    portals = {}
    for yy in range(height):
        for xx in range(width):
            ch = field[yy][xx]
            if ch in portal_pairs:
                symbol = ch
                pair_symbol = portal_pairs[symbol]
                if symbol not in portals:
                    portals[symbol] = (xx, yy)
                if pair_symbol in portals:
                    x2, y2 = portals[pair_symbol]
                    portal_links[(xx, yy)] = (x2, y2)
                    portal_links[(x2, y2)] = (xx, yy)
    load_h_path()

def move(dx, dy):
    global current_level, level_start_time, move_count
    pos = find_player()
    if pos is None:
        return
    move_count += 1
    move_h_block()
    x, y = pos

    if original_levels[current_level][y][x] == 'S':
        field[y][x] = 'S'
    else:
        if any((x, y) in hb["path"] for hb in h_blocks):
            field[y][x] = '*'
        else:
            field[y][x] = '.'

    while True:
        nx = x + dx
        ny = y + dy
        if ny < 0 or ny >= height or nx < 0 or nx >= width:
            break
        target = field[ny][nx]
        if target == '#':
            break
        if target == '%':
            field[ny][nx] = '.'
            break
        if target == '~':
            load_level(current_level)
            clear_screen()
            print("You fell into lava! Resetting level...")
            sleep(1)
            return
        if target == '+':
            push_box(nx, ny, dx, dy)
            place_player(x, y)
            return
        if target == 'H':
            break
        if target == 'X':
            place_player(nx, ny)
            show_field()
            print("Level completed!")
            sleep(1)
            current_level += 1
            if current_level >= len(levels):
                clear_screen()
                print("Congratulations! You finished all levels!")
                sleep(2)
                exit(0)
            load_level(current_level)
            return
        if target == 'S':
            place_player(nx, ny)
            return
        if target in portal_pairs:
            dest = find_portal_target(nx, ny)
            if dest:
                nx, ny = dest
                x, y = nx, ny
    place_player(x, y)

def start_game():
    global current_level, move_count
    current_level = 0
    move_count = 0
    load_level(current_level)
    direction_map = {'w': (0, -1), 's': (0, 1), 'a': (-1, 0), 'd': (1, 0)}
    while True:
        show_field()
        key = get_key()
        if key == 'q':
            clear_screen()
            print("Game ended.")
            sleep(1)
            break
        elif key == 'r':
            load_level(current_level)
        elif key == '':
            move_h_block()
        elif key in direction_map:
            dx, dy = direction_map[key]
            move(dx, dy)

if __name__ == "__main__":
    start_game()
