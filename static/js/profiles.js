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

    // ── Conquistas (Destaque)
    document.querySelectorAll('.btn-destaque').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.stopPropagation();
            SFX.click();
            const paId  = this.dataset.paId;
            const ativo = this.dataset.ativo === 'true';

            const { ok, data } = await cyberFetch(window.PROFILE_URLS.destaque, { 
                player_achievement_id: paId, ativar: !ativo 
            });

            if (ok && data.ok) {
                SFX.equip();
                showToast(ativo ? 'Conquista removida dos destaques.' : 'Conquista em destaque!', 'ok');
                setTimeout(() => location.reload(), 600);
            } else {
                SFX.error();
                showToast(data.error || 'Erro ao processar.', 'error');
            }
        });
    });

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

    // ── Usar Consumível
    document.querySelectorAll('.btn-usar-consumivel').forEach(btn => {
        btn.addEventListener('click', async function() {
            SFX.click();
            const { ok, data } = await cyberFetch(window.PROFILE_URLS.usarConsumivel, { 
                player_item_id: this.dataset.piId 
            });

            if (ok && data.ok) {
                SFX.equip();
                showToast(data.mensagem || 'Consumível ativado.', 'ok');
                setTimeout(() => location.reload(), 800);
            } else {
                SFX.error();
                showToast(data.mensagem || 'Erro ao usar consumível.', 'error');
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