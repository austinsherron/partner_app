import jinja2
import os

from google.appengine.api import images, users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required

from src.handler.base_handler import BaseHandler
from src.models.settings import SettingModel
from src.models.student import StudentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class EditProfile(BaseHandler):

    @login_required
    def get(self):
        template = JINJA_ENV.get_template('/templates/partner_update_profile.html')

        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())

        if not student:
            # redirect to main page if the student doesn't exist in the DB
            return self.redirect('/partner')

        programming_ability  = ['0: Never before this class, or just a few times', '1: I\'ve done some programming, but not as much as a whole class']
        programming_ability += ['2: I\'ve done the equivalent of one programming course, but not a whole year\'s worth']
        programming_ability += ['3: I have one to two years of programming experience', '4: I have been programming for more than two years']

        template_values = {
            'user':                user,
            'sign_out':            users.create_logout_url('/'),
            'student':             student,
            'programming_ability': programming_ability,
            'key':                 student.key.urlsafe(),
        }
        return self.response.write(template.render(template_values))


    def post(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())

        student.preferred_name      = self.request.get('preferred_name').strip()
        bio                         = self.request.get('bio').strip()
        student.bio                 = bio if bio != '' else student.bio
        availability                = self.request.get('availability').strip()
        student.availability        = availability if availability != '' else student.availability
        programming_ability         = self.request.get('programming_ability')
        student.programming_ability = programming_ability

        # grab image and resize if necessary
        avatar         = str(self.request.get('avatar'))
        student.avatar = images.resize(avatar, 320, 320) if avatar != '' else student.avatar

        phone_number         = self.request.get('phone_number')
        student.phone_number = phone_number if phone_number != '000-000-0000' else student.phone_number
        student.put()

        # redirect to main page
        return self.redirect('/partner/edit/profile')
