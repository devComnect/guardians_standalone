"""
Data migration — popula o campo `icon` de todos os itens existentes.
Mapeado por item_id canônico. Rodar após 0002_item_icon.
"""

from django.db import migrations


ICON_MAP = {
    # ── CONSUMÍVEIS ────────────────────────────────────────
    1:   'bi-arrow-counterclockwise',   # Backup de Memória — retake
    2:   'bi-graph-up-arrow',           # Injetor de Overclock — XP boost
    3:   'bi-bar-chart-steps',          # Expansor de Cache — streak cap
    4:   'bi-snow',                     # Protocolo Persistência — freeze
    5:   'bi-binoculars-fill',          # Sniffer de Metadados — hint
    6:   'bi-heart-pulse-fill',         # Buffer de Contingência — extra life
    7:   'bi-currency-exchange',        # Script de Arbitragem — coins→XP
    8:   'bi-cash-coin',                # Monetizador de Expertise — XP→coins

    # ── PASSIVOS — ECONOMY ────────────────────────────────
    101: 'bi-safe2-fill',              # Cold Wallet — XP per coin
    102: 'bi-credit-card-2-front-fill', # Cartão Clonado — shop discount
    103: 'bi-exclamation-diamond-fill', # Algoritmo de Escassez — low cash XP
    104: 'bi-123',                      # Bit de Paridade — odd cash XP

    # ── PASSIVOS — SPEEDRUN ───────────────────────────────
    105: 'bi-speedometer2',            # Overclock Instável — time-/XP+
    106: 'bi-optical-audio-fill',      # Fibra Óptica Direta — XP per second

    # ── PASSIVOS — UTILITY ────────────────────────────────
    107: 'bi-cpu-fill',                # CPU 128 Cores — add time

    # ── PASSIVOS — SKILL ──────────────────────────────────
    108: 'bi-lightning-fill',          # Brute Force — quick win XP

    # ── PASSIVOS — SYNERGY ───────────────────────────────
    109: 'bi-diagram-3-fill',          # Middleware — same rarity XP
    110: 'bi-hdd-network-fill',        # Cluster de Nodes — XP per common
    111: 'bi-layout-sidebar-inset',    # Framework Minimalista — empty slot XP

    # ── PASSIVOS — BUFF ───────────────────────────────────
    112: 'bi-shield-fill-plus',        # Firewall Camada 7 — stack multiplier

    # ── PASSIVOS — SOCIAL ─────────────────────────────────
    113: 'bi-person-badge-fill',       # Perfil Ostentação — XP per cosmetic
    114: 'bi-megaphone-fill',          # Influencer — XP per achievement

    # ── PASSIVOS — RANKING ───────────────────────────────
    115: 'bi-trophy-fill',             # Líder do Quadrante — top 3 XP
    116: 'bi-arrow-up-right-circle-fill', # Underdog Protocol — outside top 10

    # ── PASSIVOS — SCALING ───────────────────────────────
    117: 'bi-stars',                   # Veterano — XP per level

    # ── PASSIVOS — SPECIFIC ──────────────────────────────
    118: 'bi-braces',                  # Rainbow Tables — code challenge XP
    119: 'bi-wifi',                    # Wi-Fi Sniffer — patrol challenge XP
    120: 'bi-file-earmark-binary-fill', # Rev-Eng — decrypt challenge XP

    # ── PASSIVOS — LUCK ──────────────────────────────────
    121: 'bi-dice-5-fill',             # Backdoor Adormecido — random XP

    # ── PASSIVOS — TIME ──────────────────────────────────
    122: 'bi-calendar2-star-fill',     # Mestre de Cerimônia — double XP week

    # ── COSMÉTICOS — FRAMES ───────────────────────────────
    201: 'bi-terminal-fill',           # Neon Terminal
    202: 'bi-droplet-fill',            # Blood Matrix
    203: 'bi-gem',                     # Golden Root
    204: 'bi-fire',                    # Plasma Fire
    205: 'bi-circle-fill',             # Deep Void

    # ── COSMÉTICOS — BACKGROUNDS ─────────────────────────
    211: 'bi-grid-3x3-gap-fill',       # Circuit Grid
    212: 'bi-cloud-rain-fill',         # Digital Rain
    213: 'bi-reception-4',             # Glitch Static
    214: 'bi-sunset-fill',             # Synthwave Sunset
    215: 'bi-tools',                   # Blueprint Schematics

    # ── COSMÉTICOS — TITLES ───────────────────────────────
    221: 'bi-bug-fill',                # Caçador de Bugs
    222: 'bi-incognito',               # Fantasma Digital
    223: 'bi-radioactive',             # Engenheiro do Caos
    224: 'bi-person-fill-add',         # Rookie Protocol
    225: 'bi-key-fill',                # Mestre das Senhas
    226: 'bi-shield-fill-check',       # Firewall Humano
    227: 'bi-0-circle-fill',           # Zero Day
    228: 'bi-eye-fill',                # Sentinela da Rede
    229: 'bi-code-slash',              # Script Kiddie
    230: 'bi-wrench-adjustable-circle-fill', # Arquiteto de Exploit
}


def populate_icons(apps, schema_editor):
    Item = apps.get_model('store', 'Item')
    for item_id, icon in ICON_MAP.items():
        Item.objects.filter(item_id=item_id).update(icon=icon)


def reverse_icons(apps, schema_editor):
    Item = apps.get_model('store', 'Item')
    Item.objects.all().update(icon='bi-box')


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_item_icon'),
    ]

    operations = [
        migrations.RunPython(populate_icons, reverse_icons),
    ]