const today = new Date();
const yyyy = today.getFullYear();
const mm = String(today.getMonth() + 1).padStart(2, '0');
const dd = String(today.getDate()).padStart(2, '0');
const TODAY_ISO = `${yyyy}-${mm}-${dd}`;

export const constants = {
    TODAY_ISO,
    DEFAULT_DATE: TODAY_ISO,
    MIN_DATE: '2026-01-24',
    MAX_DATE: TODAY_ISO,
    GRID_SIZE: 500,
};

export const puzzle = {
    rows: 0,
    cols: 0,
    grid: [],
};

export const solution = [];

export const userState = {
    grid: [],
    selected: null,
    hovered: null,
    mode: 'pen',
    isCtrlPressed: false,
};

export let currentDate = new URLSearchParams(window.location.search).get('date') || constants.DEFAULT_DATE;

export function setCurrentDate(date) {
    currentDate = date;
}

export const numpadUndoStack = [];

export function initUserState() {
    userState.grid = [];
    for (let r = 0; r < puzzle.rows; r++) {
        const row = [];
        for (let c = 0; c < puzzle.cols; c++) {
            row.push({
                val: puzzle.grid[r][c].val,
                marks: new Set()
            });
        }
        userState.grid.push(row);
    }
}
