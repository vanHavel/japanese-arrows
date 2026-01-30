import { loadPuzzle, checkPuzzle, fillSolution, resetPuzzle, shareUrl } from './modules/puzzle.js';
import { initNavigation, navigateDay } from './modules/navigation.js';
import { setMode, handleKeyDown, handleKeyUp, inputNumber, handleNumpadInput, handleNumpadDelete, handleNumpadUndo } from './modules/input.js';
import { closeNumpadModal, setupResetModal } from './modules/modals.js';

document.addEventListener('DOMContentLoaded', () => {
    const puzzleGrid = document.getElementById('puzzle-grid');
    const numParams = document.querySelectorAll('.num-btn:not(.mobile-num-btn)');
    const deleteBtn = document.getElementById('numpad-delete');

    const modePenBtn = document.getElementById('mode-pen');
    const modePencilBtn = document.getElementById('mode-pencil');
    const modePenBtnDesktop = document.getElementById('mode-pen-desktop');
    const modePencilBtnDesktop = document.getElementById('mode-pencil-desktop');

    const shareBtn = document.getElementById('btn-share');
    const fillSolutionBtn = document.getElementById('btn-fill-solution');
    const checkBtn = document.getElementById('btn-check');

    const toggleGridBtn = document.getElementById('toggle-grid');
    const toggleGridBtnDesktop = document.getElementById('toggle-grid-desktop');

    const numpadModal = document.getElementById('numpad-modal');
    const btnCloseNumpad = document.getElementById('btn-close-numpad');
    const mobileNumBtns = document.querySelectorAll('.mobile-num-btn');

    const prevDayBtn = document.getElementById('prev-day');
    const nextDayBtn = document.getElementById('next-day');

    initNavigation();
    loadPuzzle();

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

    setupResetModal(resetPuzzle);

    btnCloseNumpad.addEventListener('click', closeNumpadModal);
    numpadModal.addEventListener('click', (e) => {
        if (e.target === numpadModal) closeNumpadModal();
    });

    mobileNumBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const val = btn.getAttribute('data-value');

            if (val === 'undo') {
                handleNumpadUndo();
                return;
            }

            if (val === 'delete') {
                handleNumpadDelete();
            } else {
                handleNumpadInput(val);
            }
        });
    });

    shareBtn.addEventListener('click', shareUrl);
    fillSolutionBtn.addEventListener('click', fillSolution);
    checkBtn.addEventListener('click', checkPuzzle);

    prevDayBtn.addEventListener('click', () => navigateDay(-1));
    nextDayBtn.addEventListener('click', () => navigateDay(1));
});
