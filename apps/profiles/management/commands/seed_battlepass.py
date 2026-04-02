from django.core.management.base import BaseCommand

BP_XP_CURVE = [
    (1, 400), (2, 900), (3, 1500), (4, 2200), (5, 3000),
    (6, 4000), (7, 5200), (8, 6500), (9, 8000), (10, 9800),
    (11, 11800), (12, 14000), (13, 16500), (14, 19200), (15, 22200),
    (16, 25500), (17, 29000), (18, 32800), (19, 37000), (20, 41500),
    (21, 46300), (22, 51500), (23, 57000), (24, 62800), (25, 69000),
    (26, 75500), (27, 82300), (28, 89500), (29, 97000), (30, 105000),
    (31, 113500), (32, 122500), (33, 132000), (34, 142000), (35, 152500),
    (36, 163500), (37, 175000), (38, 187000), (39, 199500), (40, 212500),
    (41, 226000), (42, 240000), (43, 254500), (44, 269500), (45, 285000),
    (46, 301000), (47, 317500), (48, 334500), (49, 352000), (50, 370000),
]

BP_REWARDS = [
    (1, 'coins', 50, None, '50 Coins'),
    (2, 'item', 0, 'Sniffer de Metadados', 'Sniffer de Metadados (FREE_HINT)'),
    (3, 'coins', 75, None, '75 Coins'),
    (4, 'item', 0, 'Backup de Memória', 'Backup de Memória (TOKEN_RETAKE)'),
    (5, 'cosmetic', 0, 'Rookie Protocol', 'Título COMMON'),
    (6, 'coins', 75, None, '75 Coins'),
    (7, 'item', 0, 'Buffer de Contingência', 'Buffer de Contingência (EXTRA_LIFE_TIME)'),
    (8, 'coins', 100, None, '100 Coins'),
    (9, 'item', 0, 'Sniffer de Metadados', 'Sniffer de Metadados x2'),
    (10, 'cosmetic', 0, 'Deep Void', 'Frame COMMON'),
    (11, 'coins', 100, None, '100 Coins'),
    (12, 'item', 0, 'Injetor de Overclock', 'Injetor de Overclock (XP_BOOST 3d)'),
    (13, 'coins', 125, None, '125 Coins'),
    (14, 'item', 0, 'Protocolo Persistência', 'Protocolo Persistência (STREAK_FREEZE)'),
    (15, 'cosmetic', 0, 'Script Kiddie', 'Título COMMON'),
    (16, 'coins', 125, None, '125 Coins'),
    (17, 'item', 0, 'Backup de Memória', 'Backup de Memória (TOKEN_RETAKE)'),
    (18, 'coins', 150, None, '150 Coins'),
    (19, 'item', 0, 'Expansor de Cache', 'Expansor de Cache (STREAK_CAP_BOOST)'),
    (20, 'cosmetic', 0, 'Circuit Grid', 'Background COMMON'),
    (21, 'coins', 150, None, '150 Coins'),
    (22, 'item', 0, 'Buffer de Contingência', 'Buffer de Contingência x2'),
    (23, 'coins', 175, None, '175 Coins'),
    (24, 'item', 0, 'Injetor de Overclock', 'Injetor de Overclock (XP_BOOST 3d)'),
    (25, 'cosmetic', 0, 'Caçador de Bugs', 'Título RARE'),
    (26, 'coins', 175, None, '175 Coins'),
    (27, 'item', 0, 'Backup de Memória', 'Backup de Memória (TOKEN_RETAKE)'),
    (28, 'coins', 200, None, '200 Coins'),
    (29, 'item', 0, 'Protocolo Persistência', 'Protocolo Persistência x2'),
    (30, 'cosmetic', 0, 'Digital Rain', 'Background RARE'),
    (31, 'coins', 200, None, '200 Coins'),
    (32, 'item', 0, 'Injetor de Overclock', 'Injetor de Overclock (XP_BOOST 3d)'),
    (33, 'coins', 225, None, '225 Coins'),
    (34, 'item', 0, 'Script de Arbitragem', 'Script de Arbitragem (CONVERT_GOLD_XP)'),
    (35, 'cosmetic', 0, 'Fantasma Digital', 'Título RARE'),
    (36, 'coins', 250, None, '250 Coins'),
    (37, 'item', 0, 'Backup de Memória', 'Backup de Memória (TOKEN_RETAKE)'),
    (38, 'coins', 250, None, '250 Coins'),
    (39, 'item', 0, 'Expansor de Cache', 'Expansor de Cache x2'),
    (40, 'cosmetic', 0, 'Plasma Fire', 'Frame RARE'),
    (41, 'coins', 300, None, '300 Coins'),
    (42, 'item', 0, 'Injetor de Overclock', 'Injetor de Overclock (XP_BOOST 3d)'),
    (43, 'coins', 300, None, '300 Coins'),
    (44, 'item', 0, 'Monetizador de Expertise', 'Monetizador de Expertise (CONVERT_XP_GOLD)'),
    (45, 'cosmetic', 0, 'Firewall Humano', 'Título EPIC'),
    (46, 'coins', 400, None, '400 Coins'),
    (47, 'item', 0, 'Backup de Memória', 'Backup de Memória (TOKEN_RETAKE)'),
    (48, 'coins', 400, None, '400 Coins'),
    (49, 'cosmetic', 0, 'Blood Matrix', 'Frame EPIC'),
    (50, 'cosmetic', 0, 'Synthwave Sunset', 'Background EPIC'),
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
                item = Item.objects.filter(name=item_nome, disponivel=True).first()
                if not item:
                    self.stdout.write(
                        self.style.WARNING(f'Item não encontrado: "{item_nome}" — tier {tier_num} sem item')
                    )

            _, was_created = BattlePassTier.objects.get_or_create(
                battle_pass=bp,
                tier=tier_num,
                defaults={
                    'xp_necessario': xp_map[tier_num],
                    'recompensa_tipo': tipo,
                    'recompensa_coins': coins,
                    'recompensa_item': item,
                    'recompensa_descricao': descricao,
                }
            )
            if was_created:
                criados += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Battle Pass Season {season.numero} criado com {criados} tiers.'
        ))