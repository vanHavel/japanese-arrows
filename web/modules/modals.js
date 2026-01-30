import { puzzle, userState, numpadUndoStack } from './state.js';
import { renderGrid, updateNumpadVisuals } from './render.js';

export function openNumpadModal(anchorElement) {
    const numpadModal = document.getElementById('numpad-modal');
    const btnCloseNumpad = document.getElementById('btn-close-numpad');

    numpadModal.style.pointerEvents = 'none';
    setTimeout(() => {
        numpadModal.style.pointerEvents = 'auto';
    }, 300);

    numpadUndoStack.length = 0;

    const isPencil = (userState.mode === 'pencil') || (userState.isCtrlPressed && userState.mode === 'pen');
    const numpadDiv = numpadModal.querySelector('.numpad');

    if (isPencil) {
        numpadDiv.classList.add('pencil-mode');
        numpadModal.querySelector('.undo-btn').classList.remove('hidden');
        btnCloseNumpad.textContent = 'Done';
        const btnZero = numpadModal.querySelector('.mobile-num-btn[data-value="0"]');
        if (btnZero) btnZero.classList.add('hidden');
    } else {
        numpadDiv.classList.remove('pencil-mode');
        numpadModal.querySelector('.undo-btn').classList.add('hidden');
        btnCloseNumpad.textContent = 'Cancel';
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

        const topBelow = rect.bottom + gap;
        const fitsBelow = topBelow + modalRect.height <= window.innerHeight - padding;

        const topAbove = rect.top - gap - modalRect.height;
        const fitsAbove = topAbove >= padding;

        if (fitsBelow) {
            top = topBelow;
        } else if (fitsAbove) {
            top = topAbove;
        } else {
            const cellVerticalCenter = rect.top + rect.height / 2;
            const viewportCenter = window.innerHeight / 2;

            if (cellVerticalCenter > viewportCenter) {
                top = Math.max(padding, topAbove);
            } else {
                top = Math.min(topBelow, window.innerHeight - modalRect.height - padding);
            }
        }

        left = rect.left + rect.width / 2 - modalRect.width / 2;
        left = Math.max(padding, Math.min(left, window.innerWidth - modalRect.width - padding));

        modalContent.style.position = 'fixed';
        modalContent.style.top = `${top}px`;
        modalContent.style.left = `${left}px`;
        modalContent.style.margin = '0';
    }

    updateNumpadVisuals();
}

export function closeNumpadModal() {
    const numpadModal = document.getElementById('numpad-modal');

    const rightControls = document.querySelector('.right-controls');
    if (rightControls) {
        rightControls.style.pointerEvents = 'none';
        setTimeout(() => {
            rightControls.style.pointerEvents = 'auto';
        }, 300);
    }

    numpadModal.classList.add('hidden');

    const numBtns = numpadModal.querySelectorAll('.mobile-num-btn.num-btn');
    numBtns.forEach(btn => btn.classList.remove('active'));

    if (userState.selected) {
        userState.selected = null;
        renderGrid();
    }
}

export function setupResetModal(resetPuzzle) {
    const resetModal = document.getElementById('reset-modal');
    const btnCancelReset = document.getElementById('btn-cancel-reset');
    const btnConfirmReset = document.getElementById('btn-confirm-reset');
    const resetBtn = document.getElementById('btn-reset');

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
    resetModal.addEventListener('click', (e) => {
        if (e.target === resetModal) {
            resetModal.classList.add('hidden');
        }
    });
}
