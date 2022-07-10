from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.views import generic
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.utils.timezone import make_aware
from django.http import Http404
from .models import TodoModel, WorkDateModel
from . import forms, myutils
from .mixins import extra_mixins
from todolist.mixins import formset_mixin
from datetime import datetime, timezone
from urllib.parse import urlencode


# """
# Temporary debug function in production environment.
# Comment out this part if you don't use debug function
# """
# from django.views.decorators.csrf import requires_csrf_token
# from django.http import HttpResponseServerError
#
# @requires_csrf_token
# def my_customized_server_error(request, template_name='500.html'):
#     import sys
#     from django.views import debug
#     error_html = debug.technical_500_response(request, *sys.exc_info()).content
#     return HttpResponseServerError(error_html)
# # End of debug function part


def test(request):
    return render(request, 'todolist/test.html')

def test2(request):
    return render(request, 'todolist/test2.html')

def test3(request):
    return render(request, 'todolist/test3.html')

def test4(request):
    return render(request, 'todolist/test4.html')

def index(request):
    template_name = 'todolist/index.html'
    return render(request, template_name)


class TodoListView(generic.ListView):
    model = TodoModel
    allow_empty = True
    paginate_by = 15
    paginate_orphans = 3
    ordering = 'limit_time'
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        qs = context['object_list']
        for obj in qs:
            # Djangoはdatetimeオブジェクトを基本的にUTCで扱う仕様になっている。
            # （テンプレートやフォームなどのエンドユーザーがやり取りする部分でのみ設定したタイムゾーンの時間となる）
            rest_time = obj.limit_time - datetime.now(timezone.utc) 
            obj.rest_time = rest_time
        return context


class TodoDetailView(generic.DetailView):
    model = TodoModel
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        return response


class TodoCreateView(extra_mixins.UnitExchangeMixin, generic.CreateView):
    model = TodoModel
    form_class = forms.UnCompletedTodoModelForm
    
    def get_success_url(self):
        messages.success(self.request, '登録完了しました。')
        return reverse('todolist:todomodel_list')
    
    def form_valid(self, form):
        obj = self.min_to_sec_in_form_fields(form.instance, form, 'expected_time')
        obj.limit_time = form.cleaned_data['limit_time']
        return super().form_valid(obj)


class TodoUpdateView(extra_mixins.UnitExchangeMixin, generic.UpdateView):
    model = TodoModel
    form_class = forms.UnCompletedTodoModelForm
    completed_form_class = forms.CompletedTodoModelForm
    
    def get_form_class(self):
        if self.object.achievement_rate != 0:
            self.form_class = self.completed_form_class
        return super().get_form_class()
    
    def get_success_url(self):
        messages.success(self.request, ('更新完了しました。'))
        return reverse('todolist:todomodel_list')
    
    def form_valid(self, form):
        field_names = [f for f in form.fields.keys() if f in ['expected_time', 'actual_time']]
        obj = self.min_to_sec_in_form_fields(form.instance, form, *field_names)
        response = super().form_valid(obj)
        
        if obj.work_date_model is not None:
            obj.work_date_model.save()
        return response


class TodoDeleteView(generic.DeleteView):
    model = TodoModel
    success_url = reverse_lazy('todolist:todomodel_list')
    
    def get_success_url(self):
        messages.success(self.request, ('削除完了しました。'))
        return super().get_success_url()
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        # 作業モデルのToDo実行順序を修正する
        if self.object.work_date_model is not None:
            todomodel_list = self.object.work_date_model.todomodel_list.all().order_by('order').all()
            for todomodel in todomodel_list[self.object.order:]:
                todomodel.order -= 1
                todomodel.save()
        
        self.object.delete()
        return HttpResponseRedirect(success_url)


class WorkDateListView(extra_mixins.DialogMixin, generic.ListView):
    model = WorkDateModel
    allow_empty = True
    paginate_by = 20
    paginate_orphans = 5
    ordering = 'work_date'
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        # 現地時間の日付から作業データを取得する。
        context.update({
            'workmode_info' : self.workmode_check(), 
            'today_model'   : self.model.objects.filter(work_date=make_aware(datetime.today())).first(),
        })
        return context
    
    def get(self, request, *args, **kwargs):
        # 現地時間の日付から作業データを取得する。
        self.object = self.model.objects.filter(work_date=make_aware(datetime.today())).first()
        return super().get(request, *args, **kwargs)


class WorkDateDetailView(extra_mixins.DialogMixin, generic.DetailView):
    """
    Use "todolist/workmode_result.html" template file if query parameter 'result' is True.
    Get WorkDateModel whose work_date is today if received slug is 'today'.
    """
    model = WorkDateModel
    submodel = TodoModel
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({
            'todomodel_list'   : self.object.todomodel_list.order_by('order').all() if self.object else None, 
            'workmode_info'    : self.workmode_check(), 
        })
        if self.request.GET.get('result'):
            average_plan_excution_time_rate, whole_todo_achievement_rate = self.get_whole_evaluation_indicators()
            context.update({
                'average_plan_excution_time_rate' : average_plan_excution_time_rate, 
                'whole_todo_achievement_rate'      : whole_todo_achievement_rate, 
            })
        return context
    
    def get_object(self, queryset=None):
        try:
            obj = super().get_object(queryset)
        except Http404 as e:
            if self.kwargs.get('slug') == 'today':
                obj = self.model.objects.prefetch_related('todomodel_list').filter(work_date=make_aware(datetime.today())).first()
            else:
                print(f'              self.model.DoesNotExist')
                raise Http404(e)
        return obj
    
    def get_template_names(self):
        if self.request.GET.get('result'):
            self.template_name = 'todolist/workmode_result.html'
        return super().get_template_names()
    
    def get_whole_evaluation_indicators(self):
        """これまでの実行した全てのToDoをDBから取得し、平均計画実行時間割合とToDo達成割合を計算して返す"""
        queryset = self.submodel.objects.exclude(achievement_rate=0).all()
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


class WorkDateCreateView(extra_mixins.UnitExchangeMixin, formset_mixin.OneToManyFormsView):
    model = WorkDateModel
    form_class = forms.WorkDateModelForm
    formset_model = TodoModel
    formset_class = forms.WorkDateTodoCustomFormSet
    success_url = reverse_lazy('todolist:workdatemodel_list')
    
    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset = queryset.prefetch_related('todomodel_list').all()
        return super().get_object(queryset)
    
    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        if not hasattr(self, 'todo_select_list'):
            self.todo_select_list = self.formset_model.objects.filter(work_date_model=None, achievement_rate__lt=100).order_by(*('-update_at', )).all()
        form_kwargs = {'queryset' : self.todo_select_list}
        kwargs['form_kwargs'] = form_kwargs
        return kwargs
    
    def get_success_url(self):
        messages.success(self.request, '登録が完了しました。')
        return super().get_success_url()
    
    def all_form_valid(self, form, formset):
    
        self.object = form.save()
        discount = 0
        self.object_list = []
        for i, subform in enumerate(formset):
            cleaned_data = subform.cleaned_data
            if len(cleaned_data) == 0 or (todomodel := cleaned_data['title']) is None:
                discount += 1
                continue
            # subform.instanceが空っぽなのは、CreateはinstanceがNoneだからopts.model()でインスタンス化された空っぽのモデルしか入っていない！
            
            todomodel.work_date_model = self.object
            todomodel.order = i + 1 - discount
            todomodel = self.min_to_sec_in_form_fields(todomodel, subform, 'expected_time')
            
            self.object_list.append(todomodel)
    
        return super().all_form_valid(form=form, formset=self.object_list)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if not hasattr(self, 'todo_select_list'):
            self.todo_select_list = self.formset_model.objects.filter(work_date_model=None, achievement_rate__lt=100).order_by(*('-update_at', )).all()
        
        todo_select_list_filtered = []
        for todomodel in self.todo_select_list:
            todo_select_list_filtered.append(
                myutils.convert_dict_key(
                    myutils.todomodel_to_dict(todomodel, ['title', 'id', 'expected_time_min']), myutils.snake_to_camel)
            )
        context['todo_select_list'] = todo_select_list_filtered
        return context
    
    def get(self, request, *args, **kwargs):
        self.object = None
        self.object_list = self.formset_model.objects.none()
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.object = None
        self.object_list = self.formset_model.objects.none()
        
        form = self.get_form()
        formset = self.get_formset()
        if form.is_valid() and formset.is_valid():
            return self.all_form_valid(form, formset)
        else:
            return self.all_form_invalid(form, formset)


class WorkDateUpdateView(extra_mixins.UnitExchangeMixin, formset_mixin.OneToManyFormsView):
    model = WorkDateModel
    form_class = forms.WorkDateModelForm
    formset_model = TodoModel
    formset_class = forms.WorkDateTodoCustomFormSet
    success_url = reverse_lazy('todolist:workdatemodel_list')
    
    
    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset = queryset.prefetch_related('todomodel_list').all()
        return super().get_object(queryset)
    
    def get_object_list(self):
        if self.object is None:
            self.object = self.get_object()
        object_list = self.object.todomodel_list.order_by('order').all()
        return object_list
    
    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        if not hasattr(self, 'todo_select_list'):
            self.todo_select_list = self.formset_model.objects.filter(Q(work_date_model=None, achievement_rate__lt=100) | Q(work_date_model=self.object)).all()
        form_kwargs = {
            'queryset'    : self.todo_select_list, 
            'is_finished' : self.object.is_finished, 
            }
        kwargs['form_kwargs'] = form_kwargs
        return kwargs
    
    def get_success_url(self):
        messages.success(self.request, '更新が完了しました。')
        return super().get_success_url()
    
    def all_form_valid(self, form, formset):
        # フォーム入力前の作業データに含まれるTodoModelを取得
        initial_todo_id_set = set(todomodel.id for todomodel in self.object.todomodel_list.all())
        
        # ToDoの追加、更新処理
        object_list = []
        discount = 0
        for i, subform in enumerate(formset):
            cleaned_data = subform.cleaned_data
            
            # フォームが空である場合またはフォームのToDoが選択されていない場合にそれを除く
            if len(cleaned_data) == 0 or (todomodel := cleaned_data['title']) is None:
                discount += 1
                continue
            
            if todomodel.id in initial_todo_id_set:
                initial_todo_id_set.discard(todomodel.id)
            
            todomodel.work_date_model = self.object
            todomodel.order = i + 1 - discount
            
            field_names = [f for f in subform.fields.keys() if f in ['expected_time', 'actual_time']]
            todomodel = self.min_to_sec_in_form_fields(todomodel, subform, *field_names)
            if 'achievement_rate' in subform.fields:
                todomodel.achievement_rate = cleaned_data['achievement_rate']
            object_list.append(todomodel)
        
        # 削除されたToDoの処理
        for qs_id in initial_todo_id_set:
            todomodel = self.formset_model.objects.get(id=qs_id)
            todomodel.work_date_model = None
            todomodel.order = 0
            object_list.append(todomodel)
        return super().all_form_valid(form=form, formset=object_list)
    
    def all_form_invalid(self, form, formset):
        return self.render_to_response(self.get_context_data(formset=formset))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if not hasattr(self, 'todo_select_list'):
            self.todo_select_list = self.formset_model.objects.filter(Q(work_date_model=None, achievement_rate__lt=100) | Q(work_date_model=self.object)).all()
        field_names = ['title', 'id', 'expected_time_min']
        context['todo_select_list'] = [
            myutils.convert_dict_key(myutils.todomodel_to_dict(obj, field_names), myutils.snake_to_camel) 
            for obj in self.todo_select_list
        ]
        return context
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object_list = self.get_object_list()
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object_list = self.get_object_list()
        
        form = self.get_form()
        formset = self.get_formset()
        if formset.is_valid():
            return self.all_form_valid(form, formset)
        else:
            return self.all_form_invalid(form, formset)


class WorkDateDeleteView(generic.DeleteView):
    model = WorkDateModel
    success_url = reverse_lazy('todolist:workdatemodel_list')
    
    def get_success_url(self):
        messages.success(self.request, f'{self.object}の作業データを削除しました。')
        return super().get_success_url()
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        todomodel_list = self.object.todomodel_list.order_by('order').all()
        context['todomodel_list'] = todomodel_list
        return context
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        todomodel_list = self.object.todomodel_list.all()
        for todo in todomodel_list:
            todo.order = 0
            todo.save()
        
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())


class WorkModeView(generic.edit.UpdateView):
    model = WorkDateModel
    form_class = forms.WorkModeForm
    template_name = 'todolist/workmode.html'
    
    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset = queryset.prefetch_related('todomodel_list').all()
        return super().get_object(queryset)
    
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
            'prefix' : self.get_prefix()
        }
        # クライアントからPOST/PUTされて受け取るフォームの場合
        if not(form_to_client):
            instance = self.object.todomodel_list.filter(order=self.request.POST.get('order')).first()
            kwargs.update({
                'data'  : self.request.POST, 
                'files' : self.request.FILES, 
                'instance' : instance
            })
        # サーバーがフォーム入力のためにクライアントに送るフォームの場合
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
        
        # Next（次のToDoへ進む）場合
        else:
            return reverse('todolist:workmode', kwargs={'slug' : self.object.slug, 'order' : self.todomodel_for_client.order})
    
    def get_context_data(self, *args, **kwargs):
        context = super(generic.edit.FormMixin, self).get_context_data(*args, **kwargs)
        
        extra_fields = {
            'expeted_time_min'     : self.todomodel_for_client.expected_time_min(), 
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
        # 最後のToDoを完了する場合はその日の作業モデルも更新して保存する。
        if form.cleaned_data['order'] == len(obj.work_date_model.todomodel_list.all()):
            self.object.is_finished = True
            self.object.save()
        return super(generic.edit.ModelFormMixin, self).form_valid(form)
    
    def form_invalid(self, form):
        print(f'                        form_invalid() : {form.errors}')
        return super().form_invalid(form)
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.todomodel_for_client = self.get_todomodel_for_client()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.todomodel_for_client = self.get_todomodel_for_client()
        return super(generic.edit.BaseUpdateView, self).post(request, *args, **kwargs)


class WorkModeDropView(generic.detail.SingleObjectTemplateResponseMixin, generic.detail.SingleObjectMixin,  formset_mixin.BaseUpdateMultipleView):
    model = WorkDateModel
    formset_model = TodoModel
    formset_class = forms.WorkModeDropFormSet
    template_name = 'todolist/workmode_drop.html'
    
    
    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset = queryset.prefetch_related('todomodel_list').all()
        return super().get_object(queryset)
    
    def get_object_list(self):
        if self.object is None:
            self.object = self.get_object()
        object_list = self.object.todomodel_list.order_by('order').all()
        return object_list
    
    def get_success_url(self):
        messages.success(self.request, '作業を中断しました。')
        return reverse('todolist:workdatemodel_detail', kwargs={'slug' : self.object.slug}) + '?' + urlencode(dict(result=True))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'todomodel_list' : self.object_list})
        return context
    
    def formset_valid(self, formset):
        response = super().formset_valid(formset)
        self.object.is_finished = True
        self.object.save()
        return response
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)








