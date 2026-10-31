import heapq

SQRT2 = 1.4142135623730951
NEIGHBORS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def _octile(a, b):
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return (dx + dy) + (SQRT2 - 2) * min(dx, dy)


def a_star(tilemap, start, goal):
    if tilemap.is_blocked(*goal) or start == goal:
        return []
    open_heap = [(0.0, start)]
    came = {}
    g = {start: 0.0}
    while open_heap:
        _, cur = heapq.heappop(open_heap)
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            path.reverse()
            return path[1:]
        cx, cy = cur
        for dx, dy in NEIGHBORS:
            nx, ny = cx + dx, cy + dy
            if tilemap.is_blocked(nx, ny):
                continue
            if dx != 0 and dy != 0:
                if tilemap.is_blocked(cx + dx, cy) and tilemap.is_blocked(cx, cy + dy):
                    continue
            step = SQRT2 if dx and dy else 1.0
            ng = g[cur] + step
            nb = (nx, ny)
            if nb not in g or ng < g[nb]:
                g[nb] = ng
                came[nb] = cur
                heapq.heappush(open_heap, (ng + _octile(nb, goal), nb))
    return []
