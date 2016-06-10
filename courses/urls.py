from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^mine/$', views.ManageCourseListView.as_view(),
        name='manage_course_list'),
    url(r'^create/$', views.CourseCreateView.as_view(), name='course_create'),
    url(r'^(?P<pk>\d+)/edit/$', views.CourseUpdateView.as_view(),
        name='course_edit'),
    url(r'^(?P<pk>\d+)/delete/$', views.CourseDeleteView.as_view(),
        name='course_delete'),
]
