from django.core.exceptions import ImproperlyConfigured
from django.forms import models as model_forms
from django.http import HttpResponseRedirect
from django.views import generic
from django.db import models


class FormSetMixin(generic.base.ContextMixin):
    initial = {}
    formset_class = None
    success_url = None
    prefix = None
    
    def get_initial(self):
        """Provide a way to show and handle a form in a request."""
        return self.initial.copy()
    
    def get_prefix(self):
        """Return the prefix to use for forms."""
        return self.prefix
    
    def get_formset_class(self):
        """Return the formset class to use."""
        return self.formset_class
    
    def get_formset(self, formset_class=None):
        """Return an instance of the formset to be used in this view."""
        if formset_class is None:
            formset_class = self.get_formset_class()
        return formset_class(**self.get_formset_kwargs())
    
    def get_formset_kwargs(self):
        """Return the keyword arguments for instantiating the formset."""
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }

        if self.request.method in ('POST', 'PUT'):
            # POSTとFILESに分かれているのは、通信プロトコルが違うから？
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES, 
            })
        return kwargs

    def get_success_url(self):
        """Return the URL to redirect to after processing a valid formset."""
        if not self.success_url:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")
        return str(self.success_url)  # success_url may be lazy

    def formset_valid(self, formset):
        """If the formset is valid, redirect to the supplied URL."""
        return HttpResponseRedirect(self.get_success_url())

    def formset_invalid(self, formset):
        """If the formset is invalid, render the invalid form."""
        return self.render_to_response(self.get_context_data(formset=formset))

    def get_context_data(self, **kwargs):
        """Insert the formset into the context dict."""
        if 'formset' not in kwargs:
            kwargs['formset'] = self.get_formset()
        return super().get_context_data(**kwargs)


class ModelFormSetMixin(FormSetMixin):
    formset_model = None
    formset_fields = None
    formset_queryset = None
    
    def get_formset_class(self):
        """
        FormSetクラスを取得する方法
        ①  formset_classを指定する
            →独自にカスタムしたFormSetクラスを使用できるが作成の手間がかかる
        
        ②  formset_modelとformset_fieldsを指定する
            使用したいモデルとそのフィールド名から自動でmodelformクラス（を基底クラスとした新しいクラス）
            とmodelformsetクラス（を基底クラスとした新しいクラス）を動的作成する
            →フォームを作成しなくても勝手に作成してくれるがカスタマイズ性が低い
        """
        if self.formset_fields is not None and self.formset_class:
            raise ImproperlyConfigured(
                "Specifying both 'fields' and 'form_class' is not permitted."
            )
        if self.formset_class:
            return self.formset_class
        else:
            if self.formset_model is not None:
                formset_model = self.formset_model
                
            else:
                raise ImproperlyConfigured(
                    "Using ModelFormSetMixin (base class of %s) without "
                    "the 'formset_model' attribute is prohibited." % self.__class__.__name__
                )
        
            if self.formset_fields is None:
                raise ImproperlyConfigured(
                    "Using ModelFormSetMixin (base class of %s) without "
                    "the 'formset_fields' attribute is prohibited." % self.__class__.__name__
                )
        return model_forms.modelformset_factory(model=formset_model, fields=self.formset_fields)
    
    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        if hasattr(self, 'object_list'):
            # FormSetクラスのquerysetはフォームの初期状態の取得に用いられる
            kwargs['queryset'] = self.object_list
        return kwargs
    
    def get_object_list(self, queryset=None):
        """
        ※オーバーライド必須
        このメソッドをオーバーライドしてUpdateする際のモデルのリストの取得を記述する。
        """
        if queryset is None:
            if self.formset_queryset is None:
                if getattr(self, 'formset_model', None):
                    queryset = self.formset_model.objects.all()
                else:
                    raise ImproperlyConfigured(
                        "%(cls)s is missing a QuerySet. Define "
                        "%(cls)s.formset_model, %(cls)s.formset_queryset, "
                        "or override %(cls)s.get_formset_queryset()." % {
                            'cls' : self.__class__.__name__
                        }
                    )
            else:
                queryset = self.formset_queryset
        return queryset
    
    def formset_valid(self, formset):
        self.object_list = []
        for form in formset:
            obj = form.save()
            self.object_list.append(obj)
        return HttpResponseRedirect(self.get_success_url())


class ProcessFormSetView(generic.base.View):
    
    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())
    
    def post(self, request, *args, **kwargs):
        
        formset = self.get_formset()
        if formset.is_valid():
            return self.formset_valid(formset)
        else:
            return self.formset_invalid(formset)
    
    def put(self, *args, **kwargs):
        return self.post(*args, **kwargs)


class BaseCreateMultipleView(ModelFormSetMixin, ProcessFormSetView):
    
    def get(self, request, *args, **kwargs):
        self.object_list = self.formset_model.objects.none()
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.object_list = self.formset_model.objects.none()
        return super().post(request, *args, **kwargs)


class BaseUpdateMultipleView(ModelFormSetMixin, ProcessFormSetView):
    
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_object_list()
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.object_list = self.get_object_list()
        return super().post(request, *args, **kwargs)


class OneToManyFormsMixin(ModelFormSetMixin, generic.edit.ModelFormMixin):
    """
    1対多の関係にある2つのモデルを同時に更新するためのフォームMixin
    FormとFormSetを利用する。
    """
    form_ordering = None;
    
    def get_object_list(self, parent_object=None):
        if parent_object is None:
            parent_object = self.get_object()
        
        for field in self.model._meta.get_fields():
            if isinstance(field, models.ManyToOneRel):
                related_name = field.related_name
                break
        queryset = getattr(parent_object, related_name).all()
        
        if self.form_ordering:
            queryset = queryset.order_by(self.form_ordering).all()
        return queryset
    
    def all_form_valid(self, form, formset):
        for subform in formset:
            subform.save()
        if form is not None:
            form.save()
        else:
            self.object.save()
        return HttpResponseRedirect(self.get_success_url())
    
    def all_form_invalid(self, form, formset):
        return self.render_to_response(self.get_context_data(form=form, formset=formset))
    
    def get_context_data(self, **kwargs):
        if 'form' not in kwargs:
            kwargs['form'] = self.get_form()
        return super().get_context_data(**kwargs)


class OneToManyFormsView(generic.edit.SingleObjectTemplateResponseMixin, OneToManyFormsMixin, ProcessFormSetView):
    """
    1対多の関係にある2つのモデルを扱うビュークラス。
    ユーザーはフォームに値を入力することで、「多」モデルのインスタンスの値を変更する。
    「多」モデルのインスタンスの値の変更に応じて、「1」モデルのインスタンスの値を変更する。
    """
    template_name_suffix = '_form'
    
    
    def post(self, request, *args, **kwargs):
        
        form = self.get_form()
        formset = self.get_formset()
        if form.is_valid() and formset.is_valid():
            return self.all_form_valid(form, formset)
        else:
            return self.all_form_invalid(form, formset)

