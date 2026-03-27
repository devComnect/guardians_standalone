from django.db import migrations

def populate_missions(apps, schema_editor):
    MissionTemplate = apps.get_model('missions', 'MissionTemplate')
    
    missions_data = [
        # EASY
        {"title": "Patrulheiro", "description_template": "Realize {target} patrulha(s) diária(s).", "category": "patrol", "difficulty": "easy", "min_target": 1, "max_target": 2},
        {"title": "Quiz Rápido", "description_template": "Complete {target} Quiz sobre segurança.", "category": "quiz", "difficulty": "easy", "min_target": 1, "max_target": 1},
        {"title": "Jogador Casual", "description_template": "Jogue {target} Minigame (Termo, Anagrama ou Senha).", "category": "any", "difficulty": "easy", "min_target": 1, "max_target": 1},
        {"title": "Mercado Negro", "description_template": "Gaste {target} GC atualizando o estoque da loja (Reroll).", "category": "any", "difficulty": "easy", "min_target": 1, "max_target": 5},
        {"title": "Investidor", "description_template": "Gaste um total de {target} GC na loja.", "category": "any", "difficulty": "easy", "min_target": 1, "max_target": 5},

        # MEDIUM
        {"title": "Patrulha da Cidade", "description_template": "Realize {target} patrulhas.", "category": "patrol", "difficulty": "medium", "min_target": 3, "max_target": 3},
        {"title": "Maratona de Estudos", "description_template": "Complete {target} Quizzes diferentes.", "category": "quiz", "difficulty": "medium", "min_target": 2, "max_target": 3},
        {"title": "Mente Afiada", "description_template": "Jogue {target} rodadas de Minigames.", "category": "any", "difficulty": "medium", "min_target": 2, "max_target": 4},
        {"title": "Raciocínio Rápido", "description_template": "Complete {target} Quizzes em menos de 120 segundos.", "category": "quiz", "difficulty": "medium", "min_target": 1, "max_target": 1},
        {"title": "Hacker Veloz", "description_template": "Vença {target} Minigames em tempo recorde (Speedrun).", "category": "any", "difficulty": "medium", "min_target": 1, "max_target": 3},

        # HARD
        {"title": "Guardião da Net", "description_template": "Complete {target} patrulhas diárias.", "category": "patrol", "difficulty": "hard", "min_target": 3, "max_target": 3},
        {"title": "Mestre dos Jogos", "description_template": "Jogue {target} Minigames para treinar suas habilidades.", "category": "any", "difficulty": "hard", "min_target": 3, "max_target": 4},
        {"title": "Gênio da Turma", "description_template": "Alcance {target} pontos totais em Quizzes.", "category": "quiz", "difficulty": "hard", "min_target": 60, "max_target": 120},
        {"title": "Perfeição Total", "description_template": "Obtenha pontuação perfeita em {target} Quizzes.", "category": "quiz", "difficulty": "hard", "min_target": 2, "max_target": 3},
        {"title": "Execução Impecável", "description_template": "Complete {target} desafios (qualquer tipo) sem erros.", "category": "any", "difficulty": "hard", "min_target": 1, "max_target": 3},
    ]

    for m in missions_data:
        MissionTemplate.objects.create(**m)

class Migration(migrations.Migration):
    dependencies = [
        ('missions', '0001_initial'), # Garanta que o nome aqui seja o da sua migração inicial
    ]
    operations = [
        migrations.RunPython(populate_missions),
    ]