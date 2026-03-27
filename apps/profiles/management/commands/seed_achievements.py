from django.core.management.base import BaseCommand
from apps.profiles.models import Achievement


ACHIEVEMENTS = [
    # ══════════════════════════════════════════════════════
    # QUIZ_COUNT — 3/semana × 13 semanas = ~39 no season
    # ══════════════════════════════════════════════════════
    ('QUIZ_COUNT_1',  'Primeira Validação',
     'Você respondeu. O sistema escutou.',
     'img/conquistas/batismo-de-fogo.png',     'comum',
     'quiz_count', 1,   'quiz_xp_pct', 5),

    ('QUIZ_COUNT_2',  'Linha de Raciocínio',
     'A repetição transformou tentativa em método.',
     'img/conquistas/tiro-certo.png',           'comum',
     'quiz_count', 5,   'quiz_xp_pct', 4),

    ('QUIZ_COUNT_3',  'Consistência Analítica',
     'Erros diminuem quando o padrão se consolida.',
     'img/conquistas/o-letrado.png',            'rara',
     'quiz_count', 15,  'quiz_xp_pct', 6),

    ('QUIZ_COUNT_4',  'Operador Cognitivo',
     'Você processa informação como o próprio sistema.',
     'img/conquistas/expert.png',               'rara',
     'quiz_count', 30,  'quiz_xp_pct', 8),

    ('QUIZ_COUNT_5',  'Arquitetura Mental',
     'Conhecimento deixou de ser adquirido — passou a ser produzido.',
     'img/conquistas/codinome-vaz.png',         'epica',
     'quiz_count', 39,  'quiz_xp_pct', 10),

    # ══════════════════════════════════════════════════════
    # QUIZ_PERFECT — quizzes com 100%
    # ══════════════════════════════════════════════════════
    ('QUIZ_PERFECT_1', 'Resposta Exata',
     'Sem margem para erro. Sem necessidade de.',
     'img/conquistas/tiro-certo.png',           'rara',
     'quiz_perfect', 1,  'quiz_xp_pct', 5),

    ('QUIZ_PERFECT_2', 'Precisão Cirúrgica',
     'Acertar uma vez pode ser sorte. Cinco vezes é método.',
     'img/conquistas/expert.png',               'epica',
     'quiz_perfect', 5,  'quiz_xp_pct', 10),

    ('QUIZ_PERFECT_3', 'Protocolo Sem Falhas',
     'O sistema não encontrou brechas. Você também não.',
     'img/conquistas/guardiao-supremo.png',     'lendaria',
     'quiz_perfect', 15, 'quiz_xp_pct', 15),

    # ══════════════════════════════════════════════════════
    # MINIGAME_COUNT — 5/semana × 13 = ~65 no season
    # ══════════════════════════════════════════════════════
    ('MINIGAME_1',  'Primeiro Protocolo',
     'Você aceitou o desafio fora da teoria.',
     'img/conquistas/fagulha.png',              'comum',
     'minigame_count', 1,   'minigame_xp_pct', 5),

    ('MINIGAME_2',  'Decodificador Iniciante',
     'Padrões começam a ceder sob pressão repetida.',
     'img/conquistas/fagulha-persistente.png',  'comum',
     'minigame_count', 10,  'anagram_xp_pct', 8),

    ('MINIGAME_3',  'Quebrador de Estruturas',
     'Sistemas fechados não permanecem fechados por muito tempo.',
     'img/conquistas/ferro-e-fogo.png',         'rara',
     'minigame_count', 25,  'pw_xp_pct', 12),

    ('MINIGAME_4',  'Operador de Campo',
     'Execução eficiente supera tentativa bruta.',
     'img/conquistas/forja-de-guerra.png',      'rara',
     'minigame_count', 45,  'termo_xp_pct', 15),

    ('MINIGAME_5',  'Especialista em Ruptura',
     'Nenhuma cifra resiste à insistência correta.',
     'img/conquistas/em-chamas.png',            'epica',
     'minigame_count', 65,  'anagram_xp_pct', 20),

    # ══════════════════════════════════════════════════════
    # DECRIPTAR_COUNT
    # ══════════════════════════════════════════════════════
    ('DECRIPTAR_1', 'Primeiro Código Quebrado',
     'Letras embaralhadas revelam sua ordem natural a quem insiste.',
     'img/conquistas/fagulha.png',              'comum',
     'decriptar_count', 1,   'anagram_xp_pct', 5),

    ('DECRIPTAR_2', 'Decifrador em Formação',
     'O caos de dados começa a fazer sentido.',
     'img/conquistas/fagulha-persistente.png',  'rara',
     'decriptar_count', 10,  'anagram_xp_pct', 10),

    ('DECRIPTAR_3', 'Mestre Decifrador',
     'Você lê o ruído como se fosse linguagem.',
     'img/conquistas/em-chamas.png',            'epica',
     'decriptar_count', 30,  'anagram_xp_pct', 20),

    # ══════════════════════════════════════════════════════
    # CODIGO_COUNT (Wordle)
    # ══════════════════════════════════════════════════════
    ('CODIGO_1', 'Primeira Sequência',
     'A palavra estava lá. Você a encontrou.',
     'img/conquistas/fagulha.png',              'comum',
     'codigo_count', 1,   'termo_xp_pct', 5),

    ('CODIGO_2', 'Analista de Padrões',
     'Verde, amarelo, cinza — uma gramática que você aprendeu a ler.',
     'img/conquistas/tiro-certo.png',           'rara',
     'codigo_count', 10,  'termo_xp_pct', 10),

    ('CODIGO_3', 'Criptógrafo',
     'Palavras nunca mais serão apenas palavras.',
     'img/conquistas/codinome-vaz.png',         'epica',
     'codigo_count', 30,  'termo_xp_pct', 18),

    # ══════════════════════════════════════════════════════
    # PATROL_COUNT — 5/semana × 13 = ~65 no season
    # ══════════════════════════════════════════════════════
    ('PATROL_1',  'Primeira Ronda',
     'Você saiu do núcleo e tocou o perímetro.',
     'img/conquistas/caçador-de-phish.png',     'comum',
     'patrol_count', 1,   'patrol_xp_pct', 5),

    ('PATROL_2',  'Vigilância Ativa',
     'A Grid começa a confiar sua fronteira a você.',
     'img/conquistas/mundo-real.png',           'comum',
     'patrol_count', 10,  'patrol_xp_pct', 8),

    ('PATROL_3',  'Controle Territorial',
     'Rotas são seguras porque você passou por elas.',
     'img/conquistas/coruja-da-seguranca.png',  'rara',
     'patrol_count', 25,  'patrol_xp_pct', 12),

    ('PATROL_4',  'Zona Sob Observação',
     'Nada se move sem ser notado.',
     'img/conquistas/firewall-ativo.png',       'rara',
     'patrol_count', 45,  'patrol_xp_pct', 18),

    ('PATROL_5',  'Guardião do Perímetro',
     'O território responde primeiro a você.',
     'img/conquistas/farol-de-vigia.png',       'epica',
     'patrol_count', 65,  'patrol_xp_pct', 25),

    # ══════════════════════════════════════════════════════
    # XP_TOTAL — baseado na curva de XP do jogo
    # ══════════════════════════════════════════════════════
    ('SCORE_1',  'Primeiro Sinal',
     'Você deixou de ser ruído e passou a ser detectado pela Grid.',
     'img/conquistas/veterano-de-guerra.png',   'comum',
     'xp_total', 500,    'global_xp_pct', 1),

    ('SCORE_2',  'Presença Reconhecida',
     'Seu padrão começa a se repetir nos registros do sistema.',
     'img/conquistas/arquiteto-de-elite.png',   'comum',
     'xp_total', 2500,   'global_xp_pct', 2),

    ('SCORE_3',  'Assinatura Estável',
     'A Grid agora prevê sua atuação antes mesmo do impacto.',
     'img/conquistas/seguranca-intergalatica.png', 'rara',
     'xp_total', 10000,  'global_xp_pct', 3),

    ('SCORE_4',  'Anomalia Persistente',
     'Você não é mais exceção — é uma variável permanente.',
     'img/conquistas/lenda-viva.png',           'epica',
     'xp_total', 30000,  'global_xp_pct', 4),

    ('SCORE_5',  'Entidade Registrada',
     'Seu rastro é oficial. Apagar seria custoso demais.',
     'img/conquistas/guardiao-supremo.png',     'lendaria',
     'xp_total', 75000,  'global_xp_pct', 5),

    # ══════════════════════════════════════════════════════
    # STREAK — dias consecutivos
    # ══════════════════════════════════════════════════════
    ('STREAK_1',  'Consistência Inicial',
     'Três dias. A rotina ainda é frágil — mas existe.',
     'img/conquistas/batismo-de-fogo.png',      'comum',
     'streak_days', 3,   'global_xp_pct', 2),

    ('STREAK_2',  'Padrão Estabelecido',
     'Uma semana. O hábito começa a ganhar forma.',
     'img/conquistas/ferro-e-fogo.png',         'comum',
     'streak_days', 7,   'global_xp_pct', 3),

    ('STREAK_3',  'Frequência Calibrada',
     'Quinze dias sem falhar. O sistema confia no seu ritmo.',
     'img/conquistas/forja-de-guerra.png',      'rara',
     'streak_days', 15,  'global_xp_pct', 5),

    ('STREAK_4',  'Presença Constante',
     'Um mês inteiro. Sua ausência seria notada.',
     'img/conquistas/coruja-da-seguranca.png',  'rara',
     'streak_days', 30,  'global_xp_pct', 7),

    ('STREAK_5',  'Sentinela Permanente',
     'Sessenta dias. A Grid não precisa mais te chamar.',
     'img/conquistas/farol-de-vigia.png',       'epica',
     'streak_days', 60,  'global_xp_pct', 10),

    ('STREAK_6',  'Inabalável',
     'Noventa dias. Uma temporada inteira sem falhar.',
     'img/conquistas/guardiao-supremo.png',     'lendaria',
     'streak_days', 90,  'global_xp_pct', 15),

    # ══════════════════════════════════════════════════════
    # LEVEL
    # ══════════════════════════════════════════════════════
    ('LEVEL_1',  'Ativação Confirmada',
     'O núcleo reconheceu sua identidade.',
     'img/conquistas/batismo-de-fogo.png',      'comum',
     'level_reached', 5,  'global_xp_pct', 2),

    ('LEVEL_2',  'Acesso Intermediário',
     'Camadas antes inacessíveis começam a ceder.',
     'img/conquistas/arquiteto-de-elite.png',   'rara',
     'level_reached', 10, 'global_xp_pct', 3),

    ('LEVEL_3',  'Operador Certificado',
     'Suas credenciais são reconhecidas em toda a Grid.',
     'img/conquistas/expert.png',               'rara',
     'level_reached', 20, 'global_xp_pct', 5),

    ('LEVEL_4',  'Classe Elevada',
     'Poucos chegam aqui. Você é um deles.',
     'img/conquistas/lenda-viva.png',           'epica',
     'level_reached', 35, 'global_xp_pct', 7),

    ('LEVEL_5',  'Status Máximo',
     'Nível 50. O topo da hierarquia reconhece seu nome.',
     'img/conquistas/guardiao-supremo.png',     'lendaria',
     'level_reached', 50, 'global_xp_pct', 10),

    # ══════════════════════════════════════════════════════
    # OFENSIVA
    # ══════════════════════════════════════════════════════
    ('OFENSIVA_1', 'Cadência Inicial',
     'O ritmo começa a se impor sobre o silêncio.',
     'img/conquistas/fagulha.png',              'comum',
     'ofensiva', 10,  'ofensiva_teto', 5),

    ('OFENSIVA_2', 'Pressão Sustentada',
     'Constância é uma forma de poder.',
     'img/conquistas/ferro-e-fogo.png',         'rara',
     'ofensiva', 30,  'ofensiva_teto', 10),

    ('OFENSIVA_3', 'Força Consolidada',
     'A ofensiva não é surto — é cultura.',
     'img/conquistas/em-chamas.png',            'epica',
     'ofensiva', 65,  'ofensiva_teto', 15),

    ('OFENSIVA_4', 'Pressão Máxima',
     'Você atingiu a saturação do sistema. Além daqui, é transcendência.',
     'img/conquistas/guardiao-supremo.png',     'lendaria',
     'ofensiva', 120, 'ofensiva_teto', 25),

    # ══════════════════════════════════════════════════════
    # SHOP
    # ══════════════════════════════════════════════════════
    ('SHOP_1',  'Primeiro Investimento',
     'Toda vantagem começa com uma escolha.',
     'img/conquistas/acumulador.png',           'comum',
     'shop_count', 1,   'coin_pct', 2),

    ('SHOP_2',  'Otimização Inicial',
     'Eficiência não é sorte. É acúmulo.',
     'img/conquistas/acumulador.png',           'comum',
     'shop_count', 3,   'coin_pct', 4),

    ('SHOP_3',  'Estrutura Aprimorada',
     'Seu desempenho agora é modular.',
     'img/conquistas/acumulador.png',           'rara',
     'shop_count', 7,   'coin_pct', 6),

    ('SHOP_4',  'Arquitetura de Vantagem',
     'Cada ação rende mais do que antes.',
     'img/conquistas/acumulador.png',           'rara',
     'shop_count', 12,  'coin_pct', 8),

    ('SHOP_5',  'Economia de Guerra',
     'Você não gasta recursos. Você os converte.',
     'img/conquistas/acumulador.png',           'epica',
     'shop_count', 20,  'coin_pct', 10),

    # ══════════════════════════════════════════════════════
    # ALL_DAILY — dias com todos os desafios feitos
    # ══════════════════════════════════════════════════════
    ('ALL_DAILY_1', 'Dia Completo',
     'Nenhuma missão ficou pendente.',
     'img/conquistas/batismo-de-fogo.png',      'rara',
     'all_daily_count', 1,   'global_xp_pct', 3),

    ('ALL_DAILY_2', 'Rotina de Elite',
     'Cinco dias sem deixar nada para trás.',
     'img/conquistas/forja-de-guerra.png',      'epica',
     'all_daily_count', 5,   'global_xp_pct', 5),

    ('ALL_DAILY_3', 'Protocolo Absoluto',
     'Quinze dias. Você não deixa brechas.',
     'img/conquistas/guardiao-supremo.png',     'lendaria',
     'all_daily_count', 15,  'global_xp_pct', 8),

    # ══════════════════════════════════════════════════════
    # FEEDBACK / VULNERABILITY
    # ══════════════════════════════════════════════════════
    ('FEEDBACK_1', 'Voz Ativa',
     'Você não consome o sistema — você o aprimora.',
     'img/conquistas/batismo-de-fogo.png',      'comum',
     'feedback_count', 1,  'global_xp_pct', 1),

    ('FEEDBACK_2', 'Contribuidor Frequente',
     'Seu histórico de feedback é parte do DNA do sistema.',
     'img/conquistas/arquiteto-de-elite.png',   'rara',
     'feedback_count', 5,  'global_xp_pct', 2),

    ('VULNERABILITY_1', 'Caçador de Falhas',
     'Você encontrou o que o sistema não queria que existisse.',
     'img/conquistas/farol-de-vigia.png',       'lendaria',
     'vulnerability', 1,  'global_xp_pct', 5),

    # ══════════════════════════════════════════════════════
    # SEASON — sazonais (sem bônus — prestígio)
    # ══════════════════════════════════════════════════════
    ('SEASON_TOP_3', 'Top 3',
     'Termine uma temporada no Top 3 do ranking.',
     'img/conquistas/top-3.png',                'lendaria',
     'season_top3', 1,  None, 0),

    ('SEASON_TOP_1', 'O Maioral',
     'Termine uma temporada em primeiro lugar.',
     'img/conquistas/o-maioral.png',            'lendaria',
     'season_top1', 1,  None, 0),
]


class Command(BaseCommand):
    help = 'Popula o banco com todas as conquistas do jogo'

    def handle(self, *args, **kwargs):
        created = 0
        raridade_ordem = {'comum': 1, 'rara': 2, 'epica': 3, 'lendaria': 4}

        for i, row in enumerate(ACHIEVEMENTS):
            code, nome, descricao, imagem, raridade, trigger, trigger_val, bonus_type, bonus_val = row
            _, was_created = Achievement.objects.get_or_create(
                code=code,
                defaults={
                    'nome':           nome,
                    'descricao':      descricao,
                    'imagem':         imagem,
                    'raridade':       raridade,
                    'trigger_type':   trigger,
                    'trigger_value':  trigger_val,
                    'bonus_type':     bonus_type,
                    'bonus_value':    bonus_val or 0,
                    'ordem':          (raridade_ordem.get(raridade, 1) * 100) + i,
                }
            )
            if was_created:
                created += 1

        total = Achievement.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'✅ {created} conquista(s) criada(s). Total no banco: {total}.'
        ))