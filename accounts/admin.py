from django.contrib import admin

# Register your models here.

from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _
from .models import CustomUser


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = '__all__'


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('last_name', 'first_name', 'username', 'email',)}), 
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}), 
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}), 
        )
    add_fieldsets = (
        (None, {
            'classes': ('wide', ), 
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')}
        ), 
    )
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ('full_name', 'username', 'email',)
    list_display_links = ('username', )
    # list_editable = None
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups',)
    search_fields = ('username', 'email',)
    ordering = ('email', 'username', )
    
    
    def full_name(self, user):
        return user.get_full_name().strip()
    full_name.short_description = '名前'