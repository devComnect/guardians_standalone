from .models import SystemLog

def registrar_log(user, tipo, titulo, descricao='', xp_delta=0, coin_delta=0, breakdown=None):
    SystemLog.objects.create(
        player=user,
        tipo=tipo,
        titulo=titulo,
        descricao=descricao,
        xp_delta=xp_delta,
        coin_delta=coin_delta,
        breakdown=breakdown or {},
    )