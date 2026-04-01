from .models import MissionTemplate, UserMissionSet, UserMission, MissionDifficulty
from apps.profiles.models import PlayerNotification
import random
from django.db import transaction

class MissionService:
    @staticmethod
    def get_or_create_set(user):
        active_set = UserMissionSet.objects.filter(user=user, is_claimed=False).first()
        if active_set:
            return active_set

        new_set = UserMissionSet.objects.create(user=user)
        used_categories = []

        for diff in [MissionDifficulty.EASY, MissionDifficulty.MEDIUM, MissionDifficulty.HARD]:
            # Busca templates excluindo categorias já sorteadas
            templates = MissionTemplate.objects.filter(
                difficulty=diff, 
                is_active=True
            ).exclude(category__in=used_categories)

            # Fallback de segurança caso não haja categorias inéditas disponíveis
            if not templates.exists():
                templates = MissionTemplate.objects.filter(difficulty=diff, is_active=True)

            if templates.exists():
                template = random.choice(templates)
                target = random.randint(template.min_target, template.max_target)
                
                UserMission.objects.create(
                    mission_set=new_set,
                    template=template,
                    target_value=target,
                    title_generated=template.description_template.format(target=target)
                )
                used_categories.append(template.category)

        return new_set
    
    @staticmethod
    @transaction.atomic
    def claim_reward(user):
        from .models import UserMissionSet, MissionConfig
        
        active_set = UserMissionSet.objects.filter(
            user=user, 
            is_completed=True, 
            is_claimed=False
        ).first()
        
        if not active_set:
            return False, "Nenhum set pronto para resgate."

        from apps.profiles.services import grant_xp, grant_coins
        
        config = MissionConfig.get()
        xp_ganho = config.reward_xp
        coins_ganhas = config.reward_coins
        
        grant_xp(user, xp_ganho, fonte='missao', descricao='Bônus: Set de Missões Completo')
        grant_coins(user, coins_ganhas, fonte='missao')

        active_set.is_claimed = True
        active_set.save()

        PlayerNotification.objects.create(
            player=user,
            tipo='missao',
            titulo='Recompensas Resgatadas!',
            mensagem=f'Você recebeu {xp_ganho} XP e {coins_ganhas} GC pelo seu esforço.',
            icone='bi-gift-fill'
        )

        MissionService.get_or_create_set(user)
        return True, "Resgate concluído com sucesso!"
    
    @staticmethod
    def update_progress(user, mission_code, amount=1, is_perfect=False, is_speedrun=False):
        from .models import UserMission
        
        # CORREÇÃO: Usando 'template__code' para bater com seu models.py
        active_missions = UserMission.objects.filter(
            mission_set__user=user,
            mission_set__is_claimed=False,
            template__code=mission_code,
            is_completed=False
        )

        for mission in active_missions:
            mission.update_progress(amount)

        if is_perfect:
            perfect_code = f"{mission_code}_PERFECT"
            MissionService._trigger_special_mission(user, perfect_code)

        if is_speedrun:
            speedrun_code = f"{mission_code}_SPEEDRUN"
            MissionService._trigger_special_mission(user, speedrun_code)

    @staticmethod
    def _trigger_special_mission(user, special_code):
        from .models import UserMission
        # CORREÇÃO: Usando 'template__code' aqui também
        specials = UserMission.objects.filter(
            mission_set__user=user,
            mission_set__is_claimed=False,
            template__code=special_code,
            is_completed=False
        )
        for m in specials:
            m.update_progress(1)
