from django.urls import reverse
import math


class DialogMixin():
    
    def workmode_check(self):
        if self.object is None:
            buttons = [
                {'name' : '作業データ作成', 'url'  : reverse('todolist:workdatemodel_new')}, 
                {'name' : 'キャンセル', 'url'  : None}
            ]
            messages = ['本日の作業データが登録されていません。', '作業データを登録してください']
            workmode_info = {
                'status'      : 'no_today_model', 
                'dialog_data' : {'messages' : messages, 'buttons' : buttons}
            }
        elif self.object.is_finished:
            buttons = [
                {'name' : '確認', 'url' : None}
            ]
            messages = ['本日の作業は既に完了しています。']
            workmode_info = {
                'status'      : 'already_finished', 
                'dialog_data' : {'messages' : messages, 'buttons' : buttons}
            }
        elif len(self.object.todomodel_list.all()) == 0:
            buttons = [
                {'name' : 'ToDo登録', 'url' : reverse('todolist:workdatemodel_edit', kwargs={'slug' : self.object.slug})}, 
                {'name' : 'キャンセル', 'url' : None}
            ]
            messages = ['ToDoが本日の作業データに登録されていません。', 'ToDoを登録してください。']
            workmode_info = {
                'status'      : 'no_todo', 
                'dialog_data' : {'messages' : messages, 'buttons' : buttons}
            }
        else:
            for todomodel in self.object.todomodel_list.all():
                if not(todomodel.expected_time):
                    buttons = [
                        {'name' : 'ToDo更新', 'url' : reverse('todolist:workdatemodel_edit', kwargs={'slug' : self.object.slug})}, 
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
                    'url'         : reverse('todolist:workmode', kwargs={'slug' : self.object.slug, 'order' : 1}), 
                    'dialog_data' : None
                }
        return workmode_info


class UnitExchangeMixin:
    
    def min_to_sec_in_form_fields(self, obj, form, *field_names):
        """
        クライアントから返ってきたフォームに対して、フォーム内の特定のフィールドの値を分から秒に単位変換する。
        
        obj：フォームにPOSTされたフィールドの値が反映されたモデルインスタンス。
        
        objを引数に取るのは、①FormSet内のフォームの場合と②そうでない場合でobjの取得方法が違うため。
        ①動的にフォーム数が変化するFormSet内のフォームの場合
            POSTされたFormSet内のフォーム数がクライアント側で動的に変化するため、form.instanceではobjを取得できない。
            それに加えて、ModelChoiceFieldでフォームのTodoModelを選択するため、cleaned_data['title']でモデルインスタンスを取得する。
        ②FormSet内のフォームでない場合（Form単体）
            form.instanceでモデルインスタンスを取得する。
        """
        prev_obj = obj.__class__.objects.filter(pk=obj.id).first()
        
        def should_update(field_name):
            if prev_obj is None:
                return True
            prev_val = getattr(prev_obj, field_name) or 0
            val      = form.cleaned_data[field_name] or 0
            prev_val = math.ceil(prev_val / 60)
            return prev_val != val
        
        for field_name in field_names:
            if should_update(field_name):
                val = form.cleaned_data[field_name] if form.cleaned_data[field_name] else 0
                val *= 60
            else:
                val = getattr(prev_obj, field_name)
            setattr(obj, field_name, val)
        return obj


