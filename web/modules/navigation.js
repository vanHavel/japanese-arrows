import { constants, currentDate, setCurrentDate, userState } from './state.js';
import { loadPuzzle } from './puzzle.js';
import { savePuzzleState } from './storage.js';

export function updateDateDisplay() {
    const currentDateDisplay = document.getElementById('current-date');
    const dateObj = new Date(currentDate);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    currentDateDisplay.textContent = dateObj.toLocaleDateString('en-US', options);
}

export function updateNavigationButtons() {
    const prevDayBtn = document.getElementById('prev-day');
    const nextDayBtn = document.getElementById('next-day');
    prevDayBtn.disabled = currentDate <= constants.MIN_DATE;
    nextDayBtn.disabled = currentDate >= constants.MAX_DATE;
}

export function navigateDay(delta) {
    savePuzzleState(currentDate, userState.grid);

    const dateObj = new Date(currentDate);
    dateObj.setDate(dateObj.getDate() + delta);

    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, '0');
    const d = String(dateObj.getDate()).padStart(2, '0');

    setCurrentDate(`${y}-${m}-${d}`);

    const newUrl = `${window.location.pathname}?date=${currentDate}`;
    window.history.pushState({ path: newUrl }, '', newUrl);

    updateDateDisplay();
    updateNavigationButtons();
    loadPuzzle();
}

export function initNavigation() {
    updateDateDisplay();
    updateNavigationButtons();
}
