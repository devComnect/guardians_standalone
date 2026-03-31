/* ═══════════════════════════════════════════════════════
   PERFIL DO JOGADOR · profiles.js v1
   Comnect Guardians — Cyberpunk RPG Edition
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    const csrftoken = getCookie('csrftoken');
    const toastContainer = document.getElementById('profile-toast');

    /* ══════════════════════════════════════════════════
       AUDIO ENGINE
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
        equip() {
            playTone({ freq: 400, freq2: 700,  type: 'sine', duration: 0.12, gain: 0.15 });
            playTone({ freq: 700, freq2: 1000, type: 'sine', duration: 0.15, gain: 0.12, delay: 0.10 });
        },
        unequip() {
            playTone({ freq: 800, freq2: 400, type: 'sine', duration: 0.15, gain: 0.14 });
        },
        error() {
            playTone({ freq: 200, freq2: 150, type: 'square', duration: 0.15, gain: 0.12 });
            playTone({ freq: 150, freq2: 100, type: 'square', duration: 0.15, gain: 0.10, delay: 0.12 });
        },
        tab() {
            playTone({ freq: 600, type: 'triangle', duration: 0.08, gain: 0.08 });
        }
    };

    /* ══════════════════════════════════════════════════
       UTILS
    ══════════════════════════════════════════════════ */
    function getCookie(name) {
        let val = null;
        if (document.cookie) {
            document.cookie.split(';').forEach(c => {
                c = c.trim();
                if (c.startsWith(name + '=')) val = decodeURIComponent(c.slice(name.length + 1));
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
            return { ok: res.ok, data };
        } catch (err) {
            return { ok: false, data: { error: 'Falha na conexão neural.' } };
        }
    }

    function showToast(msg, type = 'ok') {
        if (!toastContainer) return;
        const el = document.createElement('div');
        el.className = `toast-item toast-${type} font-tech`;
        el.textContent = `> ${msg}`;
        toastContainer.appendChild(el);
        setTimeout(() => el.remove(), 3800);
    }

    /* ══════════════════════════════════════════════════
       LOG TABS
    ══════════════════════════════════════════════════ */
    document.querySelectorAll('.log-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            SFX.tab();
            document.querySelectorAll('.log-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.log-content').forEach(c => c.style.display = 'none');
            this.classList.add('active');
            document.getElementById('log-' + this.dataset.tab).style.display = 'block';
        });
    });

    /* ══════════════════════════════════════════════════
       AÇÕES AJAX DO PERFIL
    ══════════════════════════════════════════════════ */

    const areaDestaque = document.getElementById('area-destaque');
    const areaInventario = document.getElementById('area-inventario');
    const areaPreviewPerfil = document.getElementById('preview-build-atual');
    const countDestaque = document.getElementById('count-destaque');

    const pNome = document.getElementById('ach-preview-nome');
    const pDesc = document.getElementById('ach-preview-desc');
    const pBonus = document.getElementById('ach-preview-bonus');

    // Função segura para montar os sockets sem perder os itens
    function renderizarSockets(container) {
        if (!container) return;
        const max = parseInt(container.dataset.max || 3);
        const conquistasEquipadas = Array.from(container.querySelectorAll('.achievement-item'));
        
        container.innerHTML = ''; 
        
        for (let i = 0; i < max; i++) {
            const socket = document.createElement('div');
            socket.className = 'ach-socket';
            
            if (conquistasEquipadas[i]) {
                socket.appendChild(conquistasEquipadas[i]);
            }
            container.appendChild(socket);
        }
    }

    renderizarSockets(areaDestaque);
    renderizarSockets(areaPreviewPerfil);

    function updatePreview(item) {
        pNome.textContent = item.dataset.nome || '???';
        pDesc.textContent = item.dataset.desc || '';
        pBonus.textContent = item.dataset.bonus || '-';
        
        const previewImgContainer = document.querySelector('#ach-preview-img .achievement-item');
        previewImgContainer.innerHTML = item.innerHTML;
        previewImgContainer.className = `achievement-item mx-auto ${item.classList.contains('unlocked') ? 'unlocked' : 'locked'}`;
        
        const rarityClass = Array.from(item.classList).find(c => c.startsWith('rarity-'));
        if (rarityClass) previewImgContainer.classList.add(rarityClass);
    }

    async function reqToggle(paId, ativar) {
        const res = await fetch(window.PROFILE_URLS.toggleConquista, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ player_achievement_id: paId, ativar: ativar })
        });
        return await res.json();
    }

    async function processarCliqueConquista(itemInventario) {
        const paId = itemInventario.dataset.paId;
        const isEquipped = itemInventario.classList.contains('is-equipped');

        if (isEquipped) {
            // DESEQUIPAR
            const data = await reqToggle(paId, false);
            if (data.ok) {
                if (typeof SFX !== 'undefined') SFX.unequip();
                itemInventario.classList.remove('is-equipped'); // Devolve a cor original na grid
                
                // Remove apenas do Modal
                const equippedItem = areaDestaque?.querySelector(`.achievement-item[data-pa-id="${paId}"]`);
                if (equippedItem) equippedItem.remove();
                
                if (countDestaque) countDestaque.textContent = data.count;
            }
        } else {
            // EQUIPAR
            // Procura sockets vazios APENAS no modal
            const socketsVazios = Array.from(areaDestaque.querySelectorAll('.ach-socket')).filter(s => s.children.length === 0);
            
            if (socketsVazios.length === 0) {
                // Tira a mais velha se estiver cheio
                const primeiroSocket = areaDestaque.querySelector('.ach-socket');
                const maisAntigo = primeiroSocket.querySelector('.achievement-item');
                
                if (maisAntigo) {
                    const antigoId = maisAntigo.dataset.paId;
                    await reqToggle(antigoId, false);
                    maisAntigo.remove();
                    
                    const oldOriginal = areaInventario.querySelector(`.achievement-item[data-pa-id="${antigoId}"]`);
                    if (oldOriginal) oldOriginal.classList.remove('is-equipped'); // Devolve a cor da que saiu
                    socketsVazios.push(primeiroSocket); 
                }
            }

            const data = await reqToggle(paId, true);
            if (data.ok) {
                if (typeof SFX !== 'undefined') SFX.equip();
                itemInventario.classList.add('is-equipped');
                
                const clone = itemInventario.cloneNode(true);
                clone.classList.remove('is-equipped');
                clone.classList.add('em-destaque');
                
                if (socketsVazios.length > 0) {
                    socketsVazios[0].appendChild(clone);
                }
                if (countDestaque) countDestaque.textContent = data.count;
            }
        }
    }

    // DELEGAÇÃO DE EVENTOS: Garante que os cliques funcionem mesmo após os elementos se moverem
    if (areaInventario) {
        areaInventario.addEventListener('click', (e) => {
            const item = e.target.closest('.achievement-item.unlocked');
            if (item) processarCliqueConquista(item);
        });
    }

    if (areaDestaque) {
        areaDestaque.addEventListener('click', (e) => {
            const item = e.target.closest('.achievement-item');
            if (!item) return;
            // Acha o original na grid e manda o clique pra ele
            const original = areaInventario.querySelector(`.achievement-item[data-pa-id="${item.dataset.paId}"]`);
            if (original) processarCliqueConquista(original);
        });
    }

    // Delegação para o Hover (Preview)
    document.addEventListener('mouseover', (e) => {
        const item = e.target.closest('.achievement-item');
        if (item && (areaDestaque?.contains(item) || areaInventario?.contains(item))) {
            updatePreview(item);
        }
    });

    // Lógica do botão VER MAIS
    const btnVerMais = document.getElementById('btn-ver-mais-mods');
    if (btnVerMais) {
        btnVerMais.addEventListener('click', (e) => {
            document.querySelectorAll('.tranca-extra').forEach(el => el.classList.remove('d-none'));
            e.target.parentElement.remove(); 
        });
    }

    // Atualiza os bônus da tela principal ao fechar
    const modalEl = document.getElementById('modalConquistas');
    if (modalEl) {
        modalEl.addEventListener('hidden.bs.modal', () => location.reload());
    }
    

    // ── Equipar Cosmético
    document.querySelectorAll('.btn-cosmetico').forEach(btn => {
        btn.addEventListener('click', async function() {
            SFX.click();
            const { ok, data } = await cyberFetch(window.PROFILE_URLS.equiparCosmetico, { 
                player_item_id: this.dataset.piId 
            });

            if (ok && data.ok) {
                SFX.equip();
                showToast('Cosmético atualizado.', 'ok');
                setTimeout(() => location.reload(), 600);
            } else {
                SFX.error();
                showToast(data.error || 'Erro ao equipar.', 'error');
            }
        });
    });

    // ── Equipar Passivo no Slot
    document.querySelectorAll('.inv-slot-select').forEach(sel => {
        sel.addEventListener('change', async function() {
            if (!this.value) return;
            SFX.click();
            const { ok, data } = await cyberFetch(window.PROFILE_URLS.equiparPassivo, { 
                player_item_id: this.dataset.piId, slot: parseInt(this.value) 
            });

            if (ok && data.ok) {
                SFX.equip();
                showToast(data.mensagem || 'Módulo instalado no slot.', 'ok');
                setTimeout(() => location.reload(), 600);
            } else {
                SFX.error();
                showToast(data.mensagem || 'Erro ao alocar módulo.', 'error');
                this.value = ""; // reseta o select
            }
        });
    });

    // ── Remover Passivo do Slot
    document.querySelectorAll('.btn-desocupar').forEach(btn => {
        btn.addEventListener('click', async function() {
            SFX.click();
            const { ok, data } = await cyberFetch(window.PROFILE_URLS.equiparPassivo, { 
                player_item_id: this.dataset.piId, slot: null 
            });

            if (ok && data.ok) {
                SFX.unequip();
                showToast('Módulo removido do slot.', 'ok');
                setTimeout(() => location.reload(), 600);
            } else {
                SFX.error();
                showToast('Erro ao remover módulo.', 'error');
            }
        });
    });

    // ── Lógica de Seleção e Slider de Injeção
    let consumivelSelecionadoId = null;
    
    const injectorContainer = document.getElementById('injector-container');
    const injectorThumb = document.getElementById('injector-thumb');
    const injectorFill = document.querySelector('.injector-fill');
    const injectorText = document.getElementById('injector-text');
    
    let isDragging = false;
    let startX = 0;
    let maxDrag = 0;

    // 1. Lógica de clicar na carta para liberar o slider
    document.querySelectorAll('#tab-modal-cons .item-card--consumable').forEach(card => {
        card.addEventListener('click', function() {
            if (typeof SFX !== 'undefined') SFX.tab();
            
            const isSelected = this.classList.contains('selected-card');
            document.querySelectorAll('#tab-modal-cons .item-card--consumable').forEach(c => c.classList.remove('selected-card'));
            
            if (isSelected) {
                consumivelSelecionadoId = null;
                if (injectorContainer) {
                    injectorContainer.className = 'injector-locked';
                    injectorText.innerHTML = '<i class="bi bi-lock-fill me-2"></i> SELECIONE UMA CARGA';
                }
            } else {
                this.classList.add('selected-card');
                consumivelSelecionadoId = this.dataset.piId;
                if (injectorContainer) {
                    injectorContainer.className = 'injector-ready';
                    injectorText.innerHTML = 'DESLIZE PARA INJETAR <i class="bi bi-chevron-double-right ms-2"></i>';
                }
            }
        });
    });

    // 2. Lógica de Arrastar o Slider
    if (injectorThumb) {
        // Eventos de Mouse e Touch
        injectorThumb.addEventListener('mousedown', startDrag);
        injectorThumb.addEventListener('touchstart', startDrag, {passive: true});

        document.addEventListener('mousemove', drag);
        document.addEventListener('touchmove', drag, {passive: false});

        document.addEventListener('mouseup', endDrag);
        document.addEventListener('touchend', endDrag);
    }

    function startDrag(e) {
        if (injectorContainer.classList.contains('injector-locked') || injectorContainer.classList.contains('injector-firing')) return;
        
        isDragging = true;
        startX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
        maxDrag = injectorContainer.offsetWidth - injectorThumb.offsetWidth - 8; // 8px de margem (left 4 + right 4)
        
        // Tira o tempo de transição pra não ter "lag" no mouse
        injectorThumb.style.transition = 'none';
        injectorFill.style.transition = 'none';
    }

    function drag(e) {
        if (!isDragging) return;
        // e.preventDefault(); // Evita scroll no celular enquanto arrasta
        
        let currentX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
        let deltaX = currentX - startX;
        
        // Trava o movimento entre 0 e o final da barra
        let pos = Math.max(0, Math.min(deltaX, maxDrag));
        
        injectorThumb.style.transform = `translateX(${pos}px)`;
        injectorFill.style.width = `${pos + 10}px`; // +10 pra barra não ficar atrás do botão
        
        // Verifica se chegou ao fim (98% da barra para garantir)
        if (pos >= maxDrag * 0.98) {
            isDragging = false;
            injetarCarga();
        }
    }

    function endDrag() {
        if (!isDragging) return;
        isDragging = false;
        
        // Se soltou antes de chegar no fim, a mola puxa de volta
        injectorThumb.style.transition = 'transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
        injectorFill.style.transition = 'width 0.3s ease';
        
        injectorThumb.style.transform = 'translateX(0px)';
        injectorFill.style.width = '0px';
    }

    // 3. O Disparo para o Backend
    async function injetarCarga() {
        if (!consumivelSelecionadoId) return;
        
        if (typeof SFX !== 'undefined') SFX.click();
        
        // Trava a UI em estado de injeção
        injectorContainer.className = 'injector-firing';
        injectorThumb.style.transform = `translateX(${maxDrag}px)`;
        injectorText.innerHTML = '<i class="bi bi-cpu me-2"></i> INJETANDO CÓDIGO...';

        const { ok, data } = await cyberFetch(window.PROFILE_URLS.usarConsumivel, { 
            player_item_id: consumivelSelecionadoId 
        });

        if (ok && data.ok) {
            if (typeof SFX !== 'undefined') SFX.equip();
            if (typeof showToast !== 'undefined') showToast(data.mensagem || 'Carga tática injetada.', 'ok');
            injectorText.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i> SUCESSO';
            setTimeout(() => location.reload(), 1000);
        } else {
            if (typeof SFX !== 'undefined') SFX.error();
            if (typeof showToast !== 'undefined') showToast(data.mensagem || 'Falha ao injetar carga.', 'error');
            
            // Falhou? Reseta o slider para o estado 'ready'
            injectorContainer.className = 'injector-ready';
            injectorText.innerHTML = 'FALHA. TENTE NOVAMENTE <i class="bi bi-chevron-double-right ms-2"></i>';
            injectorThumb.style.transform = 'translateX(0px)';
            injectorFill.style.width = '0px';
        }
    }

    // ── Battle Pass — coletar recompensa ────────
    document.querySelectorAll('.btn-bp-coletar').forEach(btn => {
        btn.addEventListener('click', async function() {
            const tier    = parseInt(this.dataset.tier);
            const descricao = this.dataset.descricao;

            const res  = await fetch("{% url 'profiles:bp_coletar' %}", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
                body: JSON.stringify({ tier }),
            });
            const data = await res.json();

            if (data.ok) {
                // Feedback visual antes de reload
                this.textContent = '✓ COLETADO!';
                this.disabled    = true;
                this.closest('.bp-tier').classList.add('bp-coletado');
                this.closest('.bp-tier').classList.remove('bp-disponivel');
                setTimeout(() => location.reload(), 800);
            } else {
                alert(data.mensagem);
            }
        });
    });

    // ── Trocar Classe
    const btnTrocarClasse = document.getElementById('btn-trocar-classe');
    if (btnTrocarClasse) {
        btnTrocarClasse.addEventListener('click', async function() {
            SFX.click();
            const novaClasse = prompt("Digite o código da nova classe (guardian, analyst, sentinel, hacker):");
            if (!novaClasse) return;

            const { ok, data } = await cyberFetch(window.PROFILE_URLS.trocarClasse, { 
                classe: novaClasse.toLowerCase().trim() 
            });

            if (ok && data.ok) {
                SFX.equip();
                showToast(data.mensagem, 'ok');
                setTimeout(() => location.reload(), 1000);
            } else {
                SFX.error();
                showToast(data.mensagem || data.error, 'error');
            }
        });
    }

    // ── Retake Token
    document.querySelectorAll('.btn-retake-log').forEach(btn => {
        btn.addEventListener('click', async function() {
            SFX.click();
            // Pega o ID do quiz da row (ajuste caso tenha passado no HTML dataset)
            const quizId = prompt("Confirme o ID do Quiz para aplicar o Retake:");
            if (!quizId) return;

            const { ok, data } = await cyberFetch(window.PROFILE_URLS.usarRetake, { 
                quiz_id: quizId 
            });

            if (ok && data.ok) {
                SFX.equip();
                showToast(data.mensagem, 'ok');
                setTimeout(() => location.reload(), 1000);
            } else {
                SFX.error();
                showToast(data.error || 'Erro ao aplicar token.', 'error');
            }
        });
    });

});