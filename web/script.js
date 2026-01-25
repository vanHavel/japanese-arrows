document.addEventListener('DOMContentLoaded', () => {
    // Constants
    const DEFAULT_DATE = '2026-01-25'; // Default to today/latest
    const MIN_DATE = '2026-01-24'; // Earliest available puzzle

    // Determine MAX_DATE dynamically based on user's today, clamped to the latest known puzzle date if we want strictly served puzzles.
    // However, the user said "Max date can be based on today". So we'll use today's date.
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const MAX_DATE = `${yyyy}-${mm}-${dd}`;

    const GRID_SIZE = 500; // Max width in px

    // State
    let currentDate = new URLSearchParams(window.location.search).get('date') || DEFAULT_DATE;
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
    const checkBtn = document.getElementById('btn-check');
    const toggleGridBtn = document.getElementById('toggle-grid');
    const toast = document.getElementById('toast');

    // Navigation Elements
    const prevDayBtn = document.getElementById('prev-day');
    const nextDayBtn = document.getElementById('next-day');
    const currentDateDisplay = document.getElementById('current-date');

    // Modal Elements
    const resetModal = document.getElementById('reset-modal');
    const btnCancelReset = document.getElementById('btn-cancel-reset');
    const btnConfirmReset = document.getElementById('btn-confirm-reset');

    // Initialization
    initNavigation();
    loadPuzzle();

    // Event Listeners
    modePenBtn.addEventListener('click', () => setMode('pen'));
    modePencilBtn.addEventListener('click', () => setMode('pencil'));

    toggleGridBtn.addEventListener('click', () => {
        puzzleGrid.classList.toggle('show-grid');
        toggleGridBtn.classList.toggle('active');
    });

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
    checkBtn.addEventListener('click', checkPuzzle);

    // Navigation Events
    prevDayBtn.addEventListener('click', () => navigateDay(-1));
    nextDayBtn.addEventListener('click', () => navigateDay(1));

    // Functions

    function initNavigation() {
        updateDateDisplay();
        updateNavigationButtons();
    }

    function updateDateDisplay() {
        const dateObj = new Date(currentDate);
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        currentDateDisplay.textContent = dateObj.toLocaleDateString('en-US', options);
    }

    function updateNavigationButtons() {
        prevDayBtn.disabled = currentDate <= MIN_DATE;
        nextDayBtn.disabled = currentDate >= MAX_DATE;
    }

    function navigateDay(delta) {
        const dateObj = new Date(currentDate);
        dateObj.setDate(dateObj.getDate() + delta);

        const y = dateObj.getFullYear();
        const m = String(dateObj.getMonth() + 1).padStart(2, '0');
        const d = String(dateObj.getDate()).padStart(2, '0');

        currentDate = `${y}-${m}-${d}`;

        // Update URL without reload
        const newUrl = `${window.location.pathname}?date=${currentDate}`;
        window.history.pushState({ path: newUrl }, '', newUrl);

        updateDateDisplay();
        updateNavigationButtons();
        loadPuzzle();
    }

    async function loadPuzzle() {
        try {
            // Construct path from currentDate
            const [y, m, d] = currentDate.split('-');
            const path = `/puzzles/${y}/${m}/${d}`;

            // Clear current grid to avoid artifacts during load
            puzzleGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem;">Loading...</div>';

            // Fetch puzzle.txt
            const puzzleRes = await fetch(`${path}/puzzle.txt`);
            if (!puzzleRes.ok) throw new Error('Puzzle not found');
            const puzzleText = await puzzleRes.text();

            // Fetch solution.txt
            const solutionRes = await fetch(`${path}/solution.txt`);
            if (!solutionRes.ok) throw new Error('Solution not found');
            const solutionText = await solutionRes.text();

            parsePuzzle(puzzleText);
            parseSolution(solutionText);

            initUserState();
            renderGrid();
        } catch (err) {
            console.error('Failed to load puzzle', err);
            puzzleGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--error-color);">
                    <h3>No Puzzle Found</h3>
                    <p>There is no puzzle available for ${currentDate}.</p>
                </div>`;
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
                    if (stateData.isError) valDiv.classList.add('error'); // Highlight error
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
        const fileMap = {
            '↑': 'arrow_NORTH.svg',
            '↗': 'arrow_NORTH_EAST.svg',
            '→': 'arrow_EAST.svg',
            '↘': 'arrow_SOUTH_EAST.svg',
            '↓': 'arrow_SOUTH.svg',
            '↙': 'arrow_SOUTH_WEST.svg',
            '←': 'arrow_WEST.svg',
            '↖': 'arrow_NORTH_WEST.svg'
        };
        const filename = fileMap[arrowChar];
        if (!filename) return '';
        return `<img src="/assets/arrows/${filename}" alt="${arrowChar}" draggable="false" />`;
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
                // Clear error state on new input
                if (userState.grid[r][c].isError) {
                    userState.grid[r][c].isError = false;
                }
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
                userState.grid[r][c].isError = false; // Clear error
            }
        }
        renderGrid();
    }

    function resetPuzzle() {
        initUserState();
        renderGrid();
    }

    function checkPuzzle() {
        // Check manually triggered
        let full = true;
        let incorrectFound = false;
        let correctCount = 0;
        let totalCells = puzzle.rows * puzzle.cols;

        // Reset previous errors
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
                    } else {
                        correctCount++;
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
            alert('Congratulations! Puzzle Solved!');
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
