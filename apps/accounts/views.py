from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'core:home')
            return redirect(next_url)
        else:
            messages.error(request, 'Credenciais inválidas. Tente novamente.')

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def alterar_senha_view(request):
    if request.method == 'POST':
        senha_atual   = request.POST.get('senha_atual', '')
        nova_senha    = request.POST.get('nova_senha', '')
        confirma_senha = request.POST.get('confirma_senha', '')

        if not request.user.check_password(senha_atual):
            messages.error(request, 'Senha atual incorreta.')
        elif nova_senha != confirma_senha:
            messages.error(request, 'As novas senhas não coincidem.')
        elif len(nova_senha) < 8:
            messages.error(request, 'A nova senha deve ter ao menos 8 caracteres.')
        else:
            request.user.set_password(nova_senha)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Senha alterada com sucesso.')
            return redirect('profiles:index')

    return render(request, 'accounts/alterar_senha.html')