import { puzzle, userState, undoStack, MAX_UNDO_SIZE, currentDate } from './state.js';
import { renderGrid, updateNumpadVisuals, updateDesktopNumpadVisuals } from './render.js';
import { openNumpadModal, closeNumpadModal, canModalUndo } from './modals.js';
import { savePuzzleState } from './storage.js';
import { clearSolvedState } from './puzzle.js';

const modePenBtn = document.getElementById('mode-pen');
const modePencilBtn = document.getElementById('mode-pencil');
const modePenBtnDesktop = document.getElementById('mode-pen-desktop');
const modePencilBtnDesktop = document.getElementById('mode-pencil-desktop');

export function setMode(mode) {
    userState.mode = mode;
    updateModeVisuals();
    updateDesktopNumpadVisuals();
}

export function updateModeVisuals() {
    if (userState.isCtrlPressed && userState.mode === 'pen') {
        modePenBtn.classList.remove('active');
        modePencilBtn.classList.add('active');
        modePenBtnDesktop.classList.remove('active');
        modePencilBtnDesktop.classList.add('active');
    } else {
        modePenBtn.classList.toggle('active', userState.mode === 'pen');
        modePencilBtn.classList.toggle('active', userState.mode === 'pencil');
        modePenBtnDesktop.classList.toggle('active', userState.mode === 'pen');
        modePencilBtnDesktop.classList.toggle('active', userState.mode === 'pencil');
    }
}

export function selectCell(r, c) {
    if (userState.selected && userState.selected.r === r && userState.selected.c === c) {
        userState.selected = null;
        renderGrid();
        if (window.matchMedia("(pointer: coarse)").matches) {
            closeNumpadModal();
        }
        return;
    }

    userState.selected = { r, c };
    renderGrid();
    updateDesktopNumpadVisuals();

    if (window.matchMedia("(pointer: coarse)").matches) {
        if (!puzzle.grid[r][c].initial) {
            const puzzleGrid = document.getElementById('puzzle-grid');
            const cells = puzzleGrid.querySelectorAll('.cell');
            const cellElement = cells[r * puzzle.cols + c];
            openNumpadModal(cellElement);
        }
    }
}

export function inputNumber(val) {
    const target = userState.selected || userState.hovered;
    if (!target) return;

    const { r, c } = target;

    if (puzzle.grid[r][c].initial) return;

    const cell = userState.grid[r][c];
    undoStack.push({
        row: r,
        col: c,
        prevVal: cell.val,
        prevMarks: new Set(cell.marks),
    });
    if (undoStack.length > MAX_UNDO_SIZE) {
        undoStack.shift();
    }

    const effectiveMode = (userState.isCtrlPressed && userState.mode === 'pen') ? 'pencil' : userState.mode;

    if (val === null) {
        userState.grid[r][c].val = null;
        userState.grid[r][c].marks.clear();
    } else {
        if (effectiveMode === 'pen') {
            userState.grid[r][c].val = val;
            userState.grid[r][c].marks.clear();
            if (userState.grid[r][c].isError) {
                userState.grid[r][c].isError = false;
            }
        } else {
            if (userState.grid[r][c].marks.has(val)) {
                userState.grid[r][c].marks.delete(val);
            } else {
                userState.grid[r][c].marks.add(val);
            }
            userState.grid[r][c].val = null;
            userState.grid[r][c].isError = false;
        }
    }
    renderGrid();
    updateDesktopNumpadVisuals();
    clearSolvedState();
    savePuzzleState(currentDate, userState.grid, false);
}

export function moveSelection(key) {
    let { r, c } = userState.selected;
    if (key === 'ArrowUp') r = Math.max(0, r - 1);
    if (key === 'ArrowDown') r = Math.min(puzzle.rows - 1, r + 1);
    if (key === 'ArrowLeft') c = Math.max(0, c - 1);
    if (key === 'ArrowRight') c = Math.min(puzzle.cols - 1, c + 1);
    selectCell(r, c);
}

export function highlightNumpadKey(val) {
    const numParams = document.querySelectorAll('.num-btn:not(.mobile-num-btn)');
    let btn = null;
    if (val === 'delete') {
        btn = document.getElementById('numpad-delete');
    } else {
        for (const b of numParams) {
            if (b.getAttribute('data-value') === val) {
                btn = b;
                break;
            }
        }
    }

    if (btn) {
        btn.classList.add('pressed');
        setTimeout(() => {
            btn.classList.remove('pressed');
        }, 150);
    }
}

export function handleKeyDown(e) {
    if (e.key === 'Control') {
        userState.isCtrlPressed = true;
        updateModeVisuals();
        updateDesktopNumpadVisuals();
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        performUndo();
        return;
    }

    if (userState.selected && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
        e.preventDefault();
        moveSelection(e.key);
        return;
    }

    if (e.key >= '0' && e.key <= '9') {
        inputNumber(e.key);
        highlightNumpadKey(e.key);
        return;
    }

    if (e.key === 'Backspace' || e.key === 'Delete') {
        inputNumber(null);
        highlightNumpadKey('delete');
        return;
    }
}

export function handleKeyUp(e) {
    if (e.key === 'Control') {
        userState.isCtrlPressed = false;
        updateModeVisuals();
        updateDesktopNumpadVisuals();
    }
}

export function handleNumpadInput(val) {
    const target = userState.selected;
    if (!target) return;

    const numpadModal = document.getElementById('numpad-modal');
    const isPencil = numpadModal.querySelector('.numpad').classList.contains('pencil-mode');

    if (isPencil) {
        inputNumber(val);
        updateNumpadVisuals();
    } else {
        inputNumber(val);
        closeNumpadModal();
    }
}

export function handleNumpadDelete() {
    const target = userState.selected;
    if (!target) return;

    const numpadModal = document.getElementById('numpad-modal');
    const isPencil = numpadModal.querySelector('.numpad').classList.contains('pencil-mode');

    if (isPencil) {
        inputNumber(null);
        updateNumpadVisuals();
    } else {
        inputNumber(null);
        closeNumpadModal();
    }
}

export function performUndo() {
    if (undoStack.length === 0) return;

    const action = undoStack.pop();
    const { row, col, prevVal, prevMarks } = action;

    userState.grid[row][col].val = prevVal;
    userState.grid[row][col].marks = new Set(prevMarks);
    userState.grid[row][col].isError = false;

    renderGrid();
    updateDesktopNumpadVisuals();
    savePuzzleState(currentDate, userState.grid, false);
}

export function handleNumpadUndo() {
    if (!canModalUndo()) return;

    performUndo();
    updateNumpadVisuals();
}

