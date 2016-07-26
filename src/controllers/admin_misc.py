import jinja2
import os

from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import admin_required

from handler import CustomHandler
from models import Assignment, Student, Setting
from src.models.assignment import AssignmentModel
from src.models.settings import SettingModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class ClearDB(CustomHandler):

    #@admin_required
    def get(self):
        template = JINJA_ENV.get_template('/templates/admin_cleardb.html')
        self.response.write(template.render())


    def post(self):
        if bool(self.request.get('choice')):
            ndb.delete_multi(Student.query().fetch(keys_only=True))
            ndb.delete_multi(Assignment.query().fetch(keys_only=True))
            ndb.delete_multi(Setting.query().fetch(keys_only=True))

        self.redirect('/admin')


class UpdateSettings(CustomHandler):

    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded 
        quarters = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        quarter  = SettingModel.quarter()
        year     = SettingModel.year()
        num_labs = SettingModel.num_labs()

        template_values = {
            'repeat_partners':        SettingModel.repeat_partners(),
            'cross_section_partners': SettingModel.cross_section_partners(),
            'year':                   year,
            'quarter':                quarter,
            'quarters':               sorted(quarters.items()),
            'num_labs':               num_labs if num_labs else 1,
            'user':                   users.get_current_user(),
            'sign_out':               users.create_logout_url('/'),
        }
        template = JINJA_ENV.get_template('/templates/admin_edit_settings.html')
        return self.response.write(template.render(template_values))


    def post(self):
        setting = Setting.query().get()

        if not setting:
            setting = Setting()

        setting.year                   = int(self.request.get('year'))
        setting.quarter                = int(self.request.get('quarter'))
        setting.num_labs               = int(self.request.get('num_labs'))
        setting.repeat_partners        = eval(self.request.get('repeat_partners'))
        setting.cross_section_partners = eval(self.request.get('cross_section_partners'))

        setting.put()
        return self.redirect('/admin?message=Quarter and Year Updated')


