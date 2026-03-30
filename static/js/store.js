/* ═══════════════════════════════════════════════════════
   MERCADO NEGRO · store.js v2
   Comnect Guardians — Cyberpunk RPG Edition
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    const csrftoken      = getCookie('csrftoken');
    const btnReroll      = document.getElementById('btn-reroll');
    const lojaContainer  = document.getElementById('loja-items');
    const playerCoinsEl  = document.getElementById('player-coins');
    const rerollCostEl   = document.getElementById('reroll-cost');
    const toastContainer = document.getElementById('store-toast');

    /* ══════════════════════════════════════════════════
       AUDIO ENGINE — Web Audio API, sem assets externos
    ══════════════════════════════════════════════════ */
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    let audioCtx = null;

    function ensureAudio() {
        if (!audioCtx) audioCtx = new AudioCtx();
        return audioCtx;
    }

    function playTone({ freq = 440, freq2 = null, type = 'sine', duration = 0.12, gain = 0.18, delay = 0 } = {}) {
        try {
            const ctx = ensureAudio();
            const t   = ctx.currentTime + delay;
            const osc = ctx.createOscillator();
            const env = ctx.createGain();
            osc.connect(env);
            env.connect(ctx.destination);
            osc.type = type;
            osc.frequency.setValueAtTime(freq, t);
            if (freq2) osc.frequency.exponentialRampToValueAtTime(freq2, t + duration);
            env.gain.setValueAtTime(0, t);
            env.gain.linearRampToValueAtTime(gain, t + 0.01);
            env.gain.exponentialRampToValueAtTime(0.001, t + duration);
            osc.start(t);
            osc.stop(t + duration + 0.02);
        } catch (e) { /* silent */ }
    }

    const SFX = {
        click()    { playTone({ freq: 800, freq2: 600,  type: 'square',   duration: 0.06, gain: 0.10 }); },
        /*hover()    { playTone({ freq: 1200, freq2: 1400, type: 'sine',    duration: 0.04, gain: 0.04 }); }, */
        buy() {
            playTone({ freq: 300, freq2: 600,  type: 'sine', duration: 0.12, gain: 0.15 });
            playTone({ freq: 600, freq2: 900,  type: 'sine', duration: 0.12, gain: 0.12, delay: 0.10 });
            playTone({ freq: 900, freq2: 1200, type: 'sine', duration: 0.18, gain: 0.10, delay: 0.20 });
        },
        sell() {
            playTone({ freq: 600, freq2: 300, type: 'sine', duration: 0.18, gain: 0.14 });
            playTone({ freq: 400, freq2: 200, type: 'sine', duration: 0.12, gain: 0.10, delay: 0.15 });
        },
        reroll() {
            [0, 0.08, 0.16, 0.24].forEach((delay, i) =>
                playTone({ freq: 200 + i * 80, freq2: 320 + i * 80, type: 'sawtooth', duration: 0.10, gain: 0.07, delay })
            );
        },
        error() {
            playTone({ freq: 200, freq2: 150, type: 'square', duration: 0.15, gain: 0.12 });
            playTone({ freq: 150, freq2: 100, type: 'square', duration: 0.15, gain: 0.10, delay: 0.12 });
        },
        drag()    { playTone({ freq: 400, freq2: 500, type: 'sine', duration: 0.08, gain: 0.07 }); },
        drop() {
            playTone({ freq: 500, freq2: 400, type: 'sine', duration: 0.10, gain: 0.12 });
            playTone({ freq: 700,             type: 'sine', duration: 0.08, gain: 0.08, delay: 0.08 });
        },
        easterEgg() {
            [523, 659, 784, 1046].forEach((freq, i) =>
                playTone({ freq, type: 'sine', duration: 0.2, gain: 0.12, delay: i * 0.12 })
            );
        },
    };

    /* ══════════════════════════════════════════════════
       STATE
    ══════════════════════════════════════════════════ */
    const STATE = {
        coins:       window.STORE_STATE?.coins       ?? 0,
        rerollCusto: window.STORE_STATE?.rerollCusto ?? 0,
        equippedIds: new Set(window.STORE_STATE?.equippedIds ?? []),
    };

    function setCoins(val) {
        STATE.coins = val;
        if (playerCoinsEl) playerCoinsEl.textContent = `${val} ⬡`;
        refreshValidations();
    }
    function setRerollCusto(val) {
        STATE.rerollCusto = val;
        if (rerollCostEl) rerollCostEl.textContent = val;
        refreshValidations();
    }
    function addEquipped(id)    { STATE.equippedIds.add(String(id));    refreshValidations(); }
    function removeEquipped(id) { STATE.equippedIds.delete(String(id)); refreshValidations(); }

    /* ══════════════════════════════════════════════════
       VALIDAÇÕES REATIVAS
    ══════════════════════════════════════════════════ */
    function refreshValidations() {
        validateReroll();
        validateAllCards();
    }

    function validateReroll() {
        if (!btnReroll) return;
        btnReroll.classList.toggle('state-broke', STATE.coins < STATE.rerollCusto);
    }

    function validateAllCards() {
        document.querySelectorAll('.item-card').forEach(validateCard);
    }

    function validateCard(card) {
        const itemId = card.dataset.itemId;
        const price  = parseInt(card.dataset.price, 10);
        const btn    = card.querySelector('.btn-buy');
        if (!btn) return;

        const isEquipped = STATE.equippedIds.has(String(itemId));
        const isBroke    = STATE.coins < price;

        card.classList.remove('state-equipped', 'state-broke');
        btn.classList.remove('state-equipped', 'state-broke');

        if (isEquipped) {
            card.classList.add('state-equipped');
            btn.classList.add('state-equipped');
            btn.querySelector('span').textContent = 'EQUIPADO';
            btn.title = 'Este módulo já está ativo no seu build.';
        } else if (isBroke) {
            card.classList.add('state-broke');
            btn.classList.add('state-broke');
            btn.querySelector('span').textContent = 'SEM GOLD';
            btn.title = `Faltam ${price - STATE.coins} ⬡`;
        } else {
            btn.querySelector('span').textContent = 'COMPRAR';
            btn.title = '';
        }
    }

    /* ══════════════════════════════════════════════════
       UTILS
    ══════════════════════════════════════════════════ */
    function getCookie(name) {
        let val = null;
        if (document.cookie) {
            document.cookie.split(';').forEach(c => {
                c = c.trim();
                if (c.startsWith(name + '='))
                    val = decodeURIComponent(c.slice(name.length + 1));
            });
        }
        return val;
    }

    async function cyberFetch(url, body = {}) {
        try {
            const res  = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                body: JSON.stringify(body),
            });
            const data = await res.json();
            return { ok: res.ok, status: res.status, data };
        } catch (err) {
            return { ok: false, status: 500, data: { mensagem: 'Falha na conexão.' } };
        }
    }

    function showToast(msg, type = 'ok') {
        const el = document.createElement('div');
        el.className = `toast-item toast-${type} font-tech`;
        el.textContent = `> ${msg}`;
        toastContainer.appendChild(el);
        setTimeout(() => el.remove(), 3800);
    }

    /* ══════════════════════════════════════════════════
       BUILD CARD HTML
    ══════════════════════════════════════════════════ */
    function buildCardHTML(slot) {
        const raridade   = (slot.raridade || 'common').toLowerCase();
        const icon       = slot.icon || 'bi-box';
        const discClass  = slot.tem_desconto ? 'has-discount' : '';
        const salePrefix = slot.tem_desconto
            ? '<span style="font-size:0.5rem;letter-spacing:2px;opacity:0.7;vertical-align:middle">SALE </span>'
            : '';

        if (slot.tipo === 'consumable') {
            return `
            <div class="item-card item-card--consumable rarity-${raridade}"
                 data-item-id="${slot.item_id}"
                 data-price="${slot.preco_final}">
                <div class="card-consumable-stripe"></div>
                <div class="card-body">
                    <div class="card-scanlines"></div>
                    <div class="card-top">
                        <span class="card-tipo-badge card-tipo-badge--consumable font-tech">
                            <i class="bi bi-lightning-charge-fill"></i> CONSUMÍVEL
                        </span>
                        <span class="card-rarity-badge font-tech badge-${raridade}">${slot.raridade}</span>
                    </div>
                    <div class="card-art card-art--consumable">
                        <div class="card-art-icon-glow consumable-glow"></div>
                        <i class="bi ${icon} card-art-icon card-art-icon--consumable"></i>
                        <span class="card-uses-badge font-tech">1× USO</span>
                    </div>
                    <div class="card-content">
                        <h4 class="card-name">${slot.name}</h4>
                        <p class="card-desc">${slot.description}</p>
                    </div>
                    <div class="card-footer card-footer--consumable">
                        <span class="card-price font-tech ${discClass}">
                            ${salePrefix}${slot.preco_final} ⬡
                        </span>
                        <button class="btn-buy btn-buy--consumable font-tech" data-id="${slot.item_id}">
                            <i class="bi bi-bag-plus"></i><span>CARREGAR</span>
                        </button>
                    </div>
                </div>
            </div>`;
        }

        return `
        <div class="item-card rarity-${raridade}"
             data-item-id="${slot.item_id}"
             data-price="${slot.preco_final}">
            <div class="card-glow"></div>
            <div class="card-body">
                <div class="card-scanlines"></div>
                <div class="card-shimmer"></div>
                <div class="card-top">
                    <span class="card-tipo-badge font-tech">
                        <i class="bi ${icon}"></i> ${(slot.tipo || '').toUpperCase()}
                    </span>
                    <span class="card-rarity-badge font-tech badge-${raridade}">${slot.raridade}</span>
                </div>
                <div class="card-art">
                    <div class="card-art-icon-glow"></div>
                    <i class="bi ${icon} card-art-icon"></i>
                </div>
                <div class="card-content">
                    <h4 class="card-name">${slot.name}</h4>
                    <p class="card-desc">${slot.description}</p>
                </div>
                <div class="card-footer">
                    <span class="card-price font-tech ${discClass}">
                        ${salePrefix}${slot.preco_final} ⬡
                    </span>
                    <button class="btn-buy font-tech" data-id="${slot.item_id}">
                        <span>COMPRAR</span>
                    </button>
                </div>
            </div>
        </div>`;
    }

    function showSkeletons(count = 4) {
        lojaContainer.innerHTML = '';
        for (let i = 0; i < count; i++)
            lojaContainer.insertAdjacentHTML('beforeend', '<div class="card-loading"></div>');
    }

    /* ══════════════════════════════════════════════════
       HOVER SOUNDS — cards e módulos
    ══════════════════════════════════════════════════ */
    document.addEventListener('mouseenter', (e) => {
        if (e.target.closest?.('.item-card:not(.state-equipped):not(.state-broke)')) SFX.hover();
        if (e.target.closest?.('.hud-module-slot.occupied')) SFX.hover();
    }, true);

    if (btnReroll) btnReroll.addEventListener('mouseenter', () => SFX.hover());

    /* ══════════════════════════════════════════════════
       DRAG-AND-DROP — reordenar módulos no HUD
    ══════════════════════════════════════════════════ */
    let dragSrc = null;

    function initModuleDrag() {
        document.querySelectorAll('.hud-module-slot').forEach(slot => {
            // Remove velhos listeners clonando o nó
            const fresh = slot.cloneNode(true);
            slot.parentNode.replaceChild(fresh, slot);
        });

        document.querySelectorAll('.hud-module-slot.occupied').forEach(slot => {
            slot.setAttribute('draggable', 'true');

            slot.addEventListener('dragstart', (e) => {
                dragSrc = slot;
                slot.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', '');
                SFX.drag();
            });

            slot.addEventListener('dragend', () => {
                slot.classList.remove('dragging');
                document.querySelectorAll('.hud-module-slot').forEach(s => s.classList.remove('drag-over'));
                dragSrc = null;
            });
        });

        document.querySelectorAll('.hud-module-slot').forEach(slot => {
            slot.addEventListener('dragover', (e) => {
                e.preventDefault();
                if (slot !== dragSrc) slot.classList.add('drag-over');
            });
            slot.addEventListener('dragleave', () => slot.classList.remove('drag-over'));
            slot.addEventListener('drop', (e) => {
                e.preventDefault();
                slot.classList.remove('drag-over');
                if (!dragSrc || dragSrc === slot) return;
                SFX.drop();
                swapSlotContents(dragSrc, slot);
            });
        });
    }

    function swapSlotContents(slotA, slotB) {
        const rarityClasses = ['rarity-common','rarity-rare','rarity-epic','rarity-legendary','occupied','empty'];

        const aInner   = slotA.innerHTML;
        const bInner   = slotB.innerHTML;
        const aRarity  = rarityClasses.filter(c => slotA.classList.contains(c));
        const bRarity  = rarityClasses.filter(c => slotB.classList.contains(c));

        slotA.innerHTML = bInner;
        slotB.innerHTML = aInner;

        rarityClasses.forEach(c => { slotA.classList.remove(c); slotB.classList.remove(c); });
        bRarity.forEach(c => slotA.classList.add(c));
        aRarity.forEach(c => slotB.classList.add(c));

        // Re-bind btn-sell listeners (event delegation handles it)
        // Re-init drag
        setTimeout(() => initModuleDrag(), 80);
        showToast('Módulos reorganizados.', 'ok');
    }

    initModuleDrag();

    /* ══════════════════════════════════════════════════
       EASTER EGG — relógio flutuante (3 cliques)
    ══════════════════════════════════════════════════ */
    const hudDate      = document.querySelector('.hud-date');
    let eggActivated   = false;
    let eggClickCount  = 0;

    if (hudDate) {
        hudDate.title = '///';

        hudDate.addEventListener('click', () => {
            eggClickCount++;
            SFX.click();
            if (eggClickCount === 3 && !eggActivated) {
                eggActivated = true;
                SFX.easterEgg();
                activateFloatingDate();
            }
        });
    }

    function activateFloatingDate() {
        if (!hudDate) return;
        const rect = hudDate.getBoundingClientRect();

        hudDate.classList.add('is-floating');
        hudDate.style.left   = rect.left + 'px';
        hudDate.style.top    = rect.top  + 'px';
        hudDate.style.margin = '0';
        hudDate.style.width  = rect.width + 'px';
        document.body.appendChild(hudDate);

        let isDragging = false, ox = 0, oy = 0;

        hudDate.addEventListener('mousedown', (e) => {
            isDragging = true;
            ox = e.clientX - parseInt(hudDate.style.left || 0);
            oy = e.clientY - parseInt(hudDate.style.top  || 0);
            hudDate.style.transition = 'none';
            e.preventDefault();
        });
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            hudDate.style.left = (e.clientX - ox) + 'px';
            hudDate.style.top  = (e.clientY - oy) + 'px';
        });
        document.addEventListener('mouseup', () => {
            if (isDragging) { isDragging = false; hudDate.style.transition = ''; }
        });

        showToast('// CLOCK.EXE liberado', 'ok');
    }

    /* ══════════════════════════════════════════════════
       REROLL
    ══════════════════════════════════════════════════ */
    if (btnReroll) {
        btnReroll.addEventListener('click', async () => {
            if (STATE.coins < STATE.rerollCusto) {
                SFX.error();
                showToast(`Créditos insuficientes. Necessário: ${STATE.rerollCusto} ⬡`, 'error');
                btnReroll.classList.add('anim-shake');
                setTimeout(() => btnReroll.classList.remove('anim-shake'), 500);
                return;
            }

            SFX.reroll();
            btnReroll.disabled = true;
            showSkeletons(lojaContainer.children.length || 4);

            const { ok, data } = await cyberFetch(window.STORE_URLS.reroll);

            if (ok && data.ok) {
                setCoins(data.coins_atual);
                setRerollCusto(data.proximo_custo);
                lojaContainer.innerHTML = '';
                
                data.novos_itens.forEach((slot, i) => {
                    lojaContainer.insertAdjacentHTML('beforeend', buildCardHTML(slot));
                    const card = lojaContainer.lastElementChild;
                    
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(24px) scale(0.95)';
                    validateCard(card);
                    
                    setTimeout(() => {
                        card.style.transition = 'opacity 0.4s ease, transform 0.4s cubic-bezier(0.34,1.56,0.64,1)';
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0) scale(1)';
                    }, i * 120);
                });

                showToast('Novos itens gerados no mercado.', 'ok');
            } else {
                SFX.error();
                showToast(data.mensagem || 'Erro no reroll.', 'error');
            }

            btnReroll.disabled = false;
        });
    }

    /* ══════════════════════════════════════════════════
       COMPRAR
    ══════════════════════════════════════════════════ */
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('.btn-buy');
        if (!btn) return;

        SFX.click();

        if (btn.classList.contains('state-equipped')) {
            showToast('Este módulo já está ativo no seu build.', 'error');
            return;
        }
        if (btn.classList.contains('state-broke')) {
            const card  = btn.closest('.item-card');
            const price = parseInt(card?.dataset.price, 10) || 0;
            SFX.error();
            showToast(`Sem créditos. Faltam ${price - STATE.coins} ⬡.`, 'error');
            card?.classList.add('anim-shake');
            setTimeout(() => card?.classList.remove('anim-shake'), 500);
            return;
        }

        const itemId = btn.dataset.id;
        const card   = btn.closest('.item-card');
        const price  = parseInt(card?.dataset.price, 10) || 0;

        btn.disabled = true;
        btn.querySelector('span').textContent = '...';

        const { ok, data } = await cyberFetch(window.STORE_URLS.comprar, { item_id: itemId });

        if (ok && data.ok) {
            SFX.buy();
            setCoins(STATE.coins - price);
            addEquipped(itemId);
            if (card) {
                card.style.transition = 'box-shadow 0.3s, transform 0.3s';
                card.style.boxShadow  = '0 0 0 2px var(--neon-green), 0 0 32px rgba(5,217,232,0.4)';
                card.style.transform  = 'translateY(-18px) scale(1.05)';
            }
            showToast('Upgrade instalado com sucesso.', 'ok');
            setTimeout(() => window.location.reload(), 750);
        } else {
            SFX.error();
            showToast(data.mensagem || 'Transação recusada.', 'error');
            btn.disabled = false;
            btn.querySelector('span').textContent = 'COMPRAR';
        }
    });

    /* ══════════════════════════════════════════════════
       VENDER
    ══════════════════════════════════════════════════ */
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('.btn-sell-hud');
        if (!btn) return;

        SFX.click();
        if (!confirm('Deseja vender este módulo por 50% do valor original?')) return;

        const itemId = btn.dataset.id;
        btn.disabled = true;
        btn.textContent = '...';

        const { ok, data } = await cyberFetch(window.STORE_URLS.vender, { item_id: itemId });

        if (ok && data.ok) {
            SFX.sell();
            removeEquipped(itemId);
            if (data.coins_apos_venda) setCoins(data.coins_apos_venda);
            showToast('Módulo vendido. Créditos creditados.', 'ok');
            setTimeout(() => window.location.reload(), 650);
        } else {
            SFX.error();
            showToast(data.mensagem || 'Erro ao vender.', 'error');
            btn.disabled = false;
            btn.textContent = 'VND';
        }
    });

    /* ══════════════════════════════════════════════════
       INIT
    ══════════════════════════════════════════════════ */
    refreshValidations();

});