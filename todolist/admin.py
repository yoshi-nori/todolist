from django.contrib import admin

from .models import TodoModel, WorkDateModel


class TodoModelAdmin(admin.ModelAdmin):
    """
    todo : filterに期限がいつまでとかでフィルターできるようにする
    """
    list_display = ('id', 'title', 'limit_time', 'achievement_rate', 'user')
    list_filter = ('achievement_rate', 'work_date_model', 'user')
    search_fields = ('title', 'work_date_model', 'user')
    ordering = ('limit_time', 'work_date_model', )

class WorkDateModelAdmin(admin.ModelAdmin):
    # fieldsets = (
        # (None, {'fields' : ('work_date', 'average_plan_excution_time_rate', 'todo_achievement_rate_in_a_day', 'create_at', 'update_at', )}), 
        # ('Todoリスト', {'fields' : ('todo_list', )})
    # )
    list_display = ('id', 'work_date', 'todo_list')
    # list_filter = (, )
    ordering = ('work_date', )
    
    def todo_list(self, workdatemodel):
        # 引数にはPOSTオブジェクトが渡される
        todo_list = TodoModel.objects.filter(work_date_model=workdatemodel).order_by('order').all()
        return todo_list

admin.site.register(TodoModel, TodoModelAdmin)
admin.site.register(WorkDateModel, WorkDateModelAdmin)