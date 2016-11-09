from django.conf.urls import url

from . import views


urlpatterns = [
        url(r'^subjects/$',views.SubjectListView.as_view(),
            name='subject_list'),

        url(r'^subjects/(?P<pk>\d+)/$',views.SubjectDetailView.as_view(),
            name='subject_detail'),
        url(r'^courses/(?P<pk>\d+)/enroll/$',views.CourseEnrollView.as_view(),
            name='course_enroll'),
]
