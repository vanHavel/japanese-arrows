import { puzzle, userState } from './state.js';

export function getArrowSvg(arrowChar) {
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

export function renderGrid() {
    const puzzleGrid = document.getElementById('puzzle-grid');
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

            cell.onclick = () => {
                import('./input.js').then(m => m.selectCell(r, c));
            };

            cell.onmouseenter = () => {
                userState.hovered = { r, c };
            };
            cell.onmouseleave = () => {
                if (userState.hovered && userState.hovered.r === r && userState.hovered.c === c) {
                    userState.hovered = null;
                }
            };

            const arrowDiv = document.createElement('div');
            arrowDiv.className = 'arrow';
            arrowDiv.innerHTML = getArrowSvg(cellData.arrow);
            cell.appendChild(arrowDiv);

            if (stateData.val !== null) {
                const valDiv = document.createElement('div');
                valDiv.className = 'cell-value';
                valDiv.textContent = stateData.val;
                if (cellData.initial) valDiv.classList.add('initial');
                if (stateData.isError) valDiv.classList.add('error');
                cell.appendChild(valDiv);
            } else {
                if (stateData.marks.size > 0) {
                    const marksDiv = document.createElement('div');
                    marksDiv.className = 'pencil-marks';
                    for (let i = 1; i <= 9; i++) {
                        const markSpan = document.createElement('div');
                        markSpan.className = 'pencil-mark';
                        markSpan.textContent = stateData.marks.has(String(i)) || stateData.marks.has(i) ? i : '';
                        marksDiv.appendChild(markSpan);
                    }
                    cell.appendChild(marksDiv);
                }
            }

            puzzleGrid.appendChild(cell);
        }
    }
}

export function updateNumpadVisuals() {
    const numpadModal = document.getElementById('numpad-modal');
    const numBtns = numpadModal.querySelectorAll('.mobile-num-btn.num-btn');
    numBtns.forEach(btn => btn.classList.remove('active'));

    const target = userState.selected;
    if (!target) return;
    const { r, c } = target;

    const isPencil = numpadModal.querySelector('.numpad').classList.contains('pencil-mode');
    if (!isPencil) return;

    const marks = userState.grid[r][c].marks;
    numBtns.forEach(btn => {
        const val = btn.getAttribute('data-value');
        if (marks.has(val) || marks.has(Number(val))) {
            btn.classList.add('active');
        }
    });
}
