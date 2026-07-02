# profiles/management/commands/seed_perks.py
from django.core.management.base import BaseCommand
from apps.profiles.models import Perk

class Command(BaseCommand):
    help = 'Popula/reseta os perks das 4 classes.'

    def handle(self, *args, **kwargs):
        Perk.objects.filter(classe__in=['guardian', 'analyst', 'sentinel', 'hacker']).delete()

        Perk.objects.bulk_create([
            # GUARDIAN — Banqueiro
            Perk(classe='guardian', tipo='xp_quiz',    nome='Investimento Inicial', descricao='Bônus de XP em Quiz.', valor=10, level_required=1),
            Perk(classe='guardian', tipo='coin_bonus', nome='Juros I',              descricao='Bônus de moedas.',     valor=10, level_required=5),
            Perk(classe='guardian', tipo='xp_quiz',    nome='Carteira Diversificada', descricao='Bônus de XP em Quiz.', valor=15, level_required=10),
            Perk(classe='guardian', tipo='coin_bonus', nome='Juros II',             descricao='Bônus de moedas.',     valor=15, level_required=20),
            Perk(classe='guardian', tipo='shop_discount', nome='Cartão Corporativo', descricao='Desconto na loja.',  valor=10, level_required=30),
            Perk(classe='guardian', tipo='coin_bonus', nome='Juros III',            descricao='Bônus de moedas.',     valor=25, level_required=40),
            Perk(classe='guardian', tipo='xp_quiz',    nome='Fundo Soberano',       descricao='Bônus de XP em Quiz.', valor=22, level_required=50),

            # ANALYST — Late Game
            Perk(classe='analyst', tipo='xp_decriptar',   nome='Análise Inicial',    descricao='Bônus de XP em Decriptar.', valor=8, level_required=1),
            Perk(classe='analyst', tipo='global_xp_pct',  nome='Eficiência I',       descricao='Bônus de XP global.',       valor=3, level_required=5),
            Perk(classe='analyst', tipo='xp_decriptar',   nome='Análise Avançada',   descricao='Bônus de XP em Decriptar.', valor=12, level_required=10),
            Perk(classe='analyst', tipo='global_xp_pct',  nome='Eficiência II',      descricao='Bônus de XP global.',       valor=6, level_required=20),
            Perk(classe='analyst', tipo='coin_bonus',     nome='Troco',              descricao='Bônus de moedas.',          valor=5, level_required=30),
            Perk(classe='analyst', tipo='global_xp_pct',  nome='Eficiência III',     descricao='Bônus de XP global.',       valor=9, level_required=40),
            Perk(classe='analyst', tipo='global_xp_pct',  nome='Otimização Total',   descricao='Bônus de XP global.',       valor=15, level_required=50),

            # SENTINEL — Defensor Consistente
            Perk(classe='sentinel', tipo='xp_password',    nome='Vigilância Inicial', descricao='Bônus de XP em Cofre de Senhas.', valor=10, level_required=1),
            Perk(classe='sentinel', tipo='coin_bonus',      nome='Ronda I',            descricao='Bônus de moedas.',                 valor=8, level_required=5),
            Perk(classe='sentinel', tipo='global_xp_pct',   nome='Postura Defensiva',  descricao='Bônus de XP global.',              valor=4, level_required=10),
            Perk(classe='sentinel', tipo='xp_password',     nome='Vigilância Avançada', descricao='Bônus de XP em Cofre de Senhas.', valor=15, level_required=20),
            Perk(classe='sentinel', tipo='ofensiva_teto',   nome='Escudo de Streak',   descricao='Aumenta o teto de bônus de ofensiva.', valor=15, level_required=30),
            Perk(classe='sentinel', tipo='global_xp_pct',   nome='Protocolo Firme',    descricao='Bônus de XP global.',              valor=7, level_required=40),
            Perk(classe='sentinel', tipo='xp_password',     nome='Muralha',            descricao='Bônus de XP em Cofre de Senhas.', valor=25, level_required=50),

            # HACKER — Especialista Agressivo
            Perk(classe='hacker', tipo='xp_codigo',  nome='Exploit Inicial',    descricao='Bônus de XP em Código.', valor=12, level_required=1),
            Perk(classe='hacker', tipo='coin_bonus', nome='Mercado Negro I',    descricao='Bônus de moedas.',       valor=8,  level_required=5),
            Perk(classe='hacker', tipo='xp_codigo',  nome='Exploit Avançado',   descricao='Bônus de XP em Código.', valor=16, level_required=10),
            Perk(classe='hacker', tipo='coin_bonus', nome='Mercado Negro II',   descricao='Bônus de moedas.',       valor=10, level_required=20),
            Perk(classe='hacker', tipo='coin_bonus', nome='Mercado Negro III',  descricao='Bônus de moedas.',       valor=12, level_required=30),
            Perk(classe='hacker', tipo='xp_codigo',  nome='Zero-Day',           descricao='Bônus de XP em Código.', valor=22, level_required=40),
            Perk(classe='hacker', tipo='xp_codigo',  nome='Root Access',        descricao='Bônus de XP em Código.', valor=35, level_required=50),
        ])

        self.stdout.write(self.style.SUCCESS('Perks das 4 classes recriados.'))