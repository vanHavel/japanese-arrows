document.addEventListener('DOMContentLoaded', () => {
    // Constants
    // Date Logic
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const TODAY_ISO = `${yyyy}-${mm}-${dd}`;

    const DEFAULT_DATE = TODAY_ISO; // Default to today
    const MIN_DATE = '2026-01-24'; // Earliest available puzzle
    const MAX_DATE = TODAY_ISO;

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

    // Numpad Undo Stack (for pencil mode)
    let numpadUndoStack = []; // Stores Set() copies

    // DOM Elements
    const puzzleGrid = document.getElementById('puzzle-grid');
    const numParams = document.querySelectorAll('.num-btn:not(.mobile-num-btn)');
    const deleteBtn = document.getElementById('numpad-delete');

    const modePenBtn = document.getElementById('mode-pen');
    const modePencilBtn = document.getElementById('mode-pencil');
    const modePenBtnDesktop = document.getElementById('mode-pen-desktop');
    const modePencilBtnDesktop = document.getElementById('mode-pencil-desktop');

    const resetBtn = document.getElementById('btn-reset');
    const shareBtn = document.getElementById('btn-share');
    const fillSolutionBtn = document.getElementById('btn-fill-solution');
    const checkBtn = document.getElementById('btn-check');

    const toggleGridBtn = document.getElementById('toggle-grid');
    const toggleGridBtnDesktop = document.getElementById('toggle-grid-desktop');

    const toast = document.getElementById('toast');

    // Navigation Elements
    const prevDayBtn = document.getElementById('prev-day');
    const nextDayBtn = document.getElementById('next-day');
    const currentDateDisplay = document.getElementById('current-date');
    const difficultyDisplay = document.getElementById('difficulty-display');

    // Modal Elements
    const resetModal = document.getElementById('reset-modal');
    const btnCancelReset = document.getElementById('btn-cancel-reset');
    const btnConfirmReset = document.getElementById('btn-confirm-reset');

    const numpadModal = document.getElementById('numpad-modal');
    const btnCloseNumpad = document.getElementById('btn-close-numpad');
    const mobileNumBtns = document.querySelectorAll('.mobile-num-btn');

    // Initialization
    initNavigation();
    loadPuzzle();

    // Event Listeners
    modePenBtn.addEventListener('click', () => setMode('pen'));
    modePencilBtn.addEventListener('click', () => setMode('pencil'));
    modePenBtnDesktop.addEventListener('click', () => setMode('pen'));
    modePencilBtnDesktop.addEventListener('click', () => setMode('pencil'));

    toggleGridBtn.addEventListener('click', () => {
        puzzleGrid.classList.toggle('show-grid');
        toggleGridBtn.classList.toggle('active');
        toggleGridBtnDesktop.classList.toggle('active');
    });

    toggleGridBtnDesktop.addEventListener('click', () => {
        puzzleGrid.classList.toggle('show-grid');
        toggleGridBtn.classList.toggle('active');
        toggleGridBtnDesktop.classList.toggle('active');
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

    // Mobile Numpad Events
    btnCloseNumpad.addEventListener('click', closeNumpadModal);
    numpadModal.addEventListener('click', (e) => {
        if (e.target === numpadModal) closeNumpadModal();
    });

    mobileNumBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const val = btn.getAttribute('data-value');

            // Special handling for undo
            if (val === 'undo') {
                handleNumpadUndo();
                return;
            }

            if (val === 'delete') {
                handleNumpadDelete();
            } else {
                // Number input
                handleNumpadInput(val);
            }
        });
    });

    shareBtn.addEventListener('click', shareUrl);
    fillSolutionBtn.addEventListener('click', fillSolution);
    checkBtn.addEventListener('click', checkPuzzle);

    // Navigation Events
    prevDayBtn.addEventListener('click', () => navigateDay(-1));
    nextDayBtn.addEventListener('click', () => navigateDay(1));

    // Functions

    function initNavigation() {
        updateDateDisplay();
        updateNavigationButtons();
    }

    function updateDifficultyDisplay(difficulty) {
        difficultyDisplay.textContent = difficulty;
        // Reset classes
        difficultyDisplay.className = 'difficulty-badge';
        if (difficulty) {
            difficultyDisplay.classList.add(`diff-${difficulty.toLowerCase()}`);
        }
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
        document.body.style.cursor = 'wait';
        try {
            // Construct path from currentDate
            const [y, m, d] = currentDate.split('-');
            const path = `/puzzles/${y}/${m}/${d}`;

            // Fetch data before clearing grid to avoid flash
            const [puzzleRes, solutionRes, metadataRes] = await Promise.all([
                fetch(`${path}/puzzle.txt`),
                fetch(`${path}/solution.txt`),
                fetch(`${path}/metadata.yaml`)
            ]);

            if (!puzzleRes.ok) throw new Error('Puzzle not found');
            if (!solutionRes.ok) throw new Error('Solution not found');

            const puzzleText = await puzzleRes.text();
            const solutionText = await solutionRes.text();

            // Parse Metadata if available
            let difficulty = 'Unknown';
            if (metadataRes.ok) {
                const metaText = await metadataRes.text();
                // simple parse: "difficulty: Value"
                const match = metaText.match(/difficulty:\s*(.+)/i);
                if (match) {
                    difficulty = match[1].trim();
                }
            }
            updateDifficultyDisplay(difficulty);

            parsePuzzle(puzzleText);
            parseSolution(solutionText);

            initUserState();
            renderGrid();
        } catch (err) {
            console.error('Failed to load puzzle', err);

            // Reset grid layout for error message
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
                        if (stateData.marks.has('0') || stateData.marks.has(0)) {
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

        // Only open numpad modal on touch devices
        if (window.matchMedia("(pointer: coarse)").matches) {
            // Only if editable
            if (!puzzle.grid[r][c].initial) {
                // Find the cell element to position the modal
                const cells = puzzleGrid.querySelectorAll('.cell');
                const cellElement = cells[r * puzzle.cols + c];
                openNumpadModal(cellElement);
            }
        }
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
            modePenBtnDesktop.classList.remove('active');
            modePencilBtnDesktop.classList.add('active');
        } else {
            // Normal state
            modePenBtn.classList.toggle('active', userState.mode === 'pen');
            modePencilBtn.classList.toggle('active', userState.mode === 'pencil');
            modePenBtnDesktop.classList.toggle('active', userState.mode === 'pen');
            modePencilBtnDesktop.classList.toggle('active', userState.mode === 'pencil');
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
            highlightNumpadKey(e.key);
            return;
        }

        // Delete
        if (e.key === 'Backspace' || e.key === 'Delete') {
            inputNumber(null);
            highlightNumpadKey('delete');
            return;
        }
    }

    function handleKeyUp(e) {
        if (e.key === 'Control') {
            userState.isCtrlPressed = false;
            updateModeVisuals();
        }
    }

    function highlightNumpadKey(val) {
        // Desktop numpad only (numParams selects desktop buttons)
        let btn = null;
        if (val === 'delete') {
            btn = document.getElementById('numpad-delete');
        } else {
            // Find by data-value
            // numParams is a NodeList of desktop num buttons
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

    function moveSelection(key) {
        let { r, c } = userState.selected;
        if (key === 'ArrowUp') r = Math.max(0, r - 1);
        if (key === 'ArrowDown') r = Math.min(puzzle.rows - 1, r + 1);
        if (key === 'ArrowLeft') c = Math.max(0, c - 1);
        if (key === 'ArrowRight') c = Math.min(puzzle.cols - 1, c + 1);
        selectCell(r, c);
    }

    function inputNumber(val) {
        // Prioritize selected cell, then hovered cell
        const target = userState.selected || userState.hovered;
        if (!target) return;

        const { r, c } = target;

        // Check if locked
        if (puzzle.grid[r][c].initial) return;

        const effectiveMode = (userState.isCtrlPressed && userState.mode === 'pen') ? 'pencil' : userState.mode;

        if (val === null) {
            userState.grid[r][c].val = null;
            userState.grid[r][c].marks.clear();
        } else {
            if (effectiveMode === 'pen') {
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
                userState.grid[r][c].val = null;
                userState.grid[r][c].isError = false;
            }
        }
        renderGrid();
    }

    function resetPuzzle() {
        initUserState();
        renderGrid();
    }

    function fillSolution() {
        for (let r = 0; r < puzzle.rows; r++) {
            for (let c = 0; c < puzzle.cols; c++) {
                if (!puzzle.grid[r][c].initial) {
                    userState.grid[r][c].val = solution[r][c];
                    userState.grid[r][c].marks.clear();
                    userState.grid[r][c].isError = false;
                }
            }
        }
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

    function openNumpadModal(anchorElement) {
        // Prevent immediate input registration (ghost clicks)
        numpadModal.style.pointerEvents = 'none';
        setTimeout(() => {
            numpadModal.style.pointerEvents = 'auto';
        }, 300);

        // Reset undo stack
        numpadUndoStack = [];

        const isPencil = (userState.mode === 'pencil') || (userState.isCtrlPressed && userState.mode === 'pen');
        const numpadDiv = numpadModal.querySelector('.numpad');

        // Update UI for mode
        if (isPencil) {
            numpadDiv.classList.add('pencil-mode');
            numpadModal.querySelector('.undo-btn').classList.remove('hidden');
            btnCloseNumpad.textContent = 'Done'; // Changed from Cancel to Done/Confirm
            // Hide 0 button in pencil mode
            const btnZero = numpadModal.querySelector('.mobile-num-btn[data-value="0"]');
            if (btnZero) btnZero.classList.add('hidden');
        } else {
            numpadDiv.classList.remove('pencil-mode');
            numpadModal.querySelector('.undo-btn').classList.add('hidden');
            btnCloseNumpad.textContent = 'Cancel';
            // Show 0 button in pen mode
            const btnZero = numpadModal.querySelector('.mobile-num-btn[data-value="0"]');
            if (btnZero) btnZero.classList.remove('hidden');
        }

        const modalContent = numpadModal.querySelector('.modal-content');
        numpadModal.classList.remove('hidden');

        if (anchorElement) {
            const rect = anchorElement.getBoundingClientRect();
            const modalRect = modalContent.getBoundingClientRect();
            const gap = 10;
            const padding = 10;

            let top, left;

            // Try to position below the cell first
            const topBelow = rect.bottom + gap;
            const fitsBelow = topBelow + modalRect.height <= window.innerHeight - padding;

            // Try to position above the cell if below doesn't fit
            const topAbove = rect.top - gap - modalRect.height;
            const fitsAbove = topAbove >= padding;

            if (fitsBelow) {
                // Position below
                top = topBelow;
            } else if (fitsAbove) {
                // Position above
                top = topAbove;
            } else {
                // If neither fits perfectly, prefer above for bottom cells, below for top cells
                const cellVerticalCenter = rect.top + rect.height / 2;
                const viewportCenter = window.innerHeight / 2;

                if (cellVerticalCenter > viewportCenter) {
                    // Cell is in bottom half - position above and allow it to go to edge
                    top = Math.max(padding, topAbove);
                } else {
                    // Cell is in top half - position below
                    top = Math.min(topBelow, window.innerHeight - modalRect.height - padding);
                }
            }

            // Center horizontally relative to cell
            left = rect.left + rect.width / 2 - modalRect.width / 2;

            // Constrain horizontal position
            left = Math.max(padding, Math.min(left, window.innerWidth - modalRect.width - padding));

            modalContent.style.position = 'fixed';
            modalContent.style.top = `${top}px`;
            modalContent.style.left = `${left}px`;
            modalContent.style.margin = '0';
        }

        // Initial visual update
        updateNumpadVisuals();
    }

    function handleNumpadInput(val) {
        const target = userState.selected;
        if (!target) return;
        const { r, c } = target;

        const isPencil = numpadModal.querySelector('.numpad').classList.contains('pencil-mode');

        if (isPencil) {
            // Save state *before* modification
            const currentMarks = new Set(userState.grid[r][c].marks);
            numpadUndoStack.push(currentMarks);

            inputNumber(val); // Logic handles toggling
            // Do NOT close modal
            updateNumpadVisuals();
        } else {
            inputNumber(val);
            closeNumpadModal();
        }
    }

    function handleNumpadDelete() {
        const target = userState.selected;
        if (!target) return;
        const { r, c } = target;

        const isPencil = numpadModal.querySelector('.numpad').classList.contains('pencil-mode');

        if (isPencil) {
            // Save state *before* clearing
            const currentMarks = new Set(userState.grid[r][c].marks);
            numpadUndoStack.push(currentMarks);

            userState.grid[r][c].marks.clear();
            userState.grid[r][c].val = null;
            userState.grid[r][c].isError = false;
            userState.grid[r][c].val = null;
            userState.grid[r][c].isError = false;
            renderGrid();
            updateNumpadVisuals();
        } else {
            inputNumber(null);
            closeNumpadModal();
        }
    }

    function handleNumpadUndo() {
        if (numpadUndoStack.length === 0) return;

        const target = userState.selected;
        if (!target) return;
        const { r, c } = target;

        const prevMarks = numpadUndoStack.pop();
        userState.grid[r][c].marks = new Set(prevMarks);
        // Ensure no value overrides marks
        if (userState.grid[r][c].marks.size > 0) {
            userState.grid[r][c].val = null;
        }
        renderGrid();
        updateNumpadVisuals();
    }

    function updateNumpadVisuals() {
        // Clear all active states first
        const numBtns = numpadModal.querySelectorAll('.mobile-num-btn.num-btn');
        numBtns.forEach(btn => btn.classList.remove('active'));

        const target = userState.selected;
        if (!target) return;
        const { r, c } = target;

        // Check if pencil mode
        const isPencil = numpadModal.querySelector('.numpad').classList.contains('pencil-mode');
        if (!isPencil) return;

        // Highlight marks
        const marks = userState.grid[r][c].marks;
        numBtns.forEach(btn => {
            const val = btn.getAttribute('data-value');
            if (marks.has(val) || marks.has(Number(val))) {
                btn.classList.add('active');
            }
        });
    }

    function closeNumpadModal() {
        // Prevent ghost clicks on underlying buttons
        const rightControls = document.querySelector('.right-controls');
        if (rightControls) {
            rightControls.style.pointerEvents = 'none';
            setTimeout(() => {
                rightControls.style.pointerEvents = 'auto';
            }, 300);
        }

        numpadModal.classList.add('hidden');

        // Clear active highlights immediately
        const numBtns = numpadModal.querySelectorAll('.mobile-num-btn.num-btn');
        numBtns.forEach(btn => btn.classList.remove('active'));

        // Deselect cell when closing modal (for better mobile UX)
        if (userState.selected) {
            userState.selected = null;
            renderGrid();
        }
    }

});
