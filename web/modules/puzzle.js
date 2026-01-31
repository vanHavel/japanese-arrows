import { puzzle, solution, userState, constants, currentDate, setCurrentDate, initUserState, clearUndoStack } from './state.js';
import { renderGrid, updateDesktopNumpadVisuals } from './render.js';
import { loadPuzzleState, clearPuzzleState, markPuzzleSolved, savePuzzleState } from './storage.js';

export function parsePuzzle(text) {
    const lines = text.trim().split('\n');
    const contentLines = lines.filter(l => l.trim().startsWith('|'));

    puzzle.rows = contentLines.length;
    const firstLineParts = contentLines[0].trim().split('|').filter(p => p.length > 0);
    puzzle.cols = firstLineParts.length;

    puzzle.grid = [];

    for (let r = 0; r < puzzle.rows; r++) {
        const rowData = [];
        const parts = contentLines[r].trim().split('|').filter(p => p.length > 0);

        for (let c = 0; c < puzzle.cols; c++) {
            const cellStr = parts[c].trim();
            const arrowMatch = cellStr.match(/[↑↓←→↖↗↘↙]/);
            const valMatch = cellStr.match(/\d/);

            const arrow = arrowMatch ? arrowMatch[0] : '';
            const val = valMatch ? valMatch[0] : null;

            rowData.push({
                arrow: arrow,
                val: val,
                initial: val !== null
            });
        }
        puzzle.grid.push(rowData);
    }
}

export function parseSolution(text) {
    const lines = text.trim().split('\n');
    const contentLines = lines.filter(l => l.trim().startsWith('|'));

    solution.length = 0;
    for (let r = 0; r < contentLines.length; r++) {
        const rowSol = [];
        const parts = contentLines[r].trim().split('|').filter(p => p.length > 0);
        for (let c = 0; c < parts.length; c++) {
            const cellStr = parts[c].trim();
            const valMatch = cellStr.match(/\d/);
            rowSol.push(valMatch ? valMatch[0] : null);
        }
        solution.push(rowSol);
    }
}

export function updateDifficultyDisplay(difficulty) {
    const difficultyDisplay = document.getElementById('difficulty-display');
    difficultyDisplay.textContent = difficulty;
    difficultyDisplay.className = 'difficulty-badge';
    if (difficulty) {
        difficultyDisplay.classList.add(`diff-${difficulty.toLowerCase()}`);
    }
}

function restoreSavedState() {
    const saved = loadPuzzleState(currentDate);

    hideSolvedBadge();

    if (!saved) return;

    for (let r = 0; r < puzzle.rows; r++) {
        for (let c = 0; c < puzzle.cols; c++) {
            if (!puzzle.grid[r][c].initial) {
                userState.grid[r][c].val = saved.grid[r][c].val;
                userState.grid[r][c].marks = saved.grid[r][c].marks;
            }
        }
    }

    if (saved.solved) {
        showSolvedBadge();
    }
}

export async function loadPuzzle() {
    const puzzleGrid = document.getElementById('puzzle-grid');
    document.body.style.cursor = 'wait';
    try {
        const [y, m, d] = currentDate.split('-');
        const path = `/puzzles/${y}/${m}/${d}`;

        const [puzzleRes, solutionRes, metadataRes] = await Promise.all([
            fetch(`${path}/puzzle.txt`),
            fetch(`${path}/solution.txt`),
            fetch(`${path}/metadata.yaml`)
        ]);

        if (!puzzleRes.ok) throw new Error('Puzzle not found');
        if (!solutionRes.ok) throw new Error('Solution not found');

        const puzzleText = await puzzleRes.text();
        const solutionText = await solutionRes.text();

        let difficulty = 'Unknown';
        if (metadataRes.ok) {
            const metaText = await metadataRes.text();
            const match = metaText.match(/difficulty:\s*(.+)/i);
            if (match) {
                difficulty = match[1].trim();
            }
        }
        updateDifficultyDisplay(difficulty);

        parsePuzzle(puzzleText);
        parseSolution(solutionText);

        initUserState();
        clearUndoStack();
        restoreSavedState();
        renderGrid();
        updateDesktopNumpadVisuals();
    } catch (err) {
        console.error('Failed to load puzzle', err);

        puzzleGrid.style.gridTemplateColumns = '1fr';
        puzzleGrid.style.gridTemplateRows = 'auto';

        puzzleGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--error-color);">
                <h3>No Puzzle Found</h3>
                <p>There is no puzzle available for ${currentDate}.</p>
            </div>`;
    } finally {
        document.body.style.cursor = 'default';
    }
}

export function checkPuzzle() {
    let full = true;
    let incorrectFound = false;

    for (let r = 0; r < puzzle.rows; r++) {
        for (let c = 0; c < puzzle.cols; c++) {
            if (userState.grid[r][c].isError) {
                userState.grid[r][c].isError = false;
            }
        }
    }

    for (let r = 0; r < puzzle.rows; r++) {
        for (let c = 0; c < puzzle.cols; c++) {
            const val = userState.grid[r][c].val;
            if (val === null) {
                full = false;
            } else {
                if (String(val) !== String(solution[r][c])) {
                    incorrectFound = true;
                    userState.grid[r][c].isError = true;
                }
            }
        }
    }

    renderGrid();

    if (incorrectFound) {
        alert('Some answers are incorrect. They have been highlighted.');
    } else if (!full) {
        alert('The puzzle is incomplete, but all filled numbers are correct so far!');
    } else {
        savePuzzleState(currentDate, userState.grid, true);
        showSolvedBadge();
        alert('Congratulations! Puzzle Solved!');
    }
}

export function fillSolution() {
    for (let r = 0; r < puzzle.rows; r++) {
        for (let c = 0; c < puzzle.cols; c++) {
            if (!puzzle.grid[r][c].initial) {
                userState.grid[r][c].val = solution[r][c];
                userState.grid[r][c].marks.clear();
                userState.grid[r][c].isError = false;
            }
        }
    }
    clearUndoStack();
    renderGrid();
    updateDesktopNumpadVisuals();
    savePuzzleState(currentDate, userState.grid);
}

export function resetPuzzle() {
    clearPuzzleState(currentDate);
    hideSolvedBadge();
    initUserState();
    clearUndoStack();
    renderGrid();
    updateDesktopNumpadVisuals();
}

function showSolvedBadge() {
    const badge = document.getElementById('solved-badge');
    if (badge) badge.classList.remove('hidden');
}

function hideSolvedBadge() {
    const badge = document.getElementById('solved-badge');
    if (badge) badge.classList.add('hidden');
}

export function clearSolvedState() {
    hideSolvedBadge();
}

export function shareUrl() {
    const toast = document.getElementById('toast');
    const baseUrl = `${window.location.origin}${window.location.pathname}`;
    const url = `${baseUrl}?date=${currentDate}`;
    navigator.clipboard.writeText(url).then(() => {
        toast.classList.remove('hidden');
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 2000);
    });
}
