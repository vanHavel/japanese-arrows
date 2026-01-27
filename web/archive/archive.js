document.addEventListener('DOMContentLoaded', async () => {
    const archiveList = document.getElementById('archive-list');
    const loadingMsg = document.getElementById('loading-msg');
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    const pageInfo = document.getElementById('page-info');
    const headers = document.querySelectorAll('th[data-sort]');

    // Filter Elements
    const filterDiff = document.getElementById('filter-difficulty');
    const filterSize = document.getElementById('filter-size');
    const filterArrows = document.getElementById('filter-arrows');

    // State
    let allPuzzles = [];
    let filteredPuzzles = [];
    let sortField = 'date';
    let sortDir = 'desc'; // 'asc' or 'desc'
    let currentPage = 1;
    const itemsPerPage = 10;

    try {
        const response = await fetch('/assets/puzzles.json');
        if (!response.ok) throw new Error('Failed to load archive');

        allPuzzles = await response.json();
        loadingMsg.classList.add('hidden');

        updateFilteredPuzzles();
    } catch (err) {
        console.error(err);
        loadingMsg.textContent = 'Failed to load archive data.';
        loadingMsg.classList.add('error');
    }

    // Event Listeners
    headers.forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (sortField === field) {
                sortDir = sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                sortField = field;
                sortDir = 'desc';
                if (field === 'date') sortDir = 'desc';
                else sortDir = 'asc';
            }
            // Update arrows visual
            headers.forEach(h => h.querySelector('span').textContent = '');
            th.querySelector('span').textContent = sortDir === 'asc' ? '▲' : '▼';

            sortPuzzles();
            currentPage = 1;
            renderTable();
        });
    });

    [filterDiff, filterSize, filterArrows].forEach(select => {
        select.addEventListener('change', () => {
            updateFilteredPuzzles();
        });
    });

    prevPageBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderTable();
        }
    });

    nextPageBtn.addEventListener('click', () => {
        const totalPages = Math.ceil(filteredPuzzles.length / itemsPerPage);
        if (currentPage < totalPages) {
            currentPage++;
            renderTable();
        }
    });

    // Functions

    function updateFilteredPuzzles() {
        const diff = filterDiff.value;
        const size = filterSize.value;
        const arrows = filterArrows.value;

        filteredPuzzles = allPuzzles.filter(p => {
            if (diff && p.difficulty !== diff) return false;
            if (size && p.size !== size) return false;
            if (arrows && p.arrows !== arrows) return false;
            return true;
        });

        sortPuzzles(); // Re-sort new list
        currentPage = 1; // Reset to first page
        renderTable();
    }

    function sortPuzzles() {
        filteredPuzzles.sort((a, b) => {
            let valA = a[sortField];
            let valB = b[sortField];

            if (sortField === 'difficulty') {
                const diffOrder = { 'Easy': 1, 'Normal': 2, 'Hard': 3, 'Devious': 4, 'Unknown': 5 };
                valA = diffOrder[valA] || 99;
                valB = diffOrder[valB] || 99;
            }

            if (valA < valB) return sortDir === 'asc' ? -1 : 1;
            if (valA > valB) return sortDir === 'asc' ? 1 : -1;
            return 0;
        });
    }

    function renderTable() {
        archiveList.innerHTML = '';

        if (filteredPuzzles.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="4" style="text-align:center;">No puzzles found matching filters.</td>';
            archiveList.appendChild(row);
            return;
        }

        // Pagination
        const totalPages = Math.ceil(filteredPuzzles.length / itemsPerPage);
        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const pagedPuzzles = filteredPuzzles.slice(start, end);

        pageInfo.textContent = `Page ${currentPage} of ${totalPages || 1}`;
        prevPageBtn.disabled = currentPage <= 1;
        nextPageBtn.disabled = currentPage >= totalPages;

        pagedPuzzles.forEach(puzzle => {
            const tr = document.createElement('tr');

            // Format Date
            const dateObj = new Date(puzzle.date);
            const dateStr = dateObj.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                weekday: 'short'
            });

            // Format Arrows
            let arrowDisplay = puzzle.arrows;
            if (arrowDisplay === 'Straight') {
                arrowDisplay = '<span title="Straight">→</span>';
            } else if (arrowDisplay === 'Diagonal') {
                arrowDisplay = '<span title="Diagonal">→ ↗</span>';
            }

            tr.innerHTML = `
                <td>${dateStr}</td>
                <td><span class="badge diff-${puzzle.difficulty.toLowerCase()}">${puzzle.difficulty}</span></td>
                <td><span class="badge size">${puzzle.size}</span></td>
                <td>${arrowDisplay}</td>
            `;

            // Click to navigate
            tr.addEventListener('click', () => {
                window.location.href = `/?date=${puzzle.date}`;
            });

            archiveList.appendChild(tr);
        });
    }
});
