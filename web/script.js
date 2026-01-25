document.addEventListener('DOMContentLoaded', () => {
    // Constants
    const PUZZLE_DATE_PATH = '/puzzles/2026/01/25'; // Fixed for v1
    const GRID_SIZE = 500; // Max width in px

    // State
    let puzzle = {
        rows: 0,
        cols: 0,
        grid: [], // Contains {arrow: 'dir', val: 'num'|null, initial: bool}
    };
    let solution = []; // 2D array of solution values
    let userState = {
        grid: [], // Contains {val: 'num'|null, marks: Set()}
        selected: null, // {r, c}
        hovered: null, // {r, c}
        mode: 'pen', // 'pen' | 'pencil'
        isCtrlPressed: false,
    };

    // DOM Elements
    const puzzleGrid = document.getElementById('puzzle-grid');
    const numParams = document.querySelectorAll('.num-btn');
    const deleteBtn = document.getElementById('numpad-delete');
    const modePenBtn = document.getElementById('mode-pen');
    const modePencilBtn = document.getElementById('mode-pencil');
    const resetBtn = document.getElementById('btn-reset');
    const shareBtn = document.getElementById('btn-share');
    const toast = document.getElementById('toast');

    // Modal Elements
    const resetModal = document.getElementById('reset-modal');
    const btnCancelReset = document.getElementById('btn-cancel-reset');
    const btnConfirmReset = document.getElementById('btn-confirm-reset');

    // Initialization
    loadPuzzle();

    // Event Listeners
    modePenBtn.addEventListener('click', () => setMode('pen'));
    modePencilBtn.addEventListener('click', () => setMode('pencil'));

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);

    numParams.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const val = e.target.getAttribute('data-value');
            inputNumber(val);
        });
    });

    deleteBtn.addEventListener('click', () => inputNumber(null));

    // Reset Flow
    resetBtn.addEventListener('click', () => {
        resetModal.classList.remove('hidden');
    });
    btnCancelReset.addEventListener('click', () => {
        resetModal.classList.add('hidden');
    });
    btnConfirmReset.addEventListener('click', () => {
        resetModal.classList.add('hidden');
        resetPuzzle();
    });
    // Close modal on outside click
    resetModal.addEventListener('click', (e) => {
        if (e.target === resetModal) {
            resetModal.classList.add('hidden');
        }
    });

    shareBtn.addEventListener('click', shareUrl);

    // Functions

    async function loadPuzzle() {
        try {
            // Fetch puzzle.txt
            const puzzleRes = await fetch(`${PUZZLE_DATE_PATH}/puzzle.txt`);
            const puzzleText = await puzzleRes.text();

            // Fetch solution.txt
            const solutionRes = await fetch(`${PUZZLE_DATE_PATH}/solution.txt`);
            const solutionText = await solutionRes.text();

            parsePuzzle(puzzleText);
            parseSolution(solutionText);

            initUserState();
            renderGrid();
        } catch (err) {
            console.error('Failed to load puzzle', err);
            alert('Error loading puzzle data.');
        }
    }

    function parsePuzzle(text) {
        // Parse the ASCII format
        // +----+
        // | ↓. |
        // +----+
        const lines = text.trim().split('\n');

        // Filter out separator lines (start with +)
        const contentLines = lines.filter(l => l.trim().startsWith('|'));

        puzzle.rows = contentLines.length;
        // Determine cols from first line: "| ↓. | →. |" -> split by "|"
        const firstLineParts = contentLines[0].trim().split('|').filter(p => p.length > 0);
        puzzle.cols = firstLineParts.length;

        puzzle.grid = [];

        for (let r = 0; r < puzzle.rows; r++) {
            const rowData = [];
            const parts = contentLines[r].trim().split('|').filter(p => p.length > 0);

            for (let c = 0; c < puzzle.cols; c++) {
                const cellStr = parts[c].trim(); // e.g., "↓." or "↓3" or "←."
                // Format seems to be ArrowChar + (Digit or Dot) usually 2 chars, or space padded?
                // Based on zeiger_1.txt: " ↓. " (padded)

                // Let's extract based on regex or simplified parsing
                // Assuming standard arrow chars and possibly numbers
                // Arrow chars: ↑ ↓ ← → ↖ ↗ ↘ ↙

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

    function parseSolution(text) {
        // Similar parsing, but we only care about the values
        const lines = text.trim().split('\n');
        const contentLines = lines.filter(l => l.trim().startsWith('|'));

        solution = [];
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

    function initUserState() {
        userState.grid = [];
        for (let r = 0; r < puzzle.rows; r++) {
            const row = [];
            for (let c = 0; c < puzzle.cols; c++) {
                row.push({
                    val: puzzle.grid[r][c].val, // Pre-fill initial values
                    marks: new Set()
                });
            }
            userState.grid.push(row);
        }
    }

    function renderGrid() {
        puzzleGrid.style.gridTemplateColumns = `repeat(${puzzle.cols}, 1fr)`;
        puzzleGrid.style.gridTemplateRows = `repeat(${puzzle.rows}, 1fr)`;
        puzzleGrid.innerHTML = '';

        for (let r = 0; r < puzzle.rows; r++) {
            for (let c = 0; c < puzzle.cols; c++) {
                const cellData = puzzle.grid[r][c];
                const stateData = userState.grid[r][c];

                const cell = document.createElement('div');
                cell.className = 'cell';
                if (userState.selected && userState.selected.r === r && userState.selected.c === c) {
                    cell.classList.add('selected');
                }

                cell.onclick = () => selectCell(r, c);

                // Track hovering
                cell.onmouseenter = () => {
                    userState.hovered = { r, c };
                };
                cell.onmouseleave = () => {
                    // Only clear if we are still hovering this exact cell (sanity check)
                    if (userState.hovered && userState.hovered.r === r && userState.hovered.c === c) {
                        userState.hovered = null;
                    }
                };

                // Draw Arrow (SVG)
                const arrowDiv = document.createElement('div');
                arrowDiv.className = 'arrow';
                arrowDiv.innerHTML = getArrowSvg(cellData.arrow);
                cell.appendChild(arrowDiv);

                // Draw Value
                if (stateData.val !== null) {
                    const valDiv = document.createElement('div');
                    valDiv.className = 'cell-value';
                    valDiv.textContent = stateData.val;
                    if (cellData.initial) valDiv.classList.add('initial');
                    cell.appendChild(valDiv);
                } else {
                    // Draw Pencil Marks
                    if (stateData.marks.size > 0) {
                        const marksDiv = document.createElement('div');
                        marksDiv.className = 'pencil-marks';
                        // 1-9 positions
                        for (let i = 1; i <= 9; i++) {
                            const markSpan = document.createElement('div');
                            markSpan.className = 'pencil-mark';
                            markSpan.textContent = stateData.marks.has(String(i)) || stateData.marks.has(i) ? i : '';
                            marksDiv.appendChild(markSpan);
                        }
                        // 0 is usually not used in pencil marks in standard sudoku-like logic but here values are 0-9?
                        // zeiger_1 has 0-9? 
                        // Wait, puzzle usually has digits. If 0 is possible, we need space for it.
                        // Standard 3x3 grid fits 1-9. Where to put 0?
                        // Maybe top or center? For now let's assume 1-9 pencil marks. 
                        // If 0 is valid, we might need a different layout or just ignore 0 for pencil.
                        // Let's add 0 to the set check but maybe it won't be shown nicely in 3x3.
                        // Handle 0 key specifically? 
                        if (stateData.marks.has('0') || stateData.marks.has(0)) {
                            // Maybe overlay it or put it in position 5?
                            // For simplicity: just 1-9 for now in grid. 
                        }

                        cell.appendChild(marksDiv);
                    }
                }

                puzzleGrid.appendChild(cell);
            }
        }
    }

    function getArrowSvg(arrowChar) {
        // Map char to rotation
        const rotations = { '↑': 0, '↗': 45, '→': 90, '↘': 135, '↓': 180, '↙': 225, '←': 270, '↖': 315 };
        const rot = rotations[arrowChar] ?? 0;

        // Simple arrow path
        return `<svg viewBox="0 0 24 24" style="transform: rotate(${rot}deg)">
            <line x1="12" y1="19" x2="12" y2="5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <polyline points="5 12 12 5 19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
        </svg>`;
    }

    function selectCell(r, c) {
        userState.selected = { r, c };
        renderGrid();
    }

    function setMode(mode) {
        userState.mode = mode;
        updateModeVisuals();
    }

    function updateModeVisuals() {
        if (userState.isCtrlPressed && userState.mode === 'pen') {
            // Temporary pencil mode
            modePenBtn.classList.remove('active');
            modePencilBtn.classList.add('active');
        } else {
            // Normal state
            modePenBtn.classList.toggle('active', userState.mode === 'pen');
            modePencilBtn.classList.toggle('active', userState.mode === 'pencil');
        }
    }

    function handleKeyDown(e) {
        if (e.key === 'Control') {
            userState.isCtrlPressed = true;
            updateModeVisuals();
        }

        // Navigation (only if selected)
        if (userState.selected && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
            e.preventDefault();
            moveSelection(e.key);
            return;
        }

        // Numbers
        if (e.key >= '0' && e.key <= '9') {
            inputNumber(e.key);
            return;
        }

        // Delete
        if (e.key === 'Backspace' || e.key === 'Delete') {
            inputNumber(null);
            return;
        }
    }

    function handleKeyUp(e) {
        if (e.key === 'Control') {
            userState.isCtrlPressed = false;
            updateModeVisuals();
        }
    }

    function moveSelection(key) {
        let { r, c } = userState.selected;
        if (key === 'ArrowUp') r = Math.max(0, r - 1);
        if (key === 'ArrowDown') r = Math.min(puzzle.rows - 1, r + 1);
        if (key === 'ArrowLeft') c = Math.max(0, c - 1);
        if (key === 'ArrowRight') c = Math.min(puzzle.cols - 1, c + 1);
        selectCell(r, c);
    }

    function inputNumber(val) {
        // Prioritize hovered cell, then selected cell
        const target = userState.hovered || userState.selected;
        if (!target) return;

        const { r, c } = target;

        // Check if locked
        if (puzzle.grid[r][c].initial) return;

        const effectiveMode = (userState.isCtrlPressed && userState.mode === 'pen') ? 'pencil' : userState.mode;

        if (val === null) {
            // Delete action
            // If has value, clear value.
            // If no value but marks, clear marks? 
            userState.grid[r][c].val = null;
            userState.grid[r][c].marks.clear();
        } else {
            if (effectiveMode === 'pen') {
                // Set value, clear marks
                userState.grid[r][c].val = val;
                userState.grid[r][c].marks.clear();

                checkCompletion();
            } else {
                // Toggle mark
                if (userState.grid[r][c].marks.has(val)) {
                    userState.grid[r][c].marks.delete(val);
                } else {
                    userState.grid[r][c].marks.add(val);
                }
                // Don't clear value if pencil marking? usually one or other.
                // If value exists, pencil marks are usually hidden or disabled.
                // Let's clear value if adding marks to avoid confusion.
                userState.grid[r][c].val = null;
            }
        }
        renderGrid();
    }

    function resetPuzzle() {
        initUserState();
        renderGrid();
    }

    function checkCompletion() {
        // Check if all cells filled
        let full = true;
        let correct = true;

        for (let r = 0; r < puzzle.rows; r++) {
            for (let c = 0; c < puzzle.cols; c++) {
                const val = userState.grid[r][c].val;
                if (val === null) {
                    full = false;
                    break;
                }
                if (String(val) !== String(solution[r][c])) {
                    correct = false;
                }
            }
        }

        if (full) {
            if (correct) {
                setTimeout(() => alert('Congratulations! Puzzle Solved!'), 100);
            } else {
                // Optional: Visual feedback for error?
                setTimeout(() => alert('Keep trying! Something is not quite right.'), 100);
            }
        }
    }

    function shareUrl() {
        const url = window.location.href;
        navigator.clipboard.writeText(url).then(() => {
            toast.classList.remove('hidden');
            setTimeout(() => {
                toast.classList.add('hidden');
            }, 2000);
        });
    }

});
