from django import template
from django.views import generic
from todolist import views
import datetime

register = template.Library()

@register.filter(expects_localtime=True)
def is_today(value):
    if type(value) is datetime.datetime:
        value = value.date()
    return value == datetime.date.today()

@register.filter()
def is_update_view(value):
    if isinstance(value, views.WorkDateUpdateView) or isinstance(value, generic.UpdateView):
        return True
    elif isinstance(value, views.WorkDateCreateView) or isinstance(value, generic.CreateView):
        return False
    else:
        raise ValueError('Invalid View')

cud_view = (
    views.TodoCreateView, 
    views.TodoUpdateView, 
    views.TodoDeleteView, 
    views.WorkDateCreateView, 
    views.WorkDateUpdateView, 
    views.WorkDateDeleteView, 
    views.WorkModeDropView
)

@register.filter()
def is_cud_view(value):
    if value.__class__ in cud_view:
        return True
    else:
        return False