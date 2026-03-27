# apps/missions/admin.py
from django.contrib import admin
from .models import MissionTemplate, UserMissionSet, UserMission, MissionConfig

@admin.register(MissionConfig)
class MissionConfigAdmin(admin.ModelAdmin):
    list_display = ('reward_xp', 'reward_coins')

@admin.register(MissionTemplate)
class MissionTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'description_template', 'code', 'category', 'difficulty', 'is_active')
    list_filter = ('category', 'difficulty', 'is_active')
    search_fields = ('title', 'code', 'description_template')
    list_editable = ('code',) 

class UserMissionInline(admin.TabularInline):
    model = UserMission
    extra = 0
    readonly_fields = ('title_generated', 'target_value')

@admin.register(UserMissionSet)
class UserMissionSetAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'is_completed', 'is_claimed')
    list_filter = ('is_completed', 'is_claimed')
    inlines = [UserMissionInline]