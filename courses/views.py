from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import DetailView
from django.core.urlresolvers import reverse_lazy
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.cache import cache
from braces.views import LoginRequiredMixin, PermissionRequiredMixin, CsrfExemptMixin, JsonRequestResponseMixin
from django.forms.models import modelform_factory
from django.apps import apps
from django.db.models import Count

from .models import Course, Module, Content, Subject
from .forms import ModuleFormSet
from students.forms import CourseEnrollForm

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
        self.course = get_object_or_404(Course, id=pk, owner=request.user)
        return super(CourseModuleUpdateView, self).dispatch(request, pk)


    """
    get() : Executed for GET requests. We build an empty ModuleFormSet
    formset and render it to the template together with the current
    Course object using the render_to_response() method provided by
    TemplateResponseMixin .
    """
    def get(self, request, *args, **kwargs):
        formset = self.get_formset()
        return self.render_to_response(
            {
                'course': self.course,
                'formset': formset
                })


    def post(self, request, *args, **kwargs):
        formset = self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('manage_course_list')
        return self.render_to_response(
            {
                'course': self.course,
                'formset': formset
                })


class ContentCreateUpdateView(TemplateResponseMixin, View):
    module = None
    model = None
    obj = None
    template_name = 'courses/manage/content/form.html'

    def get_model(self, model_name):
        if model_name in ['text', 'video', 'image', 'file']:
            return apps.get_model(app_label='courses', model_name=model_name)
        return None

    def get_form(self, model, *args, **kwargs):
        Form = modelform_factory(model, exclude=['owner', 'order', 'created', 'updated'])
        return Form(*args, **kwargs)

    def dispatch(self, request, module_id, model_name, id=None):
        self.module = get_object_or_404(Module, id=module_id, course__owner=request.user)
        self.model = self.get_model(model_name)
        if id:
            self.obj = get_object_or_404(self.model, id=id, owner=request.user)
        return super(ContentCreateUpdateView, self).dispatch(request, module_id, model_name, id)

    def get(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj)
        return self.render_to_response({
            'from':form,
            'object':self.obj,
            })


    def post(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model,
                            instance=self.obj,
                            data=request.POST,
                            files=request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            if not id:
                # new content
                Content.objects.create(module=self.module, item=obj)
                return redirect('module_content_list', self.module.id)

        return self.render_to_response({'form': form, 'object': self.obj})

"""
    The ContentDeleteView retrieves the Content object with the given id
    it deletes the related Text, Video, Image or File and finally it detetes
    the Content Object and redirects the user to the module_content_list URL
    to list other contents of the module__course__owner
"""
class ContentDeleteView(View):

    def post(self, request, id):
        content = get_object_or_404(Content, id=id, module__course__owner=request.user)
        module = content.module
        content.item.delete()
        content.delete()

        return redirect('module_content_list', module.id)


"""
    Display all Modules for a course and list contents for a specific
    module
"""

class ModuleContentListView(TemplateResponseMixin, View):
    template_name = "courses/manage/module/content_list.html"

    def get(self, request, module_id):
        module = get_object_or_404(Module,
                                   id=module_id,
                                   course__owner = request.user )

        return self.render_to_response({
            'module': module,
        })



class ModuleOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):
    def post(self, request):
        for id, order in self.request_json.items():
            Module.objects.filter(id=id, course__owner=request.user).update(order=order)
        return self.render_json_response({
            'saved': 'OK'
        })

class ContentOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):
    def post(self, request):
        for id, order in self.request_json.items():
            Content.objects.filter(id=id, course__owner=request.user).update(order=order)
        return self.render_json_response({
            'saved': 'OK'
        })


class CourseListView(TemplateResponseMixin, View):
    model = Course
    template_name = 'courses/course/list.html'

    def get(self, request, subject=None):
        """
        We retrieve all subjects, including the total number of courses for each of
        them. We use the ORM's annotate() method with the Count() aggregation
        function for doing so.
        """

        """
        Caching content
        First we try to get the all_students key from the cache using cache.
        get() . This returns None if the given key is not found. If no key is found (not cached
        yet, or cached but timed out) we perform the query to retrieve all Subject objects
        and their number of courses, and we cache the result using cache.set() .
        """
        subjects = cache.get('all_subjects')
        if not subjects:
            subjects = Subject.objects.annotate(
                        total_courses=Count('courses'))
            cache.set('all_subjects', subjects)

        all_courses = Course.objects.annotate(total_modules=Count('modules'))

        """"
        We retrieve all available courses, including the total number of modules
        contained in each course.
        3. If a subject slug URL parameter is given we retrieve the corresponding
        subject object and we limit the query to the courses that belong to the
        given subject.
        """

        if  subject:
            subject = get_object_or_404(Subject, slug=subject)
            key = 'subject_{}_courses'.format(subject.id)
            courses = cache.get(key)
            if not courses:
                courses = all_courses.filter(subject=subject)
                cache.set(key, courses)
        else:
            courses = cache.get('all_courses')
            if not courses:
                courses = all_courses
                cache.set('all_courses', courses)

        """
        We use the render_to_response() method provided by
        TemplateResponseMixin to render the objects to a template
        and return an HTTP response
        """

        return self.render_to_response({
                                            'subjects' : subjects,
                                            'subject' : subject,
                                            'courses' : courses,
                                        })

class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course/detail.html'

    def get_context_data(self, **kwargs):
        context = super(CourseDetailView, self).get_context_data(**kwargs)
        context['enroll_form'] = CourseEnrollForm(
            initial={'course':self.object})
        return context


class StudentCourseDetailView(DetailView):
    model= Course
    template_name = 'students/course/detail.html'

    def get_queryset(self):
        qs = super(StudentCourseDetailView, self).get_queryset()
        return qs.filter(students__in=[self.request.user])

    def get_context_data(self, **kwargs):
        context = super(StudentCourseDetailView, self).get_context_data(**kwargs)
        # get course object
        course = self.get_object()
        if 'module_id' in self.kwargs:
            # get current module
            context['module'] = course.modules.get(id=self.kwargs['module_id'])
        else:
            # get first module
            context['module'] = course.modules.all()[0]
        return context
