import jinja2
import os

from datetime import datetime as dt
from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import admin_required

from models import Course,Instructor
from src.handler.base_handler import BaseHandler
from src.helpers.helpers import get_active_course
from src.models.assignment import AssignmentModel
from src.models.course import CourseModel
from src.models.eval import EvalModel
from src.models.instructor import InstructorModel
from src.models.message import MessageModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class ActivateCourse(BaseHandler):

#@admin_required
    def get(self):
        course  = ndb.Key(urlsafe=self.request.get('key')).get()
        course  = CourseModel.update_active_status(course, True)
        message = MessageModel.activated_course(course.abbr_name)
        return self.redirect('/admin/courses/view?message=' + message)            


class AddCourse(BaseHandler):

#@admin_required
    def get(self):
        user       = users.get_current_user()                                        
        instructor = InstructorModel.get_instructor_by_email(user.email())
        courses    = CourseModel.get_courses_by_instructor(instructor)
        
        # grab message from URL, if it exists
        message = self.request.get('message')                                

        template_values = {                                                    
            'message':  message,
            'user':     user,
            'sign_out': users.create_logout_url('/'),
            'courses':  courses,
            'quarters': {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'},
            'year':     dt.now().year,
        }

        template = JINJA_ENV.get_template('/templates/admin_add_course.html')
        return self.response.write(template.render(template_values))        

#@admin_required
    def post(self):
        user       = users.get_current_user()                                        
        instructor = InstructorModel.get_instructor_by_email(user.email())
        
        year      = int(self.request.get('year'))
        quarter   = int(self.request.get('quarter'))
        name      = self.request.get('name')
        abbr_name = self.request.get('abbr_name')
        course    = CourseModel.create_course(quarter, year, name, abbr_name, instructor)

        message = MessageModel.course_added(abbr_name)
        return self.redirect('/admin/courses/view?message=' + message)            


class DeactivateCourse(BaseHandler):

#@admin_required
    def get(self):
        course  = ndb.Key(urlsafe=self.request.get('key')).get()
        course  = CourseModel.update_active_status(course, False)
        message = MessageModel.deactivated_course(course.abbr_name)
        return self.redirect('/admin/courses/view?message=' + message)            


class ViewCourses(BaseHandler):

#@admin_required
    def get(self):
        user         = users.get_current_user()                                        
        instructor   = InstructorModel.get_instructor_by_email(user.email())
        edit_courses = CourseModel.get_all_courses_by_instructor(instructor)
        courses      = CourseModel.get_courses_by_instructor(instructor)

        template_values = {                                                    
            'user':         user,
            'sign_out':     users.create_logout_url('/'),
            'courses':      courses,
            'edit_courses': edit_courses,
            'quarters':     {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        }
        template = JINJA_ENV.get_template('/templates/admin_view_courses.html')
        return self.response.write(template.render(template_values))        
