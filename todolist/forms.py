from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import make_aware
from datetime import datetime
import math
from . import models


class UnCompletedTodoModelForm(forms.ModelForm):
    """作成フォームまたは未完了のToDoの更新フォームに用いる"""
    
    limit_time = forms.SplitDateTimeField(label='期限', widget=forms.widgets.SplitDateTimeWidget)
    
    class Meta():
        model = models.TodoModel
        fields = ('title', 'limit_time', 'expected_time', )
        labels = {
            'expected_time' : '目標時間（分）',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['expected_time'] = math.ceil(self.instance.expected_time / 60)
    
    def clean_limit_time(self):
        limit_time = self.cleaned_data.get('limit_time')
        
        # 現在の日時を超えていればエラー
        now = make_aware(datetime.now())
        if now >= limit_time:
            raise forms.ValidationError('期限は現在時刻よりも後の日時に設定してください。')
        return limit_time


class CompletedTodoModelForm(forms.ModelForm):
    """完了済みのToDoモデルの更新フォームに用いる"""
    
    class Meta():
        model = models.TodoModel
        fields = ('title', 'expected_time', 'actual_time', 'achievement_rate', )
        labels = {
            'expected_time'         : '目標時間（分）',
            'actual_time'           : '実際の時間（分）', 
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['actual_time'] = math.ceil(self.instance.actual_time / 60)
        
        if self.instance.expected_time == 0:
            self.fields['expected_time'].required = True
        else:
            self.fields['expected_time'].widget.attrs['readonly'] = True
    
    def clean_achievement_rate(self):
        achievement_rate = self.cleaned_data.get('achievement_rate')
        
        # 達成率が0から100の範囲に入っていなければエラー
        if not (0 <= achievement_rate <= 100):
            raise forms.ValidationError('ToDo達成割合は 0 ～ 100 の範囲に設定してください')
        return achievement_rate


class WorkDateModelForm(forms.ModelForm):
    
    class Meta:
        model = models.WorkDateModel
        fields = ('work_date', 'user')
        widgets = {
            'user' : forms.HiddenInput()
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.initial['user'] = user
        
        if self.initial.get('work_date'):
            # Updateの場合に初期値のフォーマットをJS側に合わせる→datedropperの初期値を設定するため。
            self.initial['work_date'] = datetime.strftime(self.initial['work_date'], '%m/%d/%Y')
        else:
            # Createの場合に今日のDateのフォーマットをJS側に合わせて設定
            self.initial['work_date'] = datetime.strftime(make_aware(datetime.today()), '%m/%d/%Y')
        
        if self.initial.get('work_date') and self.instance.is_finished:
            self.fields['work_date'].widget.attrs['readonly'] = True


class WorkDateTodoForm(forms.ModelForm):
    
    title = forms.ModelChoiceField(label='ToDo', widget=forms.Select(attrs={'class': 'form-title'}), queryset=models.TodoModel.objects.none(), required=False)
    field_order = ('title', 'expected_time', 'actual_time', 'achievement_rate', )
    
    class Meta:
        model = models.TodoModel
        fields = ('expected_time', 'actual_time', 'achievement_rate', )
        labels = {
            'expected_time'         : '目標時間（分）',
            'actual_time'           : '実際の時間（分）', 
        }
        widgets = {
            'expected_time'    : forms.NumberInput(attrs={'class' : 'form-expected_time', 'readonly' : True}), 
        }
    
    def __init__(self, queryset=None, is_finished=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['expected_time'] = math.ceil(self.instance.expected_time / 60)
        self.initial['actual_time'] = math.ceil(self.instance.actual_time / 60)
        if queryset:
            self.fields['title'].queryset = queryset
        if 'instance' in kwargs:
            self.fields['title'].initial = kwargs['instance']
        
        if not is_finished:
            self.fields['expected_time'].widget.attrs['readonly'] = False
            self.fields.pop('actual_time')
            self.fields.pop('achievement_rate')
        else:
            self.fields['title'].widget = forms.HiddenInput()
    
    def clean_achievement_rate(self):
        achievement_rate = self.cleaned_data.get('achievement_rate')
        
        # 達成率が0から100の範囲に入っていなければエラー
        if not (0 <= achievement_rate <= 100):
            raise forms.ValidationError('ToDo達成割合は 0 ～ 100 の範囲に設定してください')
        return achievement_rate


class CustomFormSet(forms.BaseModelFormSet):
    
    def _construct_form(self, i , **kwargs):
        form = super()._construct_form(i, **kwargs)
        form.fields[self.model._meta.pk.name].required = False
        return form
    
    def total_form_count(self):
        if max(self.initial_form_count(), self.min_num) == 0:
            self.extra = 1
        else:
            self.extra = 0
        return super().total_form_count()
    
    def clean(self):
        cleaned_data_list = [data for data in self.cleaned_data]
        st = set()
        for cleaned_data in cleaned_data_list:
            if len(cleaned_data) == 0:
                raise forms.ValidationError('空のフォームが存在します。フォームを埋めてください。')
            # if 'title' not in cleaned_data:
            #     continue
            if cleaned_data['title'] is None:
                raise forms.ValidationError('"ToDo"が選択されていないフォームが存在します。フォームを埋めてください。')
            
            todomodel = cleaned_data['title']
            if todomodel in st:
                raise forms.ValidationError(
                    _('同じToDoが複数選択されています。: %(model)s'), 
                    params={'model' : todomodel.title}
                )
            else:
                st.add(todomodel)
        return self.cleaned_data


WorkDateTodoCustomFormSet = forms.modelformset_factory(
    models.TodoModel, form=WorkDateTodoForm, formset=CustomFormSet, 
    )


class WorkModeForm(forms.ModelForm):
    
    class Meta:
        model = models.TodoModel
        fields = ('order', 'actual_time')
    
    def __init__(self, *args,**kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget = forms.HiddenInput()


class WorkModeDropForm(forms.ModelForm):
    
    class Meta:
        model = models.TodoModel
        fields = ('achievement_rate', 'actual_time')
        labels = {
            'actual_time' : '実際の時間（分）'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['actual_time'] = math.ceil(self.instance.actual_time / 60)



WorkModeDropFormSet = forms.modelformset_factory(
    models.TodoModel, form=WorkModeDropForm, extra=0
)