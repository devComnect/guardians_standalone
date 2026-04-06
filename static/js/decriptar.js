document.addEventListener('DOMContentLoaded', function () {

    // ── Setup ──────────────────────────────────────────────
    const container  = document.getElementById('decriptar-container');
    const ATTEMPT_ID = container.dataset.attemptId;
    const MAX_LIVES  = parseInt(container.dataset.maxLives);
    const TOTAL      = parseInt(container.dataset.total);
    const CSRF = window.CSRF_TOKEN || '';

    const WORDS      = JSON.parse(document.getElementById('words-data').textContent);
    // WORDS = [{index, shuffled, dica, length, solved}, ...]
    // Palavras corretas nunca chegam ao cliente

    let currentIndex   = 0;
    let lives          = MAX_LIVES;
    let correctCount   = parseInt(container.dataset.correct);
    let isGameOver     = false;
    let formSubmitted  = false;
    let hintUsed       = false;

    // ── Elementos ──────────────────────────────────────────
    const timerEl      = document.getElementById('timer-display');
    const livesEl      = document.getElementById('lives-display');
    const scoreEl      = document.getElementById('score-display');
    const dotsEl       = document.getElementById('word-dots');
    const shuffledEl   = document.getElementById('shuffled-display');
    const answerGrid   = document.getElementById('answer-grid');
    const consoleEl    = document.getElementById('console-output');
    const hintZone     = document.getElementById('hint-zone');
    const hintText     = document.getElementById('hint-text');
    const input        = document.getElementById('word-input');
    const submitBtn    = document.getElementById('submit-btn');
    const prevBtn      = document.getElementById('prev-btn');
    const nextBtn      = document.getElementById('next-btn');
    const hintBtn      = document.getElementById('hint-btn');
    const abortBtn     = document.getElementById('abort-btn');

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
        const interval = setInterval(() => {
            if (isGameOver) { clearInterval(interval); return; }
            timeRemaining--;
            const m = Math.floor(timeRemaining / 60).toString().padStart(2, '0');
            const s = Math.floor(timeRemaining % 60).toString().padStart(2, '0');
            timerEl.textContent = `${m}:${s}`;
            if (timeRemaining <= 30) timerEl.classList.add('timer-danger');
            if (timeRemaining <= 0) {
                clearInterval(interval);
                finishGame(true, false);
            }
        }, 1000);
    }

    // ── Vidas UI ───────────────────────────────────────────
    function renderLives() {
        livesEl.innerHTML = '';
        for (let i = 0; i < MAX_LIVES; i++) {
            const icon = document.createElement('i');
            icon.className = `bi bi-heart-fill life-icon${i >= lives ? ' lost' : ''}`;
            livesEl.appendChild(icon);
        }
    }

    // ── Dots de progresso ──────────────────────────────────
    function renderDots() {
        dotsEl.innerHTML = '';
        WORDS.forEach((w, i) => {
            const dot = document.createElement('div');
            dot.className = 'word-dot';
            if (w.solved)      dot.classList.add('dot-solved');
            if (i === currentIndex) dot.classList.add('dot-active');
            dot.addEventListener('click', () => loadWord(i));
            dotsEl.appendChild(dot);
        });
    }

    // ── Animação de Penalidade (-Xs) ──────────────────────────
    function showTimePenalty(seconds) {
        const timerContainer = timerEl.parentElement;
        timerContainer.style.position = 'relative';

        const animEl = document.createElement('span');
        animEl.textContent = `-${seconds}s`;
        animEl.className = 'font-tech';
        animEl.style.cssText = `
            position: absolute; right: -40px; top: 0px;
            color: #ff4d4d; font-weight: bold; font-size: 1.2rem;
            pointer-events: none; transition: all 1.2s ease-out;
            opacity: 1; transform: translateY(0); z-index: 100;
        `;
        
        timerContainer.appendChild(animEl);

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                animEl.style.opacity = '0';
                animEl.style.transform = 'translateY(-25px)';
            });
        });

        setTimeout(() => animEl.remove(), 1200);
    }

    // ── Carrega uma palavra (ATUALIZADO) ─────────────────────
    function loadWord(index) {
        if (isGameOver) return;
        if (index < 0) index = WORDS.length - 1;
        if (index >= WORDS.length) index = 0;
        currentIndex = index;

        const w = WORDS[currentIndex];
        
        // Verifica se a dica desta palavra já foi usada
        if (w.hint_used && w.dica && w.dica.trim() !== '') {
            hintText.textContent = w.dica;
            hintZone.style.display = 'flex';
        } else {
            hintZone.style.display = 'none';
            hintText.textContent = '';
        }

        // Embaralhado
        shuffledEl.innerHTML = '';
        if (!w.solved) {
            w.shuffled.split('').forEach((ch, i) => {
                const span = document.createElement('span');
                span.className = 'shuffled-letter';
                span.textContent = ch;
                span.style.animationDelay = `${(i * 0.15) % 2}s`;
                shuffledEl.appendChild(span);
            });
        } else {
            const msg = document.createElement('span');
            msg.className = 'solved-label font-tech';
            msg.textContent = '[ DADOS RECUPERADOS ]';
            shuffledEl.appendChild(msg);
        }

        // Grid de resposta
        answerGrid.innerHTML = '';
        for (let i = 0; i < w.length; i++) {
            const box = document.createElement('div');
            box.className = 'answer-box';
            if (w.solved) box.classList.add('correct');
            answerGrid.appendChild(box);
        }

        // Input
        input.value       = '';
        input.maxLength   = w.length;
        input.disabled    = w.solved;

        if (w.solved) {
            consoleEl.innerHTML = `<span class="txt-success">Arquivo ${currentIndex + 1} recuperado.</span>`;
        } else {
            consoleEl.textContent = 'Aguardando chave de decriptação...';
            input.focus();
        }

        // Nav buttons
        prevBtn.disabled = false;
        nextBtn.disabled = false;

        renderDots();
    }

    // ── Input → Grid visual ────────────────────────────────
    input.addEventListener('input', () => {
        let val = input.value.toUpperCase().replace(/[^A-ZÇÃÕÁÉÍÓÚÂÊÔÀü]/g, '');
        if (val.length > WORDS[currentIndex].length) val = val.slice(0, WORDS[currentIndex].length);
        input.value = val;

        const boxes = answerGrid.querySelectorAll('.answer-box');
        val.split('').forEach((ch, i) => {
            boxes[i].textContent = ch;
            boxes[i].classList.add('filled');
        });
        for (let i = val.length; i < boxes.length; i++) {
            boxes[i].textContent = '';
            boxes[i].classList.remove('filled');
        }
    });

    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); checkAnswer(); }
    });

    // ── Valida resposta via AJAX ───────────────────────────
    submitBtn.addEventListener('click', checkAnswer);

    async function checkAnswer() {
        if (isGameOver || WORDS[currentIndex].solved) return;
        const answer = input.value.toUpperCase().trim();

        if (answer.length !== WORDS[currentIndex].length) {
            shakeGrid();
            setConsole(`<span class="txt-warn">Tamanho inválido. Necessário ${WORDS[currentIndex].length} letra(s).</span>`);
            return;
        }

        submitBtn.disabled = true;
        input.disabled     = true;

        try {
            const res  = await fetch('/minigames/decriptar/check/', {
                method:  'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken':  CSRF,
                },
                body: JSON.stringify({
                    attempt_id: ATTEMPT_ID,
                    word_index: currentIndex,
                    answer:     answer,
                }),
            });

            const data = await res.json();

            if (data.error === 'timer_expired' || data.redirect) {
                formSubmitted = true;
                window.location.href = data.redirect;
                return;
            }

            if (data.correct) {
                WORDS[currentIndex].solved = true;
                correctCount = data.correct_count;
                scoreEl.textContent = `${correctCount} / ${TOTAL}`;

                // Preenche grid com verde
                answerGrid.querySelectorAll('.answer-box').forEach((box, i) => {
                    box.textContent = answer[i];
                    box.classList.add('correct');
                });
                setConsole('<span class="txt-success">✓ Chave aceita. Dados recuperados.</span>');

                renderDots();

                if (data.all_done) {
                    setTimeout(() => {
                        formSubmitted = true;
                        window.location.href = data.redirect;
                    }, 1000);
                } else {
                    // Auto-avança para próxima não resolvida
                    setTimeout(() => {
                        let next = -1;
                        for (let i = 1; i < WORDS.length; i++) {
                            const idx = (currentIndex + i) % WORDS.length;
                            if (!WORDS[idx].solved) { next = idx; break; }
                        }
                        if (next !== -1) loadWord(next);
                        else { submitBtn.disabled = false; input.disabled = false; }
                    }, 700);
                }

            } else {
                lives = data.lives_remaining;
                renderLives();
                shakeGrid();
                setConsole(`<span class="txt-error">✗ Chave incorreta. Vidas restantes: ${lives}</span>`);

                // Limpa input após shake
                setTimeout(() => {
                    input.value = '';
                    answerGrid.querySelectorAll('.answer-box').forEach(b => {
                        b.textContent = '';
                        b.classList.remove('filled');
                    });
                    input.disabled = data.game_over;
                    submitBtn.disabled = false;
                    if (!data.game_over) input.focus();
                }, 450);

                if (data.game_over) {
                    setTimeout(() => {
                        formSubmitted = true;
                        window.location.href = data.redirect;
                    }, 1200);
                }
            }

        } catch (e) {
            console.error(e);
            setConsole('<span class="txt-error">Erro de conexão. Tente novamente.</span>');
            submitBtn.disabled = false;
            input.disabled     = false;
        }
    }

    // ── Shake ──────────────────────────────────────────────
    function shakeGrid() {
        const boxes = answerGrid.querySelectorAll('.answer-box');
        boxes.forEach(b => b.classList.add('shake'));
        setTimeout(() => boxes.forEach(b => b.classList.remove('shake')), 400);
    }

    function setConsole(html) { consoleEl.innerHTML = html; }

// ── Dica ───────────────────────────────────────────────
    hintBtn.addEventListener('click', async () => {
        if (isGameOver || WORDS[currentIndex].solved) return;
        
        const w = WORDS[currentIndex];

        // Se a dica já está destravada E o texto está no JS, só mostra na tela e para
        if (w.hint_used && w.dica && w.dica.trim() !== '') {
            hintText.textContent = w.dica;
            hintZone.style.display = 'flex';
            return;
        }
        
        hintBtn.disabled = true;
        const originalHtml = hintBtn.innerHTML;
        hintBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        try {
            const res = await fetch('/minigames/decriptar/hint/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
                body: JSON.stringify({ attempt_id: ATTEMPT_ID, word_index: currentIndex })
            });
            const data = await res.json();

            if (data.error) {
                setConsole(`<span class="txt-error">${data.error}</span>`);
            } else {
                // Atualiza o estado da palavra localmente
                WORDS[currentIndex].hint_used = true;
                WORDS[currentIndex].dica = data.hint;
                
                // Exibe a dica na tela
                hintText.textContent = data.hint;
                hintZone.style.display = 'flex';

                // Aplica penalidade se houver
                if (data.penalty_applied) {
                    timeRemaining = data.remaining_time;
                    showTimePenalty(data.time_deducted);
                }

                if (data.timer_expired) {
                    formSubmitted = true;
                    window.location.href = data.redirect;
                    return;
                }
            }
        } catch (e) {
            console.error(e);
            setConsole('<span class="txt-error">Erro ao obter dica. Tente novamente.</span>');
        } finally {
            hintBtn.disabled = false;
            hintBtn.innerHTML = originalHtml;
            input.focus();
        }
    });

    // ── Navegação ──────────────────────────────────────────
    prevBtn.addEventListener('click', () => loadWord(currentIndex - 1));
    nextBtn.addEventListener('click', () => loadWord(currentIndex + 1));

    // ── Abandonar ──────────────────────────────────────────
    abortBtn.addEventListener('click', () => {
        if (confirm('ATENÇÃO: Abandonar o protocolo?\n\nXP parcial será registrado.')) {
            finishGame(false, true);
        }
    });

    async function finishGame(timerExpired, abandoned) {
        if (isGameOver) return;
        isGameOver = true;

        try {
            const res = await fetch('/minigames/decriptar/finish/', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
                body:    JSON.stringify({ attempt_id: ATTEMPT_ID, timer_expired: timerExpired, abandoned }),
            });
            const data = await res.json();
            formSubmitted = true;
            window.location.href = data.redirect;
        } catch (e) {
            console.error(e);
        }
    }

    // ── Init ───────────────────────────────────────────────
    lives = MAX_LIVES - (WORDS.filter(w => !w.solved).length === WORDS.length ? 0 : 0);
    // Restaura lives do servidor via data attribute se necessário
    renderLives();

    // Vai direto para primeira não resolvida
    const firstUnsolved = WORDS.findIndex(w => !w.solved);
    loadWord(firstUnsolved !== -1 ? firstUnsolved : 0);
});