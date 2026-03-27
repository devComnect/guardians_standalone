document.addEventListener('DOMContentLoaded', () => {
    const csrftoken = getCookie('csrftoken');

    // URLs (Idealmente passadas via data-attributes no HTML para evitar hardcode)
    const URL_REROLL = '/loja/reroll/';
    const URL_COMPRAR = '/loja/comprar/';
    const URL_VENDER = '/loja/vender/';

    const btnReroll = document.getElementById('btn-reroll');
    const lojaItemsContainer = document.getElementById('loja-items');
    const playerCoinsDisplay = document.getElementById('player-coins');
    const rerollCostDisplay = document.getElementById('reroll-cost');

    // Utilitário: Pegar CSRF Token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Utilitário: Requisição Fetch padrão
    async function cyberFetch(url, bodyData) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify(bodyData)
            });
            const data = await response.json();
            return { status: response.status, data };
        } catch (error) {
            console.error('Erro de conexão:', error);
            return { status: 500, data: { mensagem: 'Falha de conexão com o servidor.' } };
        }
    }

    // AÇÃO: Reroll
    if (btnReroll) {
        btnReroll.addEventListener('click', async () => {
            btnReroll.disabled = true;
            btnReroll.innerHTML = '> PROCESSANDO...';

            const { status, data } = await cyberFetch(URL_REROLL, {});

            if (status === 200 && data.ok) {
                playerCoinsDisplay.innerText = `${data.coins_atual} ⬡`;
                rerollCostDisplay.innerText = data.proximo_custo;
                
                lojaItemsContainer.innerHTML = '';
                data.novos_itens.forEach(slot => {
                    const discountClass = slot.tem_desconto ? 'discounted' : '';
                    const cardHTML = `
                        <div class="cyber-card rarity-${slot.raridade.toLowerCase()}">
                            <div class="card-header">
                                <span class="item-type">[${slot.tipo.toUpperCase()}]</span>
                                <span class="item-rarity">${slot.raridade}</span>
                            </div>
                            <h3 class="item-name">${slot.name}</h3>
                            <p class="item-desc">${slot.description}</p>
                            <div class="card-footer">
                                <div class="price-tag ${discountClass}">
                                    COST: ${slot.preco_final} ⬡
                                </div>
                                <button class="btn-cyber btn-buy" data-id="${slot.item_id}">COMPRAR</button>
                            </div>
                        </div>
                    `;
                    lojaItemsContainer.insertAdjacentHTML('beforeend', cardHTML);
                });
            } else {
                alert(`[SISTEMA]: ${data.mensagem}`);
            }

            btnReroll.disabled = false;
            btnReroll.innerHTML = `> FORÇAR_REROLL [ <span id="reroll-cost">${data.proximo_custo || rerollCostDisplay.innerText}</span> ⬡ ]`;
        });
    }

    // AÇÃO: Comprar (Usa delegação de eventos para funcionar após o Reroll)
    document.addEventListener('click', async (e) => {
        if (e.target.classList.contains('btn-buy')) {
            const btn = e.target;
            const itemId = btn.getAttribute('data-id');
            
            btn.disabled = true;
            btn.innerText = 'PROCESSANDO...';

            const { status, data } = await cyberFetch(URL_COMPRAR, { item_id: itemId });

            if (status === 200 && data.ok) {
                // Atualiza a tela recarregando para renderizar o inventário e os slots corretamente
                window.location.reload();
            } else {
                alert(`[ERRO DE TRANSAÇÃO]: ${data.mensagem}`);
                btn.disabled = false;
                btn.innerText = 'COMPRAR';
            }
        }
    });

    // AÇÃO: Vender Passivo
    document.addEventListener('click', async (e) => {
        if (e.target.classList.contains('btn-sell')) {
            const btn = e.target;
            const itemId = btn.getAttribute('data-id');
            
            if (!confirm('Deseja vender este upgrade por 50% do valor?')) return;

            btn.disabled = true;
            btn.innerText = 'VENDENDO...';

            const { status, data } = await cyberFetch(URL_VENDER, { item_id: itemId });

            if (status === 200 && data.ok) {
                window.location.reload();
            } else {
                alert(`[ERRO]: ${data.mensagem}`);
                btn.disabled = false;
                btn.innerText = 'VENDER (50%)';
            }
        }
    });
});