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

export function savePuzzleState(dateStr, userGrid, solved = null) {
    const key = getStorageKey(dateStr);
    const existing = loadPuzzleState(dateStr);
    const data = {
        grid: serializeGrid(userGrid),
        savedAt: Date.now(),
        solved: solved !== null ? solved : (existing?.solved || false)
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
            savedAt: data.savedAt,
            solved: data.solved || false
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

export function markPuzzleSolved(dateStr) {
    const key = getStorageKey(dateStr);
    try {
        const raw = localStorage.getItem(key);
        if (!raw) return;
        const data = JSON.parse(raw);
        data.solved = true;
        localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {
        console.warn('Failed to mark puzzle solved:', e);
    }
}

export function isPuzzleSolved(dateStr) {
    const key = getStorageKey(dateStr);
    try {
        const raw = localStorage.getItem(key);
        if (!raw) return false;
        const data = JSON.parse(raw);
        return data.solved || false;
    } catch (e) {
        return false;
    }
}
