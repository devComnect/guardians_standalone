"""
apps/store/management/commands/seed_store_items.py

Popula o banco com todos os itens do JSON de design (MVP v2.0).
Idempotente: usa update_or_create no item_id.

Uso:
    python manage.py seed_store_items
"""
from django.core.management.base import BaseCommand
from apps.store.models import Item

CONSUMABLES = [
    {
        "item_id": 1, "name": "Backup de Memória", "raridade": "COMMON", "cost": 20,
        "effect": "TOKEN_RETAKE", "value": 1, "duration_days": 0,
        "description": "Permite refazer um desafio falho sem perder progresso.",
        "build": "NONE",
    },
    {
        "item_id": 2, "name": "Injetor de Overclock", "raridade": "COMMON", "cost": 50,
        "effect": "XP_BOOST_DAYS", "value": 30, "duration_days": 3,
        "description": "+30% XP em todos os desafios por 3 dias.",
        "build": "NONE",
    },
    {
        "item_id": 3, "name": "Expansor de Cache", "raridade": "RARE", "cost": 80,
        "effect": "STREAK_CAP_BOOST", "value": 25, "duration_days": 3,
        "description": "+25 no teto da ofensiva (streak) por 3 dias.",
        "build": "NONE",
    },
    {
        "item_id": 4, "name": "Protocolo Persistência", "raridade": "RARE", "cost": 100,
        "effect": "STREAK_FREEZE", "value": 0, "duration_days": 2,
        "description": "Congela e protege sua streak por 2 dias.",
        "build": "NONE",
    },
    {
        "item_id": 5, "name": "Sniffer de Metadados", "raridade": "COMMON", "cost": 30,
        "effect": "FREE_HINT", "value": 1, "duration_days": 0,
        "description": "Próximo desafio tem 1 dica grátis sem penalidade.",
        "build": "NONE",
    },
    {
        "item_id": 6, "name": "Buffer de Contingência", "raridade": "RARE", "cost": 60,
        "effect": "EXTRA_LIFE_TIME", "value": 30, "duration_days": 1,
        "description": "+30s de tempo e +1 vida no próximo desafio.",
        "build": "NONE",
    },
    {
        "item_id": 7, "name": "Script de Arbitragem", "raridade": "EPIC", "cost": 100,
        "effect": "CONVERT_GOLD_XP", "value": 150, "value_secondary": 100, "duration_days": 0,
        "description": "Troca imediata: 100 Coins → 150 XP.",
        "build": "NONE",
    },
    {
        "item_id": 8, "name": "Monetizador de Expertise", "raridade": "EPIC", "cost": 0,
        "effect": "CONVERT_XP_GOLD", "value": 80, "value_secondary": 500, "duration_days": 0,
        "description": "Troca imediata: 500 XP → 80 Coins.",
        "build": "NONE",
    },
]

PASSIVES = [
    {"item_id": 101, "name": "Cold Wallet",            "raridade": "COMMON", "cost": 60,  "build": "ECONOMY",  "effect": "XP_PER_COIN",                 "value": 0.1, "max_bonus": 20,  "description": "+1% XP por cada 10 Coins em saldo (Máx 20%)."},
    {"item_id": 102, "name": "Cartão Clonado",         "raridade": "RARE",   "cost": 150, "build": "ECONOMY",  "effect": "SHOP_DISCOUNT",               "value": 15,  "description": "15% de desconto em todos os itens da loja."},
    {"item_id": 103, "name": "Algoritmo de Escassez",  "raridade": "COMMON", "cost": 40,  "build": "ECONOMY",  "effect": "XP_LOW_CASH",                 "value": 20,  "description": "+20% bônus de XP se tiver menos de 10 Coins."},
    {"item_id": 104, "name": "Bit de Paridade",        "raridade": "COMMON", "cost": 40,  "build": "ECONOMY",  "effect": "XP_ODD_CASH",                 "value": 25,  "description": "+25% bônus de XP se o saldo de Coins for ÍMPAR."},
    {"item_id": 105, "name": "Overclock Instável",     "raridade": "RARE",   "cost": 120, "build": "SPEEDRUN", "effect": "TIME_REDUCTION_XP_BOOST",     "value": -30, "value_secondary": 50, "description": "-30% tempo no desafio, mas ganha +50% XP."},
    {"item_id": 106, "name": "Fibra Óptica Direta",    "raridade": "COMMON", "cost": 60,  "build": "SPEEDRUN", "effect": "XP_PER_SECOND",               "value": 1,   "max_bonus": 30,  "description": "+1% XP por cada segundo restante ao finalizar (Máx 30%)."},
    {"item_id": 107, "name": "CPU 128 Cores",          "raridade": "COMMON", "cost": 50,  "build": "UTILITY",  "effect": "ADD_TIME",                    "value": 15,  "description": "Adiciona +15 segundos fixos em todo desafio."},
    {"item_id": 108, "name": "Brute Force",            "raridade": "COMMON", "cost": 40,  "build": "SKILL",    "effect": "XP_QUICK_WIN",                "value": 20,  "description": "+20% XP se vencer em menos de 3 tentativas."},
    {"item_id": 109, "name": "Middleware",             "raridade": "EPIC",   "cost": 200, "build": "SYNERGY",  "effect": "XP_SAME_RARITY",              "value": 30,  "description": "+30% XP se todos os 4 itens forem da mesma raridade."},
    {"item_id": 110, "name": "Cluster de Nodes",       "raridade": "COMMON", "cost": 45,  "build": "SYNERGY",  "effect": "XP_PER_COMMON",               "value": 10,  "max_bonus": 40,  "description": "+10% XP para cada item COMUM equipado."},
    {"item_id": 111, "name": "Framework Minimalista",  "raridade": "RARE",   "cost": 130, "build": "SYNERGY",  "effect": "XP_PER_EMPTY_SLOT",           "value": 40,  "max_bonus": 120, "description": "+40% XP para cada slot de item vazio."},
    {"item_id": 112, "name": "Firewall Camada 7",      "raridade": "COMMON", "cost": 70,  "build": "BUFF",     "effect": "XP_STACK_MULTIPLIER",         "value": 10,  "description": "Aumenta em +10% todos os bônus de XP já ativos."},
    {"item_id": 113, "name": "Perfil Ostentação",      "raridade": "RARE",   "cost": 110, "build": "SOCIAL",   "effect": "XP_PER_COSMETIC",             "value": 10,  "max_bonus": 30,  "description": "+10% XP para cada cosmético equipado."},
    {"item_id": 114, "name": "Influencer",             "raridade": "COMMON", "cost": 45,  "build": "SOCIAL",   "effect": "XP_PER_FEATURED_ACHIEVEMENT", "value": 5,   "max_bonus": 15,  "description": "+5% XP para cada conquista em destaque."},
    {"item_id": 115, "name": "Líder do Quadrante",     "raridade": "EPIC",   "cost": 250, "build": "RANKING",  "effect": "XP_TOP_3",                    "value": 50,  "description": "+50% bônus de XP se estiver no Top 3 Geral."},
    {"item_id": 116, "name": "Underdog Protocol",      "raridade": "RARE",   "cost": 100, "build": "RANKING",  "effect": "XP_OUTSIDE_TOP_10",           "value": 30,  "description": "+30% bônus de XP se estiver fora do Top 10."},
    {"item_id": 117, "name": "Veterano",               "raridade": "COMMON", "cost": 55,  "build": "SCALING",  "effect": "XP_PER_LEVEL",                "value": 1,   "max_bonus": 50,  "description": "+1% XP de bônus para cada Nível do player."},
    {"item_id": 118, "name": "Rainbow Tables",         "raridade": "COMMON", "cost": 50,  "build": "SPECIFIC", "effect": "XP_CODE_CHALLENGE",           "value": 30,  "description": "+30% XP em desafios de Código."},
    {"item_id": 119, "name": "Wi-Fi Sniffer",          "raridade": "COMMON", "cost": 50,  "build": "SPECIFIC", "effect": "XP_PATROL_CHALLENGE",         "value": 30,  "description": "+30% XP em desafios de Patrulha."},
    {"item_id": 120, "name": "Rev-Eng",                "raridade": "COMMON", "cost": 50,  "build": "SPECIFIC", "effect": "XP_DECRYPT_CHALLENGE",        "value": 30,  "description": "+30% XP em desafios de Decriptar."},
    {"item_id": 121, "name": "Backdoor Adormecido",    "raridade": "RARE",   "cost": 90,  "build": "LUCK",     "effect": "XP_RANDOM",                   "value": 5,   "max_bonus": 25,  "description": "Bônus aleatório entre 5% e 25% por desafio."},
    {"item_id": 122, "name": "Mestre de Cerimônia",    "raridade": "EPIC",   "cost": 220, "build": "TIME",     "effect": "DOUBLE_XP_WEEK_FIRST",        "value": 100, "description": "Dobra a pontuação do primeiro desafio feito na semana."},
]

COSMETICS = [
    # Frames
    {"item_id": 201, "name": "Neon Terminal",       "raridade": "RARE",   "cost": 80,  "build": "NONE", "effect": "COSMETIC_FRAME",      "description": "Frame com estética de terminal neon."},
    {"item_id": 202, "name": "Blood Matrix",        "raridade": "EPIC",   "cost": 150, "build": "NONE", "effect": "COSMETIC_FRAME",      "description": "Frame com chuva de dados vermelho."},
    {"item_id": 203, "name": "Golden Root",         "raridade": "EPIC",   "cost": 180, "build": "NONE", "effect": "COSMETIC_FRAME",      "description": "Frame com raízes douradas."},
    {"item_id": 204, "name": "Plasma Fire",         "raridade": "RARE",   "cost": 90,  "build": "NONE", "effect": "COSMETIC_FRAME",      "description": "Frame com chamas de plasma."},
    {"item_id": 205, "name": "Deep Void",           "raridade": "COMMON", "cost": 40,  "build": "NONE", "effect": "COSMETIC_FRAME",      "description": "Frame com o vazio profundo."},
    # Backgrounds
    {"item_id": 211, "name": "Circuit Grid",        "raridade": "COMMON", "cost": 30,  "build": "NONE", "effect": "COSMETIC_BACKGROUND", "description": "Background de grade de circuito."},
    {"item_id": 212, "name": "Digital Rain",        "raridade": "RARE",   "cost": 70,  "build": "NONE", "effect": "COSMETIC_BACKGROUND", "description": "Background de chuva digital."},
    {"item_id": 213, "name": "Glitch Static",       "raridade": "RARE",   "cost": 80,  "build": "NONE", "effect": "COSMETIC_BACKGROUND", "description": "Background com estática de glitch."},
    {"item_id": 214, "name": "Synthwave Sunset",    "raridade": "EPIC",   "cost": 160, "build": "NONE", "effect": "COSMETIC_BACKGROUND", "description": "Background synthwave retrô."},
    {"item_id": 215, "name": "Blueprint Schematics","raridade": "COMMON", "cost": 35,  "build": "NONE", "effect": "COSMETIC_BACKGROUND", "description": "Background de esquemas técnicos."},
    # Títulos
    {"item_id": 221, "name": "Caçador de Bugs",     "raridade": "COMMON", "cost": 25,  "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "Título para os que caçam falhas."},
    {"item_id": 222, "name": "Fantasma Digital",    "raridade": "RARE",   "cost": 75,  "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "Invisível, implacável."},
    {"item_id": 223, "name": "Engenheiro do Caos",  "raridade": "EPIC",   "cost": 140, "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "Sistemas não testados são sistemas vulneráveis."},
    {"item_id": 224, "name": "Rookie Protocol",     "raridade": "COMMON", "cost": 0,   "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "Começando a jornada."},
    {"item_id": 225, "name": "Mestre das Senhas",   "raridade": "RARE",   "cost": 80,  "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "Nenhum cofre resiste."},
    {"item_id": 226, "name": "Firewall Humano",     "raridade": "EPIC",   "cost": 150, "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "A última linha de defesa."},
    {"item_id": 227, "name": "Zero Day",            "raridade": "EPIC",   "cost": 200, "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "Explora o que ainda não foi descoberto."},
    {"item_id": 228, "name": "Sentinela da Rede",   "raridade": "RARE",   "cost": 65,  "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "Vigia incansável."},
    {"item_id": 229, "name": "Script Kiddie",       "raridade": "COMMON", "cost": 15,  "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "Ainda aprendendo. Isso não é um insulto."},
    {"item_id": 230, "name": "Arquiteto de Exploit","raridade": "EPIC",   "cost": 180, "build": "NONE", "effect": "COSMETIC_TITLE",      "description": "Constrói o que outros não imaginam."},
]


class Command(BaseCommand):
    help = 'Popula o banco com os itens MVP do Comnect Guardians v2.0'

    def handle(self, *args, **kwargs):
        todos = (
            [(d, 'consumable') for d in CONSUMABLES] +
            [(d, 'passive')    for d in PASSIVES]    +
            [(d, 'cosmetic')   for d in COSMETICS]
        )

        criados = 0
        atualizados = 0

        for dados, tipo in todos:
            defaults = {
                'name':            dados['name'],
                'description':     dados['description'],
                'tipo':            tipo,
                'raridade':        dados['raridade'],
                'build':           dados.get('build', 'NONE'),
                'effect':          dados['effect'],
                'value':           dados.get('value', 0),
                'value_secondary': dados.get('value_secondary', 0),
                'duration_days':   dados.get('duration_days', 0),
                'max_bonus':       dados.get('max_bonus', 0),
                'cost':            dados.get('cost', 0),
                'disponivel':      True,
            }
            _, criado = Item.objects.update_or_create(
                item_id=dados['item_id'],
                defaults=defaults,
            )
            if criado:
                criados += 1
            else:
                atualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Seed concluído: {criados} criados, {atualizados} atualizados.'
            )
        )