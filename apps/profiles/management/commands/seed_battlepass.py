from django.core.management.base import BaseCommand


# XP acumulado por tier (curva: fácil no início, tryhard no final)
# Casual chega ~tier 20-25 | Regular ~tier 30-35 | Dedicado ~tier 40-45 | Tryhard ~tier 50
BP_XP_CURVE = [
    # tier: xp_acumulado
    (1,  400),    (2,  900),    (3,  1500),   (4,  2200),   (5,  3000),
    (6,  3900),   (7,  4900),   (8,  6000),   (9,  7200),   (10, 8500),
    (11, 10000),  (12, 11600),  (13, 13300),  (14, 15100),  (15, 17000),
    (16, 19000),  (17, 21100),  (18, 23300),  (19, 25600),  (20, 28000),
    (21, 30500),  (22, 33100),  (23, 35800),  (24, 38600),  (25, 41500),
    (26, 44500),  (27, 47600),  (28, 50800),  (29, 54100),  (30, 57500),
    (31, 61000),  (32, 64600),  (33, 68300),  (34, 72100),  (35, 76000),
    (36, 80000),  (37, 84100),  (38, 88300),  (39, 92600),  (40, 97000),
    (41, 101500), (42, 106100), (43, 110800), (44, 115600), (45, 120500),
    (46, 126000), (47, 132000), (48, 138500), (49, 145500), (50, 153000),
]

# Recompensas por tier
# (tier, tipo, coins, item_nome_ou_None, descricao)
BP_REWARDS = [
    # Faixa Iniciante (1-10) — pequenas recompensas motivacionais
    (1,  'coins',     50,  None,                     '50 Guardian Coins'),
    (2,  'item',       0,  'Sniffer de Metadados',   'Sniffer de Metadados (1 uso)'),
    (3,  'coins',    100,  None,                     '100 Guardian Coins'),
    (4,  'cosmetico',  0,  'Frame: Guardião',        'Frame: Guardião'),
    (5,  'coins',    150,  None,                     '150 Guardian Coins'),
    (6,  'item',       0,  'Vida Reserva',           'Vida Reserva (3 usos)'),
    (7,  'coins',    200,  None,                     '200 Guardian Coins'),
    (8,  'item',       0,  'Injetor de Overclock',   'Injetor de Overclock'),
    (9,  'coins',    250,  None,                     '250 Guardian Coins'),
    (10, 'cosmetico',  0,  'Frame: Hacker',          'Frame: Hacker'),

    # Faixa Regular (11-25) — recompensas mais substanciais
    (11, 'coins',    300,  None,                     '300 Guardian Coins'),
    (12, 'item',       0,  'Lanterna',               'Lanterna (5 usos)'),
    (13, 'coins',    350,  None,                     '350 Guardian Coins'),
    (14, 'item',       0,  'Multiplicador de Coins', 'Multiplicador de Coins'),
    (15, 'coins',    400,  None,                     '400 Guardian Coins'),
    (16, 'item',       0,  'Escudo de Streak',       'Escudo de Streak'),
    (17, 'coins',    450,  None,                     '450 Guardian Coins'),
    (18, 'item',       0,  'Amplificador I',         'Amplificador I (+25% XP)'),
    (19, 'coins',    500,  None,                     '500 Guardian Coins'),
    (20, 'item',       0,  'Catalisador',            'Upgrade: Catalisador'),

    (21, 'coins',    500,  None,                     '500 Guardian Coins'),
    (22, 'item',       0,  'Amplificador II',        'Amplificador II (+50% XP)'),
    (23, 'coins',    600,  None,                     '600 Guardian Coins'),
    (24, 'item',       0,  'Sinergia',               'Upgrade: Sinergia'),
    (25, 'coins',    750,  None,                     '750 Guardian Coins — marco!'),

    # Faixa Dedicado (26-40) — recompensas raras
    (26, 'item',       0,  'Escudo de Streak',       'Escudo de Streak'),
    (27, 'coins',    600,  None,                     '600 Guardian Coins'),
    (28, 'item',       0,  'Moldura de Destaque',    'Upgrade: Moldura de Destaque'),
    (29, 'coins',    650,  None,                     '650 Guardian Coins'),
    (30, 'item',       0,  'Amplificador II',        'Amplificador II (+50% XP)'),

    (31, 'coins',    700,  None,                     '700 Guardian Coins'),
    (32, 'item',       0,  'Momentum',               'Upgrade: Momentum'),
    (33, 'coins',    750,  None,                     '750 Guardian Coins'),
    (34, 'item',       0,  'Token de Retake',        'Token de Retake'),
    (35, 'coins',    800,  None,                     '800 Guardian Coins'),

    (36, 'item',       0,  'Colecionador',           'Upgrade: Colecionador'),
    (37, 'coins',    850,  None,                     '850 Guardian Coins'),
    (38, 'item',       0,  'Núcleo Amplificado',     'Upgrade: Núcleo Amplificado'),
    (39, 'coins',    900,  None,                     '900 Guardian Coins'),
    (40, 'item',       0,  'Amplificador III',       'Amplificador III (+100% XP)'),

    # Faixa Tryhard (41-50) — recompensas lendárias
    (41, 'coins',   1000,  None,                     '1.000 Guardian Coins'),
    (42, 'item',       0,  'Token de Retake',        'Token de Retake'),
    (43, 'coins',   1000,  None,                     '1.000 Guardian Coins'),
    (44, 'item',       0,  'Slot de Expansão',       'Upgrade: Slot de Expansão'),
    (45, 'coins',   1200,  None,                     '1.200 Guardian Coins'),

    (46, 'item',       0,  'Amplificador III',       'Amplificador III (+100% XP)'),
    (47, 'coins',   1500,  None,                     '1.500 Guardian Coins'),
    (48, 'item',       0,  'Frame: Lendário',        'Frame Lendário — Exclusivo'),
    (49, 'coins',   2000,  None,                     '2.000 Guardian Coins'),
    (50, 'item',       0,  'Token de Retake',        '🏆 TIER MÁXIMO — Token de Retake + Título Especial'),
]


class Command(BaseCommand):
    help = 'Cria o Battle Pass para a Season ativa'

    def handle(self, *args, **kwargs):
        from apps.rankings.models import Season
        from apps.profiles.models import BattlePassConfig, BattlePassTier
        from apps.store.models import Item

        season = Season.objects.filter(ativa=True).first()
        if not season:
            self.stdout.write(self.style.ERROR('Nenhuma Season ativa. Crie uma primeiro.'))
            return

        bp, created = BattlePassConfig.objects.get_or_create(
            season=season, defaults={'ativo': True}
        )

        if not created and bp.tiers.exists():
            self.stdout.write(self.style.WARNING(
                f'Battle Pass para Season {season.numero} já existe. Pulando seed.'
            ))
            return

        xp_map = dict(BP_XP_CURVE)
        criados = 0

        for tier_num, tipo, coins, item_nome, descricao in BP_REWARDS:
            item = None
            if item_nome:
                item = Item.objects.filter(nome=item_nome, disponivel=True).first()
                if not item:
                    self.stdout.write(
                        self.style.WARNING(f'  Item não encontrado: "{item_nome}" — tier {tier_num} sem item')
                    )

            _, was_created = BattlePassTier.objects.get_or_create(
                battle_pass=bp,
                tier=tier_num,
                defaults={
                    'xp_necessario':      xp_map[tier_num],
                    'recompensa_tipo':    tipo,
                    'recompensa_coins':   coins,
                    'recompensa_item':    item,
                    'recompensa_descricao': descricao,
                }
            )
            if was_created:
                criados += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Battle Pass Season {season.numero} criado com {criados} tiers.'
        ))