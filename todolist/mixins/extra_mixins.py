from django.urls import reverse
from django.views.generic.base import ContextMixin
from django.utils.timezone import make_aware
from todolist.models import WorkDateModel
from datetime import datetime


class WorkModeDialogMixin(ContextMixin):
    model_for_workmode = WorkDateModel
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        queryset = self.workmode_queryset if hasattr(self, 'workmode_queryset') else None
        context['workmode_info'] = self.workmode_check(queryset=queryset)
        return context
    
    def get_object_for_workmode(self, queryset=None):
        if queryset is None:
            queryset = self.model_for_workmode.objects.filter(user=self.request.user.id).all()
        obj = queryset.filter(work_date=make_aware(datetime.today())).first()
        return obj
    
    def workmode_check(self, queryset=None):
        object_for_workmode = self.get_object_for_workmode(queryset)
        if object_for_workmode is None:
            buttons = [
                {'name' : '作業データ作成', 'url'  : reverse('todolist:workdatemodel_new')}, 
                {'name' : 'キャンセル',     'url'  : None}
            ]
            messages = ['本日の作業データが登録されていません。', '作業データを登録してください']
            
            workmode_info = {
                'status'      : 'no_today_model', 
                'dialog_data' : {'messages' : messages, 'buttons' : buttons}
            }
            
        elif object_for_workmode.is_finished:
            buttons = [
                {'name' : '確認',           'url' : None}
            ]
            messages = ['本日の作業は既に完了しています。']
            
            workmode_info = {
                'status'      : 'already_finished', 
                'dialog_data' : {'messages' : messages, 'buttons' : buttons}
            }
            
        elif len(object_for_workmode.todomodel_list.all()) == 0:
            buttons = [
                {'name' : 'ToDo登録',       'url' : reverse('todolist:workdatemodel_edit', kwargs={'slug' : object_for_workmode.slug})}, 
                {'name' : 'キャンセル',     'url' : None}
            ]
            messages = ['ToDoが本日の作業データに登録されていません。', 'ToDoを登録してください。']
            
            workmode_info = {
                'status'      : 'no_todo', 
                'dialog_data' : {'messages' : messages, 'buttons' : buttons}
            }
            
        else:
            for todomodel in object_for_workmode.todomodel_list.all():
                if not(todomodel.expected_time):
                    buttons = [
                        {'name' : 'ToDo更新',   'url' : reverse('todolist:workdatemodel_edit', kwargs={'slug' : object_for_workmode.slug})}, 
                        {'name' : 'キャンセル', 'url' : None}
                    ]
                    messages = ['ToDoの未入力項目があります。', 'ToDoの項目を入力してください。']
                    
                    workmode_info = {
                        'status'      : 'no_detail_in_todo', 
                        'dialog_data' : {'messages' : messages, 'buttons' : buttons}
                    }
                    break
            else:
                workmode_info = {
                    'status'      : 'available', 
                    'url'         : reverse('todolist:workmode', kwargs={'slug' : object_for_workmode.slug, 'order' : 1}), 
                    'dialog_data' : None
                }
        return workmode_info
