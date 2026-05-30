(function () {
    console.log("[DEBUG] Script modal_conquistas.js inicializado.");

    const getCookie = name => {
        let val = null;
        document.cookie.split(';').forEach(c => {
            c = c.trim();
            if (c.startsWith(name + '=')) val = decodeURIComponent(c.slice(name.length + 1));
        });
        return val;
    };

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    let audioCtx = null;
    function playTone({ freq = 440, freq2 = null, type = 'sine', duration = 0.12, gain = 0.18, delay = 0 } = {}) {
        try {
            if (!audioCtx) audioCtx = new AudioCtx();
            const ctx = audioCtx, t = ctx.currentTime + delay;
            const osc = ctx.createOscillator(), env = ctx.createGain();
            osc.connect(env); env.connect(ctx.destination);
            osc.type = type;
            osc.frequency.setValueAtTime(freq, t);
            if (freq2) osc.frequency.exponentialRampToValueAtTime(freq2, t + duration);
            env.gain.setValueAtTime(0, t);
            env.gain.linearRampToValueAtTime(gain, t + 0.01);
            env.gain.exponentialRampToValueAtTime(0.001, t + duration);
            osc.start(t); osc.stop(t + duration + 0.02);
        } catch (e) { console.error("[DEBUG] Erro de áudio:", e); }
    }

    const SFX = {
        equip()   { playTone({ freq: 400, freq2: 700,  type: 'sine', duration: 0.12, gain: 0.15 }); },
        unequip() { playTone({ freq: 800, freq2: 400, type: 'sine',   duration: 0.15, gain: 0.14 }); },
        error()   { playTone({ freq: 200, freq2: 150, type: 'square', duration: 0.15, gain: 0.12 }); },
    };

    function init() {
        console.log("[DEBUG] Função init() chamada.");
        
        const areaDestaque   = document.getElementById('area-destaque');
        const areaInventario = document.getElementById('area-inventario');
        const countDestaque  = document.getElementById('count-destaque');

        console.log("[DEBUG] DOM Elements - areaDestaque:", !!areaDestaque, "areaInventario:", !!areaInventario);

        const pNome  = document.getElementById('ach-preview-nome');
        const pDesc  = document.getElementById('ach-preview-desc');
        const pReq   = document.getElementById('ach-preview-req');
        const pBonus = document.getElementById('ach-preview-bonus');

        if (!areaDestaque || !areaInventario) {
            console.warn("[DEBUG] Elementos principais não encontrados. Abortando script.");
            return;
        }

        const TOGGLE_URL = window.CONQUISTAS_TOGGLE_URL;
        console.log("[DEBUG] TOGGLE_URL local:", TOGGLE_URL);

        function renderizarSockets(container) {
            console.log("[DEBUG] Renderizando sockets...");
            if (!container) return;
            const max = parseInt(container.dataset.max || 3);
            const equipadas = Array.from(container.querySelectorAll('.achievement-item'));
            container.innerHTML = '';
            for (let i = 0; i < max; i++) {
                const socket = document.createElement('div');
                socket.className = 'ach-socket';
                if (equipadas[i]) socket.appendChild(equipadas[i]);
                container.appendChild(socket);
            }
        }

        renderizarSockets(areaDestaque);

        function updatePreview(item) {
            pNome.textContent  = item.dataset.nome  || '???';
            pDesc.textContent  = item.dataset.desc  || '';
            pReq.textContent   = item.dataset.req   || '-';
            pBonus.textContent = item.dataset.bonus || '-';

            const previewEl = document.querySelector('#ach-preview-img .achievement-item');
            if (previewEl) {
                previewEl.innerHTML = item.innerHTML;
                previewEl.className = `achievement-item mx-auto ${item.classList.contains('unlocked') ? 'unlocked' : 'locked'}`;
                const rarityClass = Array.from(item.classList).find(c => c.startsWith('rarity-'));
                if (rarityClass) previewEl.classList.add(rarityClass);
            }
        }

        async function reqToggle(paId, ativar) {
            console.log(`[DEBUG] Disparando reqToggle. paId: ${paId}, ativar: ${ativar}`);
            try {
                const res = await fetch(TOGGLE_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
                    body: JSON.stringify({ player_achievement_id: paId, ativar }),
                });
                console.log("[DEBUG] Status HTTP HTTP:", res.status);
                if (!res.ok) return { ok: false };
                return await res.json();
            } catch (error) {
                console.error("[DEBUG] Erro fatal no fetch:", error);
                return { ok: false };
            }
        }

        async function processarClique(itemInventario) {
            console.log("[DEBUG] processarClique iniciado. Item:", itemInventario);
            const paId       = itemInventario.dataset.paId;
            const isEquipped = itemInventario.classList.contains('is-equipped');

            if (isEquipped) {
                console.log("[DEBUG] Fluxo de DESEQUIPAR. paId:", paId);
                const data = await reqToggle(paId, false);
                console.log("[DEBUG] Resposta API Desequipar:", data);
                if (data.ok) {
                    SFX.unequip();
                    itemInventario.classList.remove('is-equipped');
                    const slot = areaDestaque.querySelector(`.achievement-item[data-pa-id="${paId}"]`);
                    if (slot) slot.remove();
                    renderizarSockets(areaDestaque);
                    if (countDestaque) countDestaque.textContent = data.count;
                }
            } else {
                console.log("[DEBUG] Fluxo de EQUIPAR. paId:", paId);
                let socketsVazios = Array.from(areaDestaque.querySelectorAll('.ach-socket')).filter(s => s.children.length === 0);

                if (socketsVazios.length === 0) {
                    console.log("[DEBUG] Capacidade máxima atingida, removendo o mais antigo...");
                    const primeiroSocket = areaDestaque.querySelector('.ach-socket');
                    const maisAntigo = primeiroSocket?.querySelector('.achievement-item');
                    if (maisAntigo) {
                        const antigoId = maisAntigo.dataset.paId;
                        await reqToggle(antigoId, false);
                        maisAntigo.remove();
                        const oldOriginal = areaInventario.querySelector(`.achievement-item[data-pa-id="${antigoId}"]`);
                        if (oldOriginal) oldOriginal.classList.remove('is-equipped');
                        socketsVazios.push(primeiroSocket);
                    }
                }

                const data = await reqToggle(paId, true);
                console.log("[DEBUG] Resposta API Equipar:", data);
                if (data.ok) {
                    SFX.equip();
                    itemInventario.classList.add('is-equipped');
                    const clone = itemInventario.cloneNode(true);
                    clone.classList.remove('is-equipped');
                    clone.classList.add('em-destaque');
                    if (socketsVazios.length > 0) socketsVazios[0].appendChild(clone);
                    renderizarSockets(areaDestaque);
                    if (countDestaque) countDestaque.textContent = data.count;
                } else {
                    SFX.error();
                }
            }
        }

        areaInventario.addEventListener('click', e => {
            console.log("[DEBUG] Capturou click em areaInventario. Target:", e.target);
            const item = e.target.closest('.achievement-item.unlocked');
            if (item) processarClique(item);
        });

        areaDestaque.addEventListener('click', e => {
            console.log("[DEBUG] Capturou click em areaDestaque. Target:", e.target);
            const item = e.target.closest('.achievement-item');
            if (!item) return;
            const original = areaInventario.querySelector(`.achievement-item[data-pa-id="${item.dataset.paId}"]`);
            if (original) processarClique(original);
        });

        document.addEventListener('mouseover', e => {
            const item = e.target.closest('.achievement-item');
            if (item && (areaDestaque.contains(item) || areaInventario.contains(item))) {
                updatePreview(item);
                if (!item.classList.contains('spin-active')) {
                    item.classList.add('spin-active');
                    item.addEventListener('animationend', () => item.classList.remove('spin-active'), { once: true });
                }
            }
        });

        const modalEl = document.getElementById('modalConquistas');
        console.log("[DEBUG] Modal Element detectado:", !!modalEl);
        if (modalEl) {
            modalEl.addEventListener('hidden.bs.modal', () => {
                console.log("[DEBUG] Modal fechado, disparando reload.");
                location.reload();
            });
        }
    }

    if (document.readyState === 'loading') {
        console.log("[DEBUG] Status loading: Aguardando DOMContentLoaded");
        document.addEventListener('DOMContentLoaded', init);
    } else {
        console.log("[DEBUG] DOM pronto, acionando init direto.");
        init();
    }
})();