import random
import string

DIRECTIONS = {
    'H':  (0,  1),
    'V':  (1,  0),
    'HR': (0, -1),
    'VR': (-1, 0),
    'D1': (1,  1),
    'D2': (1, -1),
    'D3': (-1, 1),
    'D4': (-1,-1),
}


def _calc_grid_size(words):
    longest = max(len(w) for w in words)
    total_chars = sum(len(w) for w in words)
    size = max(longest + 2, int(total_chars ** 0.6) + 2)
    return min(size, 20)


def _can_place(grid, word, row, col, dr, dc):
    size = len(grid)
    for i, ch in enumerate(word):
        r, c = row + dr * i, col + dc * i
        if not (0 <= r < size and 0 <= c < size):
            return False
        if grid[r][c] not in ('.', ch):
            return False
    return True


def _place_word(grid, word, row, col, dr, dc):
    cells = []
    for i, ch in enumerate(word):
        r, c = row + dr * i, col + dc * i
        grid[r][c] = ch
        cells.append([r, c])
    return cells


def build_grid(words):
    """
    Recebe lista de strings (já em maiúsculas).
    Retorna (grid, placements) onde:
      - grid: lista de listas de chars (NxN)
      - placements: {'PALAVRA': [[r,c], ...]}
    Levanta ValueError se não conseguir posicionar todas as palavras.
    """
    words_sorted = sorted(words, key=len, reverse=True)
    size = _calc_grid_size(words_sorted)

    directions = list(DIRECTIONS.values())
    placements = {}

    for attempt in range(50):
        grid = [['.' for _ in range(size)] for _ in range(size)]
        placements = {}
        failed = False

        for word in words_sorted:
            placed = False
            order = directions[:]
            random.shuffle(order)

            for dr, dc in order:
                positions = [(r, c) for r in range(size) for c in range(size)]
                random.shuffle(positions)
                for row, col in positions:
                    if _can_place(grid, word, row, col, dr, dc):
                        cells = _place_word(grid, word, row, col, dr, dc)
                        placements[word] = cells
                        placed = True
                        break
                if placed:
                    break

            if not placed:
                failed = True
                break

        if not failed:
            for r in range(size):
                for c in range(size):
                    if grid[r][c] == '.':
                        grid[r][c] = random.choice(string.ascii_uppercase)
            return grid, placements

    raise ValueError(f'Não foi possível montar o grid após 50 tentativas. Palavras: {words_sorted}')