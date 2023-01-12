from django.urls import path
from . import views


# 1つのプロジェクトに複数のアプリケーションがあって，アプリで同じURLがある場合に指定する
app_name = 'todolist'


urlpatterns = [
    path('index/',                                      views.index,                        name='index'),
    path('home/',                                       views.HomeView.as_view(),           name='home'),
    path('tasks/',                                      views.TodoListView.as_view(),       name='todomodel_list'),
    path('tasks/<int:pk>/',                             views.TodoDetailView.as_view(),     name='todomodel_detail'), 
    path('tasks/new/',                                  views.TodoCreateView.as_view(),     name='todomodel_new'), 
    path('tasks/<int:pk>/edit/',                        views.TodoUpdateView.as_view(),     name='todomodel_edit'), 
    path('tasks/<int:pk>/confirm_delete/',              views.TodoDeleteView.as_view(),     name='todomodel_confirm_delete'), 
    
    path('workdates/',                                  views.WorkDateListView.as_view(),   name='workdatemodel_list'), 
    path('workdates/new/',                              views.WorkDateCreateView.as_view(), name='workdatemodel_new'), 
    path('workdates/<slug:slug>/',                      views.WorkDateDetailView.as_view(), name='workdatemodel_detail'), 
    path('workdates/<slug:slug>/edit/',                 views.WorkDateUpdateView.as_view(), name='workdatemodel_edit'), 
    path('workdates/<slug:slug>/confirm-delete/',       views.WorkDateDeleteView.as_view(), name='workdatemodel_delete'), 
    
    path('workdates/workmode/<slug:slug>/<int:order>/', views.WorkModeView.as_view(),       name='workmode'), 
    path('workdates/workmode/<slug:slug>/drop/',        views.WorkModeDropView.as_view(),   name='workmode_drop'), 
    
    path('analysis/',                                   views.AnalysisView.as_view(),       name='analysis'),
    ]