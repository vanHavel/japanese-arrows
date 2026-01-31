import { puzzle, userState, numpadUndoStack, currentDate } from './state.js';
import { renderGrid, updateNumpadVisuals, updateDesktopNumpadVisuals } from './render.js';
import { openNumpadModal, closeNumpadModal } from './modals.js';
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
    const { r, c } = target;

    const numpadModal = document.getElementById('numpad-modal');
    const isPencil = numpadModal.querySelector('.numpad').classList.contains('pencil-mode');

    if (isPencil) {
        const currentMarks = new Set(userState.grid[r][c].marks);
        numpadUndoStack.push(currentMarks);

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
    const { r, c } = target;

    const numpadModal = document.getElementById('numpad-modal');
    const isPencil = numpadModal.querySelector('.numpad').classList.contains('pencil-mode');

    if (isPencil) {
        const currentMarks = new Set(userState.grid[r][c].marks);
        numpadUndoStack.push(currentMarks);

        userState.grid[r][c].marks.clear();
        userState.grid[r][c].val = null;
        userState.grid[r][c].isError = false;
        renderGrid();
        updateNumpadVisuals();
        savePuzzleState(currentDate, userState.grid);
    } else {
        inputNumber(null);
        closeNumpadModal();
    }
}

export function handleNumpadUndo() {
    if (numpadUndoStack.length === 0) return;

    const target = userState.selected;
    if (!target) return;
    const { r, c } = target;

    const prevMarks = numpadUndoStack.pop();
    userState.grid[r][c].marks = new Set(prevMarks);
    if (userState.grid[r][c].marks.size > 0) {
        userState.grid[r][c].val = null;
    }
    renderGrid();
    updateNumpadVisuals();
    savePuzzleState(currentDate, userState.grid);
}
