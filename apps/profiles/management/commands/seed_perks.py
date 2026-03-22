from django.core.management.base import BaseCommand
from apps.profiles.models import Perk


PERKS = [
    # ── GUARDIAN ──────────────────────────────────────────
    # Tank: vida, streak, coins
    ('guardian', 'xp_global',    'Guardião Iniciante',    'Bônus de XP em todas as atividades.',          5,  1),
    ('guardian', 'coin_bonus',   'Tesouro do Guardião',   'Bônus de moedas em todas as recompensas.',     10, 5),
    ('guardian', 'vida_extra',   'Escudo Adicional',      'Vida extra no Decriptar.',                      1, 10),
    ('guardian', 'streak_shield','Proteção de Streak',    'Protege o streak por 1 dia caso falhe.',        1, 20),
    ('guardian', 'xp_global',    'Guardião Veterano',     'Bônus de XP ampliado.',                        15, 30),
    ('guardian', 'coin_bonus',   'Cofre do Guardião',     'Bônus de moedas ampliado.',                    20, 40),
    ('guardian', 'vida_extra',   'Muralha Viva',          'Mais uma vida extra no Decriptar.',             1, 50),

    # ── ANALYST ───────────────────────────────────────────
    # Suporte: XP em quiz, dicas
    ('analyst',  'xp_quiz',      'Foco Analítico',        'Bônus de XP em quizzes.',                      10, 1),
    ('analyst',  'dica_gratis',  'Consulta Gratuita',     'Dica gratuita por sessão no Decriptar/Código.',  1, 5),
    ('analyst',  'xp_global',    'Mente Estratégica',     'Bônus de XP global.',                           8, 10),
    ('analyst',  'xp_quiz',      'Especialista em Dados', 'Bônus de XP em quizzes ampliado.',             20, 20),
    ('analyst',  'coin_bonus',   'Analista Sênior',       'Bônus de moedas por desempenho.',               15, 30),
    ('analyst',  'dica_gratis',  'Banco de Dados Mental', 'Dica gratuita adicional por sessão.',            1, 40),
    ('analyst',  'xp_quiz',      'Analista Mestre',       'Bônus máximo em quizzes.',                     30, 50),

    # ── SENTINEL ──────────────────────────────────────────
    # Vigilante: Decriptar e Código
    ('sentinel', 'xp_decriptar', 'Olho Treinado',         'Bônus de XP no Decriptar.',                    10, 1),
    ('sentinel', 'xp_codigo',    'Leitor de Padrões',     'Bônus de XP no Código.',                       10, 5),
    ('sentinel', 'vida_extra',   'Resiliência',           'Vida extra no Decriptar.',                       1, 10),
    ('sentinel', 'xp_decriptar', 'Sentinela Avançado',    'Bônus de XP no Decriptar ampliado.',           20, 20),
    ('sentinel', 'xp_codigo',    'Criptoanálise',         'Bônus de XP no Código ampliado.',              20, 30),
    ('sentinel', 'tentativa_extra','Protocolo Extra',     'Tentativa extra no Código.',                     1, 40),
    ('sentinel', 'xp_decriptar', 'Sentinel Supremo',      'Bônus máximo no Decriptar.',                   30, 50),

    # ── HACKER ────────────────────────────────────────────
    # Ofensivo: XP global alto, cofre de senhas
    ('hacker',   'xp_global',    'Acesso Root',           'Bônus de XP global.',                          10, 1),
    ('hacker',   'xp_password',  'Quebrador de Senhas',   'Bônus de XP no Cofre de Senhas.',              15, 5),
    ('hacker',   'coin_bonus',   'Black Market',          'Bônus de moedas em todas as recompensas.',     10, 10),
    ('hacker',   'xp_global',    'Exploit Avançado',      'Bônus de XP global ampliado.',                 18, 20),
    ('hacker',   'xp_password',  'Engenheiro Reverso',    'Bônus de XP no Cofre ampliado.',               25, 30),
    ('hacker',   'coin_bonus',   'Mercado Paralelo',      'Bônus de moedas ampliado.',                    20, 40),
    ('hacker',   'xp_global',    'God Mode',              'Bônus máximo de XP global.',                   25, 50),
]


class Command(BaseCommand):
    help = 'Popula os perks padrão de cada classe'

    def handle(self, *args, **kwargs):
        created = 0
        for classe, tipo, nome, descricao, valor, level_req in PERKS:
            _, was_created = Perk.objects.get_or_create(
                classe=classe, nome=nome,
                defaults={
                    'tipo':           tipo,
                    'descricao':      descricao,
                    'valor':          valor,
                    'level_required': level_req,
                }
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'✅ {created} perk(s) criados.'))