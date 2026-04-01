from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


# ─────────────────────────────────────────────
# SIGNAL EXISTENTE — Conquistas após XP
# ─────────────────────────────────────────────

@receiver(post_save, sender='profiles.XPEvent')
def verificar_conquistas_apos_xp(sender, instance, created, **kwargs):
    if not created:
        return

    from apps.profiles.services import verificar_conquistas

    user  = instance.player
    fonte = instance.fonte

    universais = ['xp_total', 'level_reached', 'ofensiva', 'streak_days']

    mapa = {
        'quiz':      ['quiz_count', 'quiz_perfect', 'all_daily_count'],
        'decriptar': ['decriptar_count', 'minigame_count', 'all_daily_count'],
        'codigo':    ['codigo_count',    'minigame_count', 'all_daily_count'],
        'password':  ['minigame_count',  'all_daily_count'],
        'patrol':    ['patrol_count',    'all_daily_count'],
        'bonus':     [],
        'conquista': [],
        'missao':    [],
    }

    triggers = universais + mapa.get(fonte, [])
    for trigger in triggers:
        verificar_conquistas(user, trigger)


# ─────────────────────────────────────────────
# NOVOS SIGNALS — SystemLog
# ─────────────────────────────────────────────

@receiver(post_save, sender='profiles.XPEvent')
def log_xp_event(sender, instance, created, **kwargs):
    if not created:
        return

    from apps.profiles.log_service import registrar_log

    tipo = 'xp_gain' if instance.xp_total > 0 else 'xp_loss'

    registrar_log(
        user=instance.player,
        tipo=tipo,
        titulo=instance.descricao,
        descricao=instance.fonte,
        xp_delta=instance.xp_total,
        breakdown={
            "xp_base":        instance.xp_base,
            "bonus_breakdown": instance.breakdown,   # lista detalhada real
            "xp_bonus_total": instance.xp_bonus,
            "xp_final":       instance.xp_total,
            "extra":          {"fonte": instance.fonte},
        }
    )


# ─────────────────────────────────────────────
# LEVEL UP
# ─────────────────────────────────────────────

_player_level_cache = {}
_player_classe_cache = {}


@receiver(pre_save,  sender='profiles.Player')
def cache_player_state(sender, instance, **kwargs):
    """Captura level e classe antes do save para detectar mudanças."""
    if not instance.pk:
        return
    valores = instance.__class__.objects.filter(
        pk=instance.pk
    ).values('level', 'classe', 'coins').first()
    if valores:
        _player_level_cache[instance.pk]  = valores['level']
        _player_classe_cache[instance.pk] = (valores['classe'], valores['coins'])


@receiver(post_save, sender='profiles.Player')
def log_level_up(sender, instance, created, **kwargs):
    if created:
        return

    from apps.profiles.log_service import registrar_log

    nivel_anterior = _player_level_cache.pop(instance.pk, None)
    if nivel_anterior and instance.level > nivel_anterior:
        registrar_log(
            user=instance.user,
            tipo='level_up',
            titulo=f'LEVEL UP → {instance.level}',
            breakdown={
                "nivel_anterior": nivel_anterior,
                "nivel_novo": instance.level,
            }
        )


@receiver(post_save, sender='profiles.Player')
def log_classe_change(sender, instance, created, **kwargs):
    if created:
        return

    from apps.profiles.log_service import registrar_log
    from apps.profiles.models import ClasseConfig

    cached = _player_classe_cache.pop(instance.pk, None)
    if not cached:
        return

    classe_anterior, _ = cached
    if classe_anterior != instance.classe:
        config = ClasseConfig.get()
        
        is_primeira_vez = (classe_anterior == 'none')
        
        if is_primeira_vez:
            custo = config.custo_primeira_classe
            titulo_log = f'Primeira Classe: {instance.get_classe_display()}'
        else:
            custo = config.custo_troca_coins
            titulo_log = f'Classe alterada: {classe_anterior} → {instance.classe}'

        registrar_log(
            user=instance.user,
            tipo='classe_change',
            titulo=titulo_log,
            coin_delta=-custo,
            breakdown={
                "classe_anterior": classe_anterior,
                "classe_nova": instance.classe,
                "custo": custo,
            }
        )


# ─────────────────────────────────────────────
# CONQUISTA DESBLOQUEADA
# ─────────────────────────────────────────────

@receiver(post_save, sender='profiles.PlayerAchievement')
def log_achievement(sender, instance, created, **kwargs):
    if not created:
        return

    from apps.profiles.log_service import registrar_log

    registrar_log(
        user=instance.player,
        tipo='achievement',
        titulo=f'Conquista: {instance.achievement.nome}',
        breakdown={
            "code":        instance.achievement.code,
            "raridade":    instance.achievement.raridade,
            "bonus_type":  instance.achievement.bonus_type,
            "bonus_value": instance.achievement.bonus_value,
        }
    )


# ─────────────────────────────────────────────
# LOJA — registrado via função para evitar import circular
# ─────────────────────────────────────────────

def _register_store_signals():
    try:
        from apps.store.models import StoreTransaction

        TIPO_MAP = {
            'purchase': 'item_purchase',
            'sell':     'item_sell',
            'activate': 'item_activate',
            'reroll':   'store_reroll',
            'convert':  'coin_gain',
        }

        @receiver(post_save, sender=StoreTransaction)
        def log_store_transaction(sender, instance, created, **kwargs):
            if not created:
                return

            from apps.profiles.log_service import registrar_log

            tipo_log = TIPO_MAP.get(instance.tipo, 'system')
            titulo   = instance.descricao or (
                f'{instance.get_tipo_display()}: {instance.item.name}'
                if instance.item else instance.get_tipo_display()
            )

            breakdown = {"tipo_transacao": instance.tipo}
            if instance.item:
                breakdown.update({
                    "item_id":   instance.item.item_id,
                    "item_name": instance.item.name,
                    "raridade":  instance.item.raridade,
                    "effect":    instance.item.effect,
                })
            if instance.coins_delta:
                breakdown["custo"]              = abs(instance.coins_delta)
                breakdown["desconto_aplicado"]  = instance.desconto_aplicado
            if instance.xp_delta:
                breakdown["xp_convertido"] = instance.xp_delta

            registrar_log(
                user=instance.player,
                tipo=tipo_log,
                titulo=titulo,
                xp_delta=instance.xp_delta,
                coin_delta=instance.coins_delta,
                breakdown=breakdown,
            )

    except Exception:
        pass


# ─────────────────────────────────────────────
# MISSÕES
# ─────────────────────────────────────────────

def _register_mission_signals():
    try:
        from apps.missions.models import UserMissionSet

        @receiver(post_save, sender=UserMissionSet)
        def log_mission_claim(sender, instance, created, **kwargs):
            if created or not instance.is_claimed:
                return

            from apps.profiles.log_service import registrar_log
            from apps.profiles.models import SystemLog

            # Evita log duplicado
            if SystemLog.objects.filter(
                player=instance.user,
                tipo='mission_claim',
                breakdown__mission_set_id=instance.pk,
            ).exists():
                return

            try:
                from apps.missions.models import MissionConfig
                config      = MissionConfig.get()
                xp_reward   = config.reward_xp
                coin_reward = config.reward_coins
            except Exception:
                xp_reward = coin_reward = 0

            missoes = list(instance.missions.values_list('title_generated', flat=True))

            registrar_log(
                user=instance.user,
                tipo='mission_claim',
                titulo='Missões Resgatadas',
                xp_delta=xp_reward,
                coin_delta=coin_reward,
                breakdown={
                    "mission_set_id": instance.pk,
                    "xp_reward":      xp_reward,
                    "coin_reward":    coin_reward,
                    "missoes":        missoes,
                }
            )

    except Exception:
        pass


# ─────────────────────────────────────────────
# BATTLE PASS
# ─────────────────────────────────────────────

def _register_battle_pass_signals():
    try:
        from apps.profiles.models import PlayerBattlePass

        _bp_tiers_cache = {}

        @receiver(pre_save, sender=PlayerBattlePass)
        def cache_bp_tiers(sender, instance, **kwargs):
            if instance.pk:
                anterior = instance.__class__.objects.filter(
                    pk=instance.pk
                ).values_list('tiers_coletados', flat=True).first()
                _bp_tiers_cache[instance.pk] = list(anterior or [])

        @receiver(post_save, sender=PlayerBattlePass)
        def log_battle_pass_tier(sender, instance, created, **kwargs):
            if created:
                return

            from apps.profiles.log_service import registrar_log

            tiers_anteriores = set(_bp_tiers_cache.pop(instance.pk, []))
            tiers_novos      = set(instance.tiers_coletados) - tiers_anteriores

            for tier_num in tiers_novos:
                tier_obj = instance.battle_pass.tiers.filter(tier=tier_num).first()
                if not tier_obj:
                    continue
                registrar_log(
                    user=instance.player,
                    tipo='battle_pass',
                    titulo=f'Battle Pass — Tier {tier_num} Coletado',
                    coin_delta=tier_obj.recompensa_coins,
                    breakdown={
                        "tier":                 tier_num,
                        "recompensa_tipo":      tier_obj.recompensa_tipo,
                        "recompensa_descricao": tier_obj.recompensa_descricao,
                        "coins":                tier_obj.recompensa_coins,
                        "item": str(tier_obj.recompensa_item) if tier_obj.recompensa_item else None,
                    }
                )

    except Exception:
        pass