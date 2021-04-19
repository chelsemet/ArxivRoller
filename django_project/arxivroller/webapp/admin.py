from django.contrib import admin

from .models import Paper, UserPreference, UserPaper, S2Info

# Register your models here.

class UserPreferenceAdmin(admin.ModelAdmin):
    exclude = ['user']
    list_display = ['user']

admin.site.register(UserPreference, UserPreferenceAdmin)

class UserPaperAdmin(admin.ModelAdmin):
    exclude = ['user', 'paper']
    list_display = ['id', 'paper', 'get_user']
    
    def get_user(self, obj):
        return obj.user.username

admin.site.register(UserPaper, UserPaperAdmin)

class PaperAdmin(admin.ModelAdmin):
    exclude = ['categories_m2m', 'authors_m2m', 'user']
    list_display = ['title', 'updated']
admin.site.register(Paper, PaperAdmin)


admin.site.register(S2Info)