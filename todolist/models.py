from django.db import models
from django.utils import timezone


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
    
    work_date                       = models.DateField(verbose_name='作業日', unique=True, null=False, blank=False)
    is_finished                     = models.BooleanField(verbose_name='終了したかどうか', default=False)
    average_plan_excution_time_rate = models.FloatField(verbose_name='平均計画実行時間割合', default=0, blank=True)
    todo_achievement_rate_in_a_day  = models.FloatField(verbose_name='1日の進捗率', default=0, blank=True)
    slug                            = models.SlugField(verbose_name='スラッグ', unique=True, blank=True)
    create_at                       = models.DateTimeField(verbose_name='登録日時')
    update_at                       = models.DateTimeField(verbose_name='更新日時')
    
    
    def __str__(self):
        return str(self.work_date)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.create_at = timezone.now()
        self.update_at = timezone.now()
        
        if self.is_finished:
            self.set_average_petr()
            self.set_tar_in_a_day()
        else:
            self.average_plan_excution_time_rate = 0
            self.todo_achievement_rate_in_a_day = 0
        
        self.slug = str(self.work_date)
        if self.slug in ['today', ]:
            raise ValueError(
                '"%(slug_name)s" はスラッグ名として利用することができません。', 
                params={'slug_name': self.slug}
            )
        return super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        # Adminで一括削除した場合はこのメソッドは呼ばれない。
        todomodel_list = self.todomodel_list.all()
        if len(todomodel_list):
            for todomodel in todomodel_list:
                todomodel.order = 0
                todomodel.save()
        return super().delete(using=using, keep_parents=keep_parents)
    
    def set_average_petr(self):
        sum_ptr = 0
        todomodel_list = self.todomodel_list.all()
        for todomodel in todomodel_list:
            sum_ptr += todomodel.plan_excution_time_rate
            
        self.average_plan_excution_time_rate = "{:.2f}".format(sum_ptr / len(todomodel_list))
    
    def set_tar_in_a_day(self):
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
        return super().delete(using=using, keep_parents=keep_parents)
    
    def expected_time_min(self):
        return str(self.expected_time // 60)
    
    def actual_time_min(self):
        m = str(self.actual_time // 60)
        s = str(self.actual_time % 60).zfill(2)
        return m, s
    
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

