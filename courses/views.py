from django.shortcuts import render, get_object_or_404
from django.views.generic.base import TemplateResponseMixin, View
from django.core.urlresolvers import reverse_lazy
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from braces.views import LoginRequiredMixin, PermissionRequiredMixin

from .models import Course
from .forms import ModuleFormSet




# create mixins first


class OwnerMixin(object):
    # overrid query_set to retrieve only content made by the user
    def get_queryset(self):
        qs = super(OwnerMixin, self).get_queryset()
        return qs.filter(owner=self.request.user)


class OwnerEditMixin(object):
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super(OwnerEditMixin, self).form_valid(form)


class OwnerCourseMixin(OwnerMixin, LoginRequiredMixin):
    model = Course
    fields = ['subject', 'title', 'slug', 'overview']
    success_url = reverse_lazy('manage_course_list')


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerEditMixin):
    fields = ['subject', 'title', 'slug', 'overview']
    success_url = reverse_lazy('manage_course_list')
    template_name = 'courses/manage/course/form.html'

# Create your views here.


class ManageCourseListView(OwnerCourseMixin, ListView):
    template_name = 'courses/manage/course/list.html'


class CourseCreateView(PermissionRequiredMixin, OwnerCourseEditMixin, CreateView):
    permission_required = 'courses.add_course'


class CourseUpdateView(PermissionRequiredMixin, OwnerCourseEditMixin, UpdateView):
    permission_required = 'courses.change_course'


class CourseDeleteView(OwnerCourseMixin, DeleteView):
    template_name = 'courses/manage/course/delete.html'
    success_url = reverse_lazy('manage_course_list')
    permission_required = 'courses.delete_course'

# add/update/delete Modules for a specific Course


class CourseModuleUpdateView(TemplateResponseMixin, View):
    template_name = 'courses/manage/module/formset.html'
    course = None

    # define get_formset to avoid repeating the code to build the formset
    def get_formset(self, data=None):
        # return the ModuleFormSet object for the given course object with optional data
        return ModuleFormSet(instance=self.course, data=data)

    """
    dispatch() : This method is provided by the View class. It takes an HTTP
    request and its parameters and attempts to delegate to a lowercase method
    that matches the HTTP method used: A GET request is delegated to the
    get() method and a POST request to post() respectively. In this method,
    we use the get_object_or_404() shortcut function to get the Course object
    for the given id parameter that belongs to the current user. We include this
    code in the dispatch() method because we need to retrieve the course for
    both GET and POST requests. We save it into the course attribute of the
    view to make it accessible to other methods.
    """
    def dispatch(self, request, pk):
        self.cource = get_object_or_404(Course, id=pk, owner=request.user)
        return super(CourseModuleUpdateView, self).dispatch(request, pk)


    """
    get() : Executed for GET requests. We build an empty ModuleFormSet
    formset and render it to the template together with the current
    Course object using the render_to_response() method provided by
    TemplateResponseMixin .
    """
    def get(self, request, *args, **kwargs):
        formset = self.get_formset()
        return self.render_to_response({
            'course': self.course,
            'formset': formset,
        })


    def post(self, request, *args, **kwargs):
        formset = self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('manage_course_list')
        return self.render_to_response({
            'course': self.course,
            'formset': formset,
        })
