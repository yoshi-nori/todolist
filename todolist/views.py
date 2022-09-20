from django.shortcuts import render
from django.views import generic
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.utils.timezone import make_aware
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import TodoModel, WorkDateModel
from . import forms, myutils
from .mixins import extra_mixins, formset_mixin
from datetime import datetime
from urllib.parse import urlencode


"""
Temporary debug function in production environment.
Comment out this part if you don't use debug function
"""
from django.views.decorators.csrf import requires_csrf_token
from django.http import HttpResponseServerError

@requires_csrf_token
def my_customized_server_error(request, template_name='500.html'):
    import sys
    from django.views import debug
    error_html = debug.technical_500_response(request, *sys.exc_info()).content
    return HttpResponseServerError(error_html)
# End of debug function part


def index(request):
    template_name = 'todolist/index.html'
    return render(request, template_name)

@login_required
def home(request):
    template_name = 'todolist/home.html'
    return render(request, template_name)


class HomeView(LoginRequiredMixin, extra_mixins.WorkModeDialogMixin, generic.TemplateView):
    template_name = 'todolist/home.html'


class TodoListView(LoginRequiredMixin, extra_mixins.WorkModeDialogMixin, generic.ListView):
    model            = TodoModel
    allow_empty      = True
    paginate_by      = 15
    paginate_orphans = 3
    ordering         = 'limit_time'
    
    def get(self, request, *args, **kwargs):
        self.queryset = self.model.objects.filter(user=self.request.user.id).all()
        return super().get(request, *args, **kwargs)


class TodoDetailView(LoginRequiredMixin, extra_mixins.WorkModeDialogMixin, generic.DetailView):
    model = TodoModel
    
    def get(self, request, *args, **kwargs):
        self.queryset = self.model.objects.select_related('work_date_model').filter(user=self.request.user.id).all()
        return super().get(request, *args, **kwargs)


class TodoCreateView(LoginRequiredMixin, generic.CreateView):
    model       = TodoModel
    form_class  = forms.UnCompletedTodoModelForm
    success_url = reverse_lazy('todolist:todomodel_list')
    
    def form_valid(self, form):
        obj = form.instance
        obj.convert_form_values_min_to_sec(form)
        obj.user = self.request.user
        
        response = super().form_valid(form)
        messages.success(self.request, f'"{self.object.title}" の登録が完了しました。', extra_tags='todolist')
        return response
    
    def get(self, request, *args, **kwargs):
        self.queryset = self.model.objects.filter(user=self.request.user.id).all()
        return super().get(request, *args, **kwargs)


class TodoUpdateView(LoginRequiredMixin, generic.UpdateView):
    model                = TodoModel
    form_class           = forms.UnCompletedTodoModelForm
    completed_form_class = forms.CompletedTodoModelForm
    success_url = reverse_lazy('todolist:todomodel_list')
    
    def get_form_class(self):
        if self.object.achievement_rate != 0:
            self.form_class = self.completed_form_class
        return super().get_form_class()
    
    def form_valid(self, form):
        obj = form.instance
        obj.convert_form_values_min_to_sec(form)
        obj.user = self.request.user
        response = super().form_valid(form)
        
        if obj.work_date_model:
            obj.work_date_model.save()
        messages.success(self.request, f'"{self.object.title}" の更新が完了しました。', extra_tags='todolist')
        return response
    
    def get(self, request, *args, **kwargs):
        self.queryset = self.model.objects.filter(user=self.request.user.id).all()
        return super().get(request, *args, **kwargs)


class TodoDeleteView(LoginRequiredMixin, generic.DeleteView):
    model       = TodoModel
    success_url = reverse_lazy('todolist:todomodel_list')
    
    def get(self, request, *args, **kwargs):
        self.queryset = self.model.objects.select_related('work_date_model').filter(user=self.request.user.id).all()
        return super().get(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(self.request, f'"{self.object.title}" の削除が完了しました。', extra_tags='todolist')
        return response


class WorkDateListView(LoginRequiredMixin, extra_mixins.WorkModeDialogMixin, generic.ListView):
    # 現状維持かクラス変数userを使う方がいいのか分からないので、発行されるクエリを見て考える 
    model            = WorkDateModel
    allow_empty      = True
    paginate_by      = 20
    paginate_orphans = 5
    ordering         = 'work_date'
    
    def get(self, request, *args, **kwargs):
        self.queryset = self.workmode_queryset = self.model.objects.filter(user=self.request.user.id).all()
        
        # 現地時間の日付から作業データを取得する。
        self.object = self.queryset.filter(work_date=make_aware(datetime.today())).first()
        return super().get(request, *args, **kwargs)


class WorkDateDetailView(LoginRequiredMixin, extra_mixins.WorkModeDialogMixin, generic.DetailView):
    """
    Use "todolist/workmode_result.html" template file if query parameter 'result' is True.
    Get WorkDateModel whose work_date is today if received slug is 'today'.
    """
    model    = WorkDateModel
    submodel = TodoModel
    
    def get_object(self, queryset=None):
        try:
            obj = super().get_object(queryset)
        except Http404 as e:
            if self.kwargs.get('slug') == 'today':
                obj = self.queryset.filter(work_date=make_aware(datetime.today())).first()
            else:
                print(f'              self.model.DoesNotExist')
                raise Http404(e)
        return obj
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({
            'todomodel_list'   : self.object.todomodel_list.order_by('order').all() if self.object else None, 
        })
        if self.request.GET.get('result'):
            average_plan_excution_time_rate, whole_todo_achievement_rate = self.submodel.evaluate_total_todos(self.request.user)
            context.update({
                'average_plan_excution_time_rate' : average_plan_excution_time_rate, 
                'whole_todo_achievement_rate'      : whole_todo_achievement_rate, 
            })
        return context
    
    def get_template_names(self):
        if self.request.GET.get('result'):
            self.template_name = 'todolist/workmode_result.html'
        return super().get_template_names()
    
    def get(self, request, *args, **kwargs):
        self.queryset = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        return super().get(request, *args, **kwargs)


class WorkDateCreateView(LoginRequiredMixin, formset_mixin.OneToManyFormsView):
    model         = WorkDateModel
    form_class    = forms.WorkDateModelForm
    formset_model = TodoModel
    formset_class = forms.WorkDateTodoCustomFormSet
    success_url   = reverse_lazy('todolist:workdatemodel_list')
    form_ordering = 'order'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method == 'GET':
            kwargs['user'] = self.request.user
        return kwargs
    
    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        
        if not hasattr(self, 'todo_select_list'):
            self.todo_select_list = self.formset_queryset.filter(
                work_date_model      = None, 
                achievement_rate__lt = 100
            ).order_by(*('-update_at', )).all()
            
        kwargs['form_kwargs'] = {'queryset' : self.todo_select_list}
        return kwargs
    
    def all_form_valid(self, form, formset):
        form.instance.user = self.request.user
        self.object = form.save()
        self.object_list = []
        for i, subform in enumerate(formset, 1):
            todomodel = subform.cleaned_data['title']
            todomodel.apply_registered_form(i, subform, self.object)
            self.object_list.append(todomodel)
        
        response = super().all_form_valid(form=form, formset=self.object_list)
        messages.success(self.request, f'{self.object.work_date.strftime("%Y年%m月%d日")}の作業データの登録が完了しました。', extra_tags='todolist')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if not hasattr(self, 'todo_select_list'):
            self.todo_select_list = self.formset_queryset.filter(
                work_date_model      = None, 
                achievement_rate__lt = 100
            ).order_by(*('-update_at', )).all()
        
        # TODO : Ajaxでの処理に変更する
        context['todo_select_list'] = [
            myutils.convert_dict_key(myutils.todomodel_to_dict(obj, ['title', 'id', 'expected_time_min']), myutils.snake_to_camel) 
            for obj in self.todo_select_list
        ]
        return context
    
    def get(self, request, *args, **kwargs):
        self.queryset         = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        self.formset_queryset = self.formset_model.objects.filter(user=self.request.user.id).all()
        self.object           = None
        self.object_list      = self.formset_model.objects.none()
        
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.queryset         = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        self.formset_queryset = self.formset_model.objects.filter(user=self.request.user.id).all()
        self.object           = None
        self.object_list      = self.formset_model.objects.none()
        
        return super().post(request, *args, **kwargs)


class WorkDateUpdateView(LoginRequiredMixin, formset_mixin.OneToManyFormsView):
    model         = WorkDateModel
    form_class    = forms.WorkDateModelForm
    formset_model = TodoModel
    formset_class = forms.WorkDateTodoCustomFormSet
    success_url   = reverse_lazy('todolist:workdatemodel_list')
    form_ordering = 'order'
    
    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        if not hasattr(self, 'todo_select_list'):
            
            self.todo_select_list = self.formset_queryset.filter(
                Q(work_date_model=None, achievement_rate__lt=100) | Q(work_date_model=self.object)
            ).all()
        
        form_kwargs = {
            'queryset'    : self.todo_select_list, 
            'is_finished' : self.object.is_finished, 
            }
        kwargs['form_kwargs'] = form_kwargs
        return kwargs
    
    def all_form_valid(self, form, formset):
        # フォーム入力前の作業データに含まれるTodoModelを取得
        initial_todomodels = {obj.id : obj for obj in self.object.todomodel_list.all()}
        
        # ToDoの追加、更新処理
        object_list = []
        for i, subform in enumerate(formset, 1):
            todomodel = subform.cleaned_data['title']
            if todomodel.id in initial_todomodels.keys():
                initial_todomodels.pop(todomodel.id)
            
            todomodel.apply_registered_form(i, subform, self.object)
            object_list.append(todomodel)
        
        # 削除されたToDoの処理
        for removed_todomodel in initial_todomodels.values():
            removed_todomodel.apply_deleted_form()
            object_list.append(removed_todomodel)
        
        messages.success(self.request, f'{self.object.work_date.strftime("%Y年%m月%d日")}の作業データの更新が完了しました。', extra_tags='todolist')
        return super().all_form_valid(form=form, formset=object_list)
    
    def all_form_invalid(self, form, formset):
        return self.render_to_response(self.get_context_data(formset=formset))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if not hasattr(self, 'todo_select_list'):
            self.todo_select_list = self.formset_queryset.filter(
                Q(work_date_model=None, achievement_rate__lt=100) | Q(work_date_model=self.object)
            ).all()
        
        # クライアント側での一部フォーム自動入力のためのデータ
        # →TODO : Ajaxで通信を行う処理に変更する
        context['todo_select_list'] = [
            myutils.convert_dict_key(myutils.todomodel_to_dict(obj, ['title', 'id', 'expected_time_min']), myutils.snake_to_camel) 
            for obj in self.todo_select_list
        ]
        return context
    
    def get(self, request, *args, **kwargs):
        self.queryset         = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        self.formset_queryset = self.formset_model.objects.filter(user=self.request.user.id).all()
        self.object           = self.get_object()
        self.object_list      = self.get_object_list()
        
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.queryset         = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        self.formset_queryset = self.formset_model.objects.filter(user=self.request.user.id).all()
        self.object           = self.get_object()
        self.object_list      = self.get_object_list()
        
        return super().post(request, *args, **kwargs)


class WorkDateDeleteView(LoginRequiredMixin, generic.DeleteView):
    model       = WorkDateModel
    success_url = reverse_lazy('todolist:workdatemodel_list')
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['todomodel_list'] = self.object.todomodel_list.order_by('order').all()
        return context
    
    def get(self, request, *args, **kwargs):
        self.queryset = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        return super().get(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        self.queryset = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        
        response = super().delete(request, *args, **kwargs)
        messages.success(self.request, f'{self.object.work_date.strftime("%Y年%m月%d日")}の作業データの削除が完了しました。', extra_tags='todolist')
        return response


class WorkModeView(LoginRequiredMixin, generic.edit.UpdateView):
    model         = WorkDateModel
    form_class    = forms.WorkModeForm
    template_name = 'todolist/workmode.html'
    
    def get_object(self, queryset=None):
        try:
            obj = super().get_object(queryset)
        except Http404 as e:
            if self.kwargs.get('slug') == 'today':
                obj = self.queryset.filter(work_date=make_aware(datetime.today())).first()
            else:
                print(f'              self.model.DoesNotExist')
                raise Http404(e)
        return obj
    
    def get_todomodel_for_client(self):
        """"無い場合はNoneを返す"""
        return self.object.todomodel_list.filter(order=self.kwargs.get('order')).first()
    
    def get_form(self, form_class=None, form_to_client=False):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs(form_to_client=form_to_client))
        
    def get_form_kwargs(self, form_to_client=False):
        kwargs = {
            'initial' : self.get_initial(), 
            'prefix'  : self.get_prefix()
        }
        # self.request.method == 'POST' ではなく、form_to_clientで判定を行うのは、
        # 1度のPOSTリクエストの中で、受け取り用フォームと送信用フォームをどちらも作成する必要があるため。
        if not(form_to_client):
            instance = self.object.todomodel_list.filter(order=self.request.POST.get('order')).first()
            kwargs.update({
                'data'     : self.request.POST, 
                'files'    : self.request.FILES, 
                'instance' : instance
            })
        else:
            kwargs.update({'instance': self.todomodel_for_client})
        return kwargs
    
    def get_success_url(self):
        # Drop（中断）する場合
        if self.is_drop:
            return reverse('todolist:workmode_drop', kwargs={'slug' : self.object.slug})
        
        # Complete（その日の全てのToDoを完了）する場合
        elif self.kwargs.get('order') > len(self.object.todomodel_list.all()):
            url = reverse('todolist:workdatemodel_detail', kwargs={'slug' : self.object.slug}) + '?' + urlencode(dict(result=True))
            return url
        
        # Next（次のToDoへ進む）またはBack（前のToDoに戻る）する場合
        else:
            return reverse('todolist:workmode', kwargs={'slug' : self.object.slug, 'order' : self.todomodel_for_client.order})
    
    def get_context_data(self, *args, **kwargs):
        context = super(generic.edit.FormMixin, self).get_context_data(*args, **kwargs)
        
        extra_fields = {
            'expected_time_min'    : self.todomodel_for_client.expected_time_min(), 
            'actual_time_min'      : self.todomodel_for_client.actual_time_min(), 
            'next_order'           : self.todomodel_for_client.order + 1, 
            'back_order'           : self.todomodel_for_client.order - 1, 
            'todo_num_in_workdate' : len(self.object.todomodel_list.order_by('order').all()), 
        }
        todo_py = myutils.todomodel_to_dict(self.todomodel_for_client, '__all__', **extra_fields)
        todo_js = myutils.convert_dict_key(todo_py, myutils.snake_to_camel)
        context.update({
            'todo_py' : todo_py, 
            'todo_js' : todo_js, 
        })
        
        if 'form' not in kwargs:
            context['form'] = self.get_form(form_to_client=True)
        context.update(**kwargs)
        return context
    
    def form_valid(self, form):
        obj = form.save(commit=False)
        # Nextの場合
        if form.cleaned_data['order'] < self.kwargs.get('order'):
            self.is_drop = False
            obj.achievement_rate = 100
            
            # 最後のToDoを完了する場合はその日の作業モデルも更新して保存する。
            if form.cleaned_data['order'] == len(self.object.todomodel_list.all()):
                self.object.is_finished = True
                self.object.save()
        
        # Backの場合
        elif form.cleaned_data['order'] > self.kwargs.get('order'):
            self.is_drop = False
            back_obj = self.object.todomodel_list.filter(order=(obj.order - 1)).first()
            back_obj.achievement_rate = 0
            back_obj.save()
        
        # Dropの場合
        else:
            self.is_drop = True
        form.save()
        return super(generic.edit.ModelFormMixin, self).form_valid(form)
    
    def form_invalid(self, form):
        print(f'                        form_invalid() : {form.errors}')
        return super().form_invalid(form)
    
    def get(self, request, *args, **kwargs):
        self.queryset             = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        self.object               = self.get_object()
        self.todomodel_for_client = self.get_todomodel_for_client()
        
        return super(generic.edit.BaseUpdateView, self).get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.queryset             = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        self.object               = self.get_object(self.queryset.prefetch_related('todomodel_list').all())
        self.todomodel_for_client = self.get_todomodel_for_client()
        
        return super(generic.edit.BaseUpdateView, self).post(request, *args, **kwargs)


class WorkModeDropView(LoginRequiredMixin, generic.detail.SingleObjectTemplateResponseMixin, generic.detail.SingleObjectMixin,  formset_mixin.BaseUpdateMultipleView):
    model         = WorkDateModel
    formset_model = TodoModel
    formset_class = forms.WorkModeDropFormSet
    template_name = 'todolist/workmode_drop.html'
    
    def get_object_list(self):
        return self.object.todomodel_list.order_by('order').all()
    
    def get_success_url(self):
        return reverse_lazy('todolist:workdatemodel_detail', kwargs={'slug' : self.object.slug}) + '?' + urlencode(dict(result=True))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['todomodel_list'] = self.object_list
        return context
    
    def formset_valid(self, formset):
        for subform in formset:
            subform.instance.convert_form_value_min_to_sec(subform)
        response = super().formset_valid(formset)
        self.object.is_finished = True
        self.object.save()
        
        messages.success(self.request, '実行中の作業を中断しました。', extra_tags='todolist')
        return response
    
    def get(self, request, *args, **kwargs):
        self.queryset = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.queryset = self.model.objects.prefetch_related('todomodel_list').filter(user=self.request.user.id).all()
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)


