from django.db import models
from django.contrib.auth.models import User
import random
from apps.profiles.models import PlayerNotification

class MissionDifficulty(models.TextChoices):
    EASY = 'easy', 'Fácil'
    MEDIUM = 'medium', 'Médio'
    HARD = 'hard', 'Difícil'

class MissionCategory(models.TextChoices):
    QUIZ = 'quiz', 'Quiz'
    PATROL = 'patrol', 'Patrulha (Codebreaker)'
    PASSWORD = 'password', 'Cofre de Senhas'
    DECRYPT = 'decrypt', 'Decriptar (Anagrama)'
    CODE = 'code', 'Código (Termo)'
    STREAK = 'streak', 'Ofensiva'
    FEEDBACK = 'feedback', 'Feedback e Sugestões'
    ANY = 'any', 'Qualquer Desafio'

class MissionTemplate(models.Model):
    title = models.CharField(max_length=100)
    description_template = models.CharField(
        max_length=255, 
        help_text="Use {target} para inserir o valor dinâmico. Ex: 'Vença {target} partidas'"
    )
    category = models.CharField(max_length=20, choices=MissionCategory.choices)
    difficulty = models.CharField(max_length=10, choices=MissionDifficulty.choices)
    
    min_target = models.PositiveIntegerField(default=1)
    max_target = models.PositiveIntegerField(default=5)
    
    xp_reward = models.PositiveIntegerField(default=100)
    coin_reward = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    code = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"[{self.get_difficulty_display()}] {self.title}"

class UserMissionSet(models.Model):
    """O 'baú' de missões atual do jogador."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mission_sets')
    is_claimed = models.BooleanField(default=False, help_text="Se o prêmio do baú foi resgatado")
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Set de {self.user.username} - {self.created_at.strftime('%d/%m/%Y')}"

class UserMission(models.Model):
    """A missão específica vinculada ao progresso do player."""
    mission_set = models.ForeignKey(UserMissionSet, on_delete=models.CASCADE, related_name='missions')
    template = models.ForeignKey(MissionTemplate, on_delete=models.CASCADE)
    
    title_generated = models.CharField(max_length=255)
    target_value = models.PositiveIntegerField()
    current_progress = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    def update_progress(self, amount=1):
        if not self.is_completed:
            self.current_progress += amount
            if self.current_progress >= self.target_value:
                self.current_progress = self.target_value
                self.is_completed = True
                
                # Opcional: Notificar missão individual
                PlayerNotification.objects.create(
                    player=self.mission_set.user,
                    tipo='missao',
                    titulo='Objetivo Alcançado!',
                    mensagem=f'Você concluiu: {self.title_generated}',
                    icone='bi-check-circle-fill'
                )
                
            self.save()
            
            # Verifica se completou o set inteiro
            if not self.mission_set.is_completed:
                if not self.mission_set.missions.filter(is_completed=False).exists():
                    self.mission_set.is_completed = True
                    self.mission_set.save()
                    
                    # NOTIFICAÇÃO DO SET COMPLETO
                    PlayerNotification.objects.create(
                        player=self.mission_set.user,
                        tipo='missao',
                        titulo='🏆 Pacote de Missões Completo!',
                        mensagem='Você finalizou todos os objetivos. Resgate sua recompensa!',
                        icone='bi-trophy-fill',
                    )

    def __str__(self):
        return f"{self.mission_set.user.username}: {self.title_generated} ({self.current_progress}/{self.target_value})"
    

class MissionConfig(models.Model):
    reward_xp = models.PositiveIntegerField(default=10)
    reward_coins = models.PositiveIntegerField(default=50)

    class Meta:
        verbose_name = 'Configuração de Missões'
        verbose_name_plural = 'Configurações de Missões'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Configuração Geral"