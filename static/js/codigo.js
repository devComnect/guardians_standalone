document.addEventListener('DOMContentLoaded', function () {

    // ── Setup ──────────────────────────────────────────────
    const container   = document.getElementById('codigo-container');
    const ATTEMPT_ID  = container.dataset.attemptId;
    const WORD_LENGTH = parseInt(container.dataset.wordLength);
    const MAX_ATT     = parseInt(container.dataset.maxAttempts);
    const MAX_XP      = parseInt(container.dataset.xp);
    const CSRF        = window.CSRF_TOKEN || '';

    // Guesses salvos no banco — restaura estado após refresh
    const SAVED_GUESSES = JSON.parse(
        document.getElementById('guesses-data').textContent
    ) || [];

    let currentRow  = SAVED_GUESSES.length;
    let isGameOver  = false;
    let formSubmitted = false;

    // ── Elementos ──────────────────────────────────────────
    const board      = document.getElementById('game-board');
    const input      = document.getElementById('word-input');
    const submitBtn  = document.getElementById('submit-btn');
    const hintBtn    = document.getElementById('hint-btn');
    const abortBtn   = document.getElementById('abort-btn');
    const consoleEl  = document.getElementById('console-msg');
    const timerEl    = document.getElementById('timer-display');
    const xpEl       = document.getElementById('xp-display');

    // ── Segurança ──────────────────────────────────────────
    document.addEventListener('copy',        e => e.preventDefault());
    document.addEventListener('cut',         e => e.preventDefault());
    document.addEventListener('contextmenu', e => e.preventDefault());
    document.addEventListener('keydown', e => {
        const blocked = (e.ctrlKey && ['c','x','a','u','s','p'].includes(e.key.toLowerCase()))
                      || e.key === 'F12' || e.key === 'PrintScreen';
        if (blocked) e.preventDefault();
    });
    window.addEventListener('beforeunload', e => {
        if (!formSubmitted) { e.preventDefault(); e.returnValue = ''; }
    });

    // ── Timer ──────────────────────────────────────────────
    let timeRemaining = parseFloat(container.dataset.timer);
    if (timeRemaining > 0) {
        timerEl.textContent = formatTime(timeRemaining);
        const interval = setInterval(() => {
            if (isGameOver) { clearInterval(interval); return; }
            timeRemaining--;
            timerEl.textContent = formatTime(timeRemaining);
            if (timeRemaining <= 30) timerEl.classList.add('timer-danger');
            if (timeRemaining <= 0) {
                clearInterval(interval);
                sendGuess(null, false, true);
            }
        }, 1000);
    }

    function formatTime(s) {
        const m = Math.floor(s / 60).toString().padStart(2, '0');
        const r = Math.floor(s % 60).toString().padStart(2, '0');
        return `${m}:${r}`;
    }

    // ── Constrói tabuleiro ─────────────────────────────────
    function buildBoard() {
        board.style.setProperty('--word-len', WORD_LENGTH);
        board.innerHTML = '';
        for (let r = 0; r < MAX_ATT; r++) {
            const row = document.createElement('div');
            row.className = 'board-row';
            row.id = `row-${r}`;
            for (let c = 0; c < WORD_LENGTH; c++) {
                const box = document.createElement('div');
                box.className = 'letter-box';
                box.id = `box-${r}-${c}`;
                row.appendChild(box);
            }
            board.appendChild(row);
        }
    }

    // ── Restaura guesses salvos (refresh-safe) ─────────────
    function restoreGuesses() {
        SAVED_GUESSES.forEach((g, rowIndex) => {
            g.feedback.forEach((status, colIndex) => {
                const box = document.getElementById(`box-${rowIndex}-${colIndex}`);
                if (box) {
                    box.textContent = g.guess[colIndex];
                    box.className   = `letter-box ${status}`;
                }
            });
        });
        updateXpDisplay();
    }

    // ── XP dinâmico ───────────────────────────────────────
    function updateXpDisplay() {
        if (!xpEl) return;
        const half     = Math.floor(MAX_ATT / 3);
        const attUsed  = currentRow + 1;
        const potential = attUsed <= half ? MAX_XP : Math.round(MAX_XP * 0.5);
        xpEl.textContent = potential;
        xpEl.style.color = attUsed <= half ? 'var(--neon-blue)' : 'var(--neon-red)';
    }

    // ── Input → tabuleiro ─────────────────────────────────
    input.addEventListener('input', () => {
        if (isGameOver) return;
        let val = input.value.toUpperCase().replace(/[^A-ZÁÉÍÓÚÂÊÔÃÕÇÜ]/g, '');
        if (val.length > WORD_LENGTH) val = val.slice(0, WORD_LENGTH);
        input.value = val;

        for (let c = 0; c < WORD_LENGTH; c++) {
            const box = document.getElementById(`box-${currentRow}-${c}`);
            if (!box) continue;
            box.textContent = val[c] || '';
            box.classList.toggle('filled', !!val[c]);
        }
    });

    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); handleSubmit(); }
    });

    // ── Submit ────────────────────────────────────────────
    submitBtn.addEventListener('click', handleSubmit);

    function handleSubmit() {
        if (isGameOver) return;
        const guess = input.value.toUpperCase().trim();
        if (guess.length !== WORD_LENGTH) {
            shakeRow(currentRow);
            setConsole(`<span class="txt-warn">// Input deve ter ${WORD_LENGTH} letras.</span>`);
            return;
        }
        sendGuess(guess, false, false);
    }

    // ── AJAX ──────────────────────────────────────────────
    async function sendGuess(guess, abandoned, timedOut) {
        if (isGameOver && !abandoned && !timedOut) return;
        isGameOver     = true;
        input.disabled = true;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span>';

        try {
            const res  = await fetch('/minigames/codigo/check/', {
                method:  'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken':  CSRF,
                },
                body: JSON.stringify({
                    attempt_id: ATTEMPT_ID,
                    guess:      guess || '',
                    abandoned,
                    timed_out:  timedOut,
                }),
            });

            const data = await res.json();

            if (data.error) {
                setConsole(`<span class="txt-error">// ${data.error}</span>`);
                input.disabled    = false;
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-terminal"></i> EXECUTAR';
                isGameOver = false;
                return;
            }

            if (abandoned || timedOut) {
                formSubmitted = true;
                window.location.href = data.redirect;
                return;
            }

            // Anima feedback letra a letra
            animateFeedback(data.feedback, guess, data.is_winner, data.game_over, data);

        } catch (e) {
            console.error(e);
            setConsole('<span class="txt-error">// Erro de conexão.</span>');
            input.disabled     = false;
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-terminal"></i> EXECUTAR';
            isGameOver = false;
        }
    }

    // ── Animação flip ─────────────────────────────────────
    function animateFeedback(feedback, guess, isWinner, gameOver, data) {
        const delay = 300; // ms por letra

        feedback.forEach((status, i) => {
            setTimeout(() => {
                const box = document.getElementById(`box-${currentRow}-${i}`);
                if (!box) return;
                box.classList.add('flip');
                setTimeout(() => {
                    box.textContent = guess[i];
                    box.className   = `letter-box ${status} flip-done`;
                }, 150);
            }, i * delay);
        });

        // Após animação completa
        setTimeout(() => {
            currentRow++;
            updateXpDisplay();

            if (isWinner) {
                setConsole('<span class="txt-success">// ACESSO LIBERADO. Redirecionando...</span>');
                pulseRow(currentRow - 1);
                setTimeout(() => { formSubmitted = true; window.location.href = data.redirect; }, 1200);

            } else if (gameOver) {
                setConsole(`<span class="txt-error">// TENTATIVAS ESGOTADAS. Palavra: ${data.secret_word || '???'}</span>`);
                setTimeout(() => { formSubmitted = true; window.location.href = data.redirect; }, 1800);

            } else {
                setConsole(`<span class="txt-muted">// Tentativa ${currentRow}/${MAX_ATT}. Insira próximo comando.</span>`);
                input.value       = '';
                input.disabled    = false;
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-terminal"></i> EXECUTAR';
                isGameOver = false;
                input.focus();
            }
        }, feedback.length * delay + 400);
    }

    // ── Utilitários ───────────────────────────────────────
    function shakeRow(rowIndex) {
        const row = document.getElementById(`row-${rowIndex}`);
        if (!row) return;
        row.classList.add('shake');
        setTimeout(() => row.classList.remove('shake'), 400);
    }

    function pulseRow(rowIndex) {
        const row = document.getElementById(`row-${rowIndex}`);
        if (row) row.classList.add('pulse-win');
    }

    function setConsole(html) { consoleEl.innerHTML = html; }

    // ── Dica ─────────────────────────────────────────────
    hintBtn.addEventListener('click', () => {
        const hint = window.WORD_HINT;
        if (hint) {
            setConsole(`<span class="txt-warn">// DICA: ${hint}</span>`);
        } else {
            setConsole('<span class="txt-warn">// Sem dica disponível para esta palavra.</span>');
        }
        input.focus();
    });

    // ── Abandonar ─────────────────────────────────────────
    abortBtn.addEventListener('click', () => {
        if (confirm('ATENÇÃO: Abandonar o protocolo?\n\nPontuação será zerada.')) {
            sendGuess(null, true, false);
        }
    });

    // ── Init ──────────────────────────────────────────────
    buildBoard();
    restoreGuesses();
    if (currentRow >= MAX_ATT) {
        isGameOver = true;
    } else {
        input.focus();
    }
    setConsole(`<span class="txt-muted">// Tentativa ${currentRow + 1}/${MAX_ATT}. Insira comando.</span>`);
});