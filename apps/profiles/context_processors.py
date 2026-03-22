def notifications(request):
    if not request.user.is_authenticated:
        return {}
    unread = request.user.notifications.filter(lida=False)
    return {
        'notificacoes_nao_lidas': unread[:10],
        'notificacoes_count':     unread.count(),
    }