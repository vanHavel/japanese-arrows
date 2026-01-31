const STORAGE_PREFIX = 'yazudo_puzzle_';

function getStorageKey(dateStr) {
    return `${STORAGE_PREFIX}${dateStr}`;
}

function serializeGrid(grid) {
    return grid.map(row =>
        row.map(cell => ({
            val: cell.val,
            marks: Array.from(cell.marks)
        }))
    );
}

function deserializeGrid(data) {
    return data.map(row =>
        row.map(cell => ({
            val: cell.val,
            marks: new Set(cell.marks)
        }))
    );
}

export function savePuzzleState(dateStr, userGrid) {
    const key = getStorageKey(dateStr);
    const data = {
        grid: serializeGrid(userGrid),
        savedAt: Date.now()
    };
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {
        console.warn('Failed to save puzzle state:', e);
    }
}

export function loadPuzzleState(dateStr) {
    const key = getStorageKey(dateStr);
    try {
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        const data = JSON.parse(raw);
        return {
            grid: deserializeGrid(data.grid),
            savedAt: data.savedAt
        };
    } catch (e) {
        console.warn('Failed to load puzzle state:', e);
        return null;
    }
}

export function clearPuzzleState(dateStr) {
    const key = getStorageKey(dateStr);
    try {
        localStorage.removeItem(key);
    } catch (e) {
        console.warn('Failed to clear puzzle state:', e);
    }
}
