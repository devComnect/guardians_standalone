(function () {
    const container   = document.getElementById('logscan-container');
    const ATTEMPT_ID  = container.dataset.attemptId;
    const TIMER_INIT  = parseInt(container.dataset.timer) || 0;
    const TOTAL       = parseInt(container.dataset.total);

    const grid        = JSON.parse(document.getElementById('grid-data').textContent);
    const wordsData   = JSON.parse(document.getElementById('words-data').textContent);

    const gridEl      = document.getElementById('ls-grid');
    const consoleEl   = document.getElementById('ls-console');
    const scoreEl     = document.getElementById('correct-count');
    const statusEl    = document.getElementById('status-display');
    const timerEl     = document.getElementById('timer-display');
    const wordListEl  = document.getElementById('word-list');

    let correctCount  = parseInt(container.dataset.correct);
    let timerInterval = null;
    let secondsLeft   = TIMER_INIT;
    let isDragging    = false;
    let selecting     = [];
    let finished      = false;

    // ── Render word list ──────────────────────────────────
    function renderWordList() {
        wordListEl.innerHTML = '';
        wordsData.forEach(w => {
            const item = document.createElement('div');
            item.className = 'ls-word-item' + (w.solved ? ' found' : '');
            item.dataset.palavra = w.palavra;
            item.innerHTML = `
                <div class="ls-word-name">
                    ${w.solved ? '<i class="bi bi-check-circle-fill ls-found-icon"></i>' : ''}
                    ${w.palavra}
                </div>
                ${w.dica ? `<div class="ls-word-hint">${w.dica}</div>` : ''}
            `;
            wordListEl.appendChild(item);
        });
    }

    // ── Render grid ───────────────────────────────────────
    function renderGrid() {
        gridEl.innerHTML = '';
        grid.forEach((row, r) => {
            const tr = document.createElement('tr');
            row.forEach((ch, c) => {
                const td = document.createElement('td');
                td.textContent = ch;
                td.dataset.r = r;
                td.dataset.c = c;
                tr.appendChild(td);
            });
            gridEl.appendChild(tr);
        });
    }

    function getCell(r, c) {
        return gridEl.querySelector(`td[data-r="${r}"][data-c="${c}"]`);
    }

    function clearSelecting() {
        gridEl.querySelectorAll('.cell-selecting').forEach(td => td.classList.remove('cell-selecting'));
        selecting = [];
    }

    // ── Seleção: extrai células em linha reta ─────────────
    function cellsBetween(r1, c1, r2, c2) {
        const dr = Math.sign(r2 - r1);
        const dc = Math.sign(c2 - c1);

        // Só aceita retas válidas
        const rowDiff = Math.abs(r2 - r1);
        const colDiff = Math.abs(c2 - c1);
        if (dr !== 0 && dc !== 0 && rowDiff !== colDiff) return null;

        const cells = [];
        let r = r1, c = c1;
        while (true) {
            cells.push([r, c]);
            if (r === r2 && c === c2) break;
            r += dr;
            c += dc;
        }
        return cells;
    }

    // ── Mouse events ──────────────────────────────────────
    gridEl.addEventListener('mousedown', e => {
        const td = e.target.closest('td');
        if (!td || finished) return;
        e.preventDefault();
        isDragging = true;
        clearSelecting();
        selecting = [[parseInt(td.dataset.r), parseInt(td.dataset.c)]];
        td.classList.add('cell-selecting');
    });

    gridEl.addEventListener('mousemove', e => {
        if (!isDragging || finished) return;
        const td = e.target.closest('td');
        if (!td) return;

        const r2 = parseInt(td.dataset.r);
        const c2 = parseInt(td.dataset.c);
        const [r1, c1] = selecting[0] || [r2, c2];

        const cells = cellsBetween(r1, c1, r2, c2);
        if (!cells) return;
        selecting = cells;
        gridEl.querySelectorAll('.cell-selecting').forEach(td => td.classList.remove('cell-selecting'));
        cells.forEach(([r, c]) => {
            const cell = getCell(r, c);
            if (cell) cell.classList.add('cell-selecting');
        });
    });

    document.addEventListener('mouseup', e => {
        if (!isDragging || finished) return;
        isDragging = false;
        if (selecting.length < 2) { clearSelecting(); return; }
        submitSelection([...selecting]);
        clearSelecting();
    });

    // ── Touch support ─────────────────────────────────────
    gridEl.addEventListener('touchstart', e => {
        const touch = e.touches[0];
        const td = document.elementFromPoint(touch.clientX, touch.clientY)?.closest('td');
        if (!td || finished) return;
        e.preventDefault();
        isDragging = true;
        clearSelecting();
        selecting = [[parseInt(td.dataset.r), parseInt(td.dataset.c)]];
        td.classList.add('cell-selecting');
    }, { passive: false });

    gridEl.addEventListener('touchmove', e => {
        if (!isDragging || finished) return;
        e.preventDefault();
        const touch = e.touches[0];
        const td = document.elementFromPoint(touch.clientX, touch.clientY)?.closest('td');
        if (!td) return;
        const r2 = parseInt(td.dataset.r);
        const c2 = parseInt(td.dataset.c);
        const [r1, c1] = selecting[0] || [r2, c2];
        const cells = cellsBetween(r1, c1, r2, c2);
        if (!cells) return;  
        selecting = cells;
        gridEl.querySelectorAll('.cell-selecting').forEach(td => td.classList.remove('cell-selecting'));
        cells.forEach(([r, c]) => {
            const cell = getCell(r, c);
            if (cell) cell.classList.add('cell-selecting');
        });
    }, { passive: false });

    gridEl.addEventListener('touchend', e => {
        if (!isDragging || finished) return;
        isDragging = false;
        if (selecting.length < 2) { clearSelecting(); return; }
        submitSelection([...selecting]);
        clearSelecting();
    });

    // ── Submit seleção ────────────────────────────────────
    function submitSelection(cells) {
        const letters = cells.map(([r, c]) => grid[r][c]).join('');

        const matched = wordsData.find(w => !w.solved && w.palavra === letters);
        if (!matched) {
            flashCells(cells, 'cell-error');
            setConsole('> sequência não reconhecida.', 'txt-error');
            return;
        }

        fetch('/minigames/logscan/check/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
            body: JSON.stringify({ attempt_id: ATTEMPT_ID, palavra: matched.palavra, cells: cells })
        })
        .then(r => r.json())
        .then(data => {
            if (data.error === 'timer_expired') { window.location = data.redirect; return; }

            if (data.correct) {
                matched.solved = true;
                markCellsFound(cells);
                updateWordItem(matched.palavra);
                correctCount = data.correct_count;
                scoreEl.textContent = correctCount;
                setConsole(`> AMEAÇA IDENTIFICADA: ${matched.palavra}`, 'txt-success');

                if (data.all_done) {
                    finished = true;
                    statusEl.textContent = 'CONCLUÍDO';
                    setTimeout(() => { window.location = data.redirect; }, 1200);
                }
            }
        });
    }

    function markCellsFound(cells) {
        cells.forEach(([r, c]) => {
            const td = getCell(r, c);
            if (td) {
                td.classList.remove('cell-selecting', 'cell-error');
                td.classList.add('cell-found');
            }
        });
    }

    function flashCells(cells, cls) {
        cells.forEach(([r, c]) => {
            const td = getCell(r, c);
            if (!td) return;
            td.classList.add(cls);
            setTimeout(() => td.classList.remove(cls), 400);
        });
    }

    function updateWordItem(palavra) {
        const item = wordListEl.querySelector(`[data-palavra="${palavra}"]`);
        if (!item) return;
        item.classList.add('found');
        item.querySelector('.ls-word-name').innerHTML =
            `<i class="bi bi-check-circle-fill ls-found-icon"></i> ${palavra}`;
    }

    function setConsole(msg, cls) {
        consoleEl.className = 'ls-console font-tech' + (cls ? ` ${cls}` : '');
        consoleEl.textContent = msg;
    }

    // ── Timer ─────────────────────────────────────────────
    function formatTime(s) {
        const m = Math.floor(s / 60).toString().padStart(2, '0');
        const sec = (s % 60).toString().padStart(2, '0');
        return `${m}:${sec}`;
    }

    function startTimer() {
        if (!TIMER_INIT) return;
        timerEl.textContent = formatTime(secondsLeft);

        timerInterval = setInterval(() => {
            secondsLeft--;
            timerEl.textContent = formatTime(secondsLeft);
            if (secondsLeft <= 30) timerEl.classList.add('timer-danger');
            if (secondsLeft <= 0) {
                clearInterval(timerInterval);
                timerExpired();
            }
        }, 1000);
    }

    function timerExpired() {
        finished = true;
        fetch('/minigames/logscan/finish/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
            body: JSON.stringify({ attempt_id: ATTEMPT_ID, timer_expired: true, abandoned: false })
        })
        .then(r => r.json())
        .then(data => { window.location = data.redirect; });
    }

    // ── Abort ─────────────────────────────────────────────
    document.getElementById('abort-btn').addEventListener('click', () => {
        if (!confirm('Abandonar o LogScan? O progresso atual será salvo.')) return;
        finished = true;
        clearInterval(timerInterval);
        fetch('/minigames/logscan/finish/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
            body: JSON.stringify({ attempt_id: ATTEMPT_ID, timer_expired: false, abandoned: true })
        })
        .then(r => r.json())
        .then(data => { window.location = data.redirect; });
    });

    // ── Init ──────────────────────────────────────────────
    renderGrid();
    renderWordList();
    startTimer();
})();