from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import math


# class WorkModeModel(models.Model):
#     # シングルトン実装して作業モードの実行状態を監視する？
#
#     class Meta:
#         verbose_name = '作業モードモデル'
#
#     workdate = models.OneToOneField()
#     is_running = models.BooleanField()
#     has_instance = False
#
#
#     def __str__(self):
#         return self.workdate
#
#     def __new__(self):
#         if self.has_instance:
#             raise Exception('インスタンスは一つまで') 
#         return super().__new__()


class WorkDateModel(models.Model):
    
    class Meta:
        verbose_name = '作業モデル'
        verbose_name_plural = '作業リスト'
        
        constraints = [
            models.UniqueConstraint(
                fields = ['work_date', 'user'], 
                name   = 'unique_workdate_in_user'
            ), 
            models.UniqueConstraint(
                fields = ['slug', 'user'], 
                name   = 'unique_slug_in_user'
            ),
        ]
    
    work_date                       = models.DateField(verbose_name='作業日', null=False, blank=False)
    is_finished                     = models.BooleanField(verbose_name='終了したかどうか', default=False)
    average_plan_excution_time_rate = models.FloatField(verbose_name='平均計画実行時間割合', default=0, blank=True)
    todo_achievement_rate_in_a_day  = models.FloatField(verbose_name='1日の進捗率', default=0, blank=True)
    slug                            = models.SlugField(verbose_name='スラッグ', blank=True)
    create_at                       = models.DateTimeField(verbose_name='登録日時')
    update_at                       = models.DateTimeField(verbose_name='更新日時')
    user                            = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, verbose_name='ユーザー名', null=False, blank=False, related_name='work_date_models')
    
    
    def __str__(self):
        return str(self.work_date)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.create_at = timezone.now()
            self.slug = str(self.work_date)
        self.update_at = timezone.now()
        
        if self.is_finished:
            self.set_average_plan_excution_time_rate()
            self.set_todo_achievement_rate_in_a_day()
        else:
            self.average_plan_excution_time_rate = 0
            self.todo_achievement_rate_in_a_day = 0
        
        return super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        # Adminで一括削除した場合はこのメソッドは呼ばれない。
        todomodel_list = self.todomodel_list.all()
        if len(todomodel_list):
            for todomodel in todomodel_list:
                todomodel.order = 0
                todomodel.save()
        return super().delete(using=using, keep_parents=keep_parents)
    
    def set_average_plan_excution_time_rate(self):
        sum_ptr = 0
        todomodel_list = self.todomodel_list.all()
        for todomodel in todomodel_list:
            sum_ptr += todomodel.plan_excution_time_rate
        self.average_plan_excution_time_rate = "{:.2f}".format(sum_ptr / len(todomodel_list))
    
    def set_todo_achievement_rate_in_a_day(self):
        total_expected_time = 0
        total_todo_achievement_time = 0
        todomodel_list = self.todomodel_list.all()
        for todomodel in todomodel_list:
            total_expected_time += todomodel.expected_time 
            total_todo_achievement_time += todomodel.expected_time * (todomodel.achievement_rate / 100)
        try:
            self.todo_achievement_rate_in_a_day = "{:.2f}".format((total_todo_achievement_time / total_expected_time) * 100)
        except ZeroDivisionError:
            self.todo_achievement_rate_in_a_day = 0


class TodoModel(models.Model):
    
    class Meta:
        verbose_name = 'ToDoモデル'
        verbose_name_plural = 'ToDoリスト'
    
    title                   = models.CharField(verbose_name='ToDo', max_length=100, null=False)
    limit_time              = models.DateTimeField(verbose_name='期限')     # デフォルトのフォーマットはYYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ]
    expected_time           = models.PositiveSmallIntegerField(verbose_name='目標時間（秒）', default=0, blank=True)
    work_date_model         = models.ForeignKey(WorkDateModel, on_delete=models.SET_NULL, verbose_name='作業日', null=True, blank=True, related_name='todomodel_list')
    order                   = models.PositiveSmallIntegerField(verbose_name='作業順', default=0, null=False)
    actual_time             = models.PositiveSmallIntegerField(verbose_name='実際の時間（秒）', default=0)
    plan_excution_time_rate = models.FloatField(verbose_name='計画実行時間割合', default=0, blank=True)
    achievement_rate        = models.IntegerField(verbose_name='ToDo達成割合（%）', default=0)
    create_at               = models.DateTimeField(verbose_name='登録日時')
    update_at               = models.DateTimeField(verbose_name='更新日時')
    user                    = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, verbose_name='ユーザー名', null=False, blank=False, related_name='todomodel_list')
    
    
    field_names_min_to_sec = {'expected_time', 'actual_time'}
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.create_at = timezone.now()
        self.update_at = timezone.now()
        
        if self.work_date_model:
            self.work_date_model.update_at = timezone.now()
        
        if self.achievement_rate != 0:
            self.set_plan_excution_time_rate()
        else:
            self.plan_excution_time_rate = 0
        return super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        if self.work_date_model is not None:
            self.work_date_model.update_at = timezone.now()
            
            # 作業モデルのToDo実行順序を修正する
            todomodel_list = self.work_date_model.todomodel_list.order_by('order').all()
            for todomodel in todomodel_list[self.order:]:
                todomodel.order -= 1
                todomodel.save()
        return super().delete(using=using, keep_parents=keep_parents)
    
    def apply_registered_form(self, order, form, work_date_obj):
        """
        FormSetでクライアント側で動的に作成したフォームをDBに保存する際に利用する。
        動的に作成したFormSetのフォームはインスタンスがFormと結びついておらず、（form.instanceに値が入っていない）
        form.save()してもフォーム入力内容がDBに保存されないため。
        """
        # 基本情報の反映
        self.work_date_model = work_date_obj
        self.order = order
        
        # フォーム入力内容の反映
        cleaned_data = form.cleaned_data
        for key, value in cleaned_data.items():
            if key in ('title', 'id'):
                continue
            elif key in self.field_names_min_to_sec:
                self.convert_form_value_min_to_sec(key, value)
            else:
                setattr(self, key, value)
    
    def apply_deleted_form(self):
        self.work_date_model = None
        self.order = 0
    
    def expected_time_min(self):
        return str(self.expected_time // 60)
    
    def actual_time_min(self):
        m = str(self.actual_time // 60)
        s = str(self.actual_time % 60).zfill(2)
        return m, s
    
    def convert_form_values_min_to_sec(self, form, field_names=field_names_min_to_sec):
        for field_name in form.fields.keys():
            if field_name not in field_names:
                continue
            
            value = form.cleaned_data[field_name] or 0
            instance_exists = True if self.__class__.objects.filter(pk=self.id).first() else False
            
            self.convert_form_value_min_to_sec(field_name, value, instance_exists)
    
    def convert_form_value_min_to_sec(self, field_name, cleaned_val, instance_exists=True):
        def should_update(field_name, cleaned_val):
            # TODO : クエリ発行しないようにするために、新しくタスクを作成する場合は、フォームにチェック入れる等して、
            # DBを参照せずに、formの値から判断するように改善する。
            if not(instance_exists):
                return True
            db_value   = getattr(self, field_name, 0)
            form_value = cleaned_val
            db_value = math.ceil(db_value / 60)
            return db_value != form_value
        
        if should_update(field_name, cleaned_val):
            value = cleaned_val * 60
            setattr(self, field_name, value)
    
    def set_plan_excution_time_rate(self):
        try:
            if self.achievement_rate == 100:
                if self.expected_time is not None:
                    self.plan_excution_time_rate = "{:.2f}".format(self.actual_time / self.expected_time)
            elif self.achievement_rate == 0:
                self.plan_excution_time_rate = 0
            else:
                self.plan_excution_time_rate = "{:.2f}".format(self.actual_time / (self.expected_time * (self.achievement_rate / 100)))
        except ZeroDivisionError:
            self.plan_excution_time_rate = 0
    
    @classmethod
    def evaluate_total_todos(cls, user):
        """これまでの実行した全てのToDoをDBから取得し、平均計画実行時間割合とToDo達成割合を計算して返す"""
        queryset = cls.objects.filter(user=user).exclude(achievement_rate=0).all()
        num = len(queryset)
        total_plan_excution_time_rate = 0
        total_expected_time = 0
        total_todo_achievement_time = 0
        
        for obj in queryset:
            total_plan_excution_time_rate += obj.plan_excution_time_rate
            total_expected_time += obj.expected_time
            total_todo_achievement_time += obj.expected_time * (obj.achievement_rate / 100)
        
        average_plan_excution_time_rate = "{:.2f}".format(total_plan_excution_time_rate / num)
        whole_todo_achievement_rate = "{:.2f}".format((total_todo_achievement_time / total_expected_time) * 100)
        return average_plan_excution_time_rate, whole_todo_achievement_rate


