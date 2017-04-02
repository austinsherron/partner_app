import jinja2
import os
import webapp2

from google.appengine.api import users
from webapp2_extras.appengine.users import admin_required

from src.handler.base_handler import BaseHandler
from src.helpers.admin_helpers import keys_to_partners, student_info_to_partner_list
from src.helpers.helpers import get_sess_val, get_sess_vals
from src.models.assignment import AssignmentModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)

class AddSoloPartnership(BaseHandler):

    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        quarter     = self.request.get('quarter')                           # try grabbing quarter/year from URL
        year        = self.request.get('year')

        if not quarter or not year:                                         # if they don't exist, try grabbing from session
            temp = get_sess_vals(self.session, 'quarter', 'year')
            if not temp:                                                    # if they don't exist there, redirect with error
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp

        quarter,year = int(quarter), int(year)
        view         = self.request.get('view')                             # check URL for 'view by' options (lab vs class)
        view         = view if view else 'class'

        if view == 'class':
            students = StudentModel.get_students_by_active_status(quarter, year).fetch()
        else:
            students = StudentModel.get_students_by_lab(quarter, year, int(view)).fetch()

        current_assign = AssignmentModel.get_active_assign_with_latest_fade_in_date(quarter, year)
        current_num    = 1 if not current_assign else current_assign.number

        template        = JINJA_ENV.get_template('/templates/admin_add_solo_partnership.html')
        template_values = {
            'students':    sorted(students, key=lambda x: x.last_name),
            'view':        str(view),
            'quarter':     quarter,
            'year':        year,
            'user':        users.get_current_user(),
            'sign_out':    users.create_logout_url('/'),
            'current_num': current_num,
            'num_labs':    SettingModel.num_labs() if SettingModel.num_labs() else 1,
        }
        return self.response.write(template.render(template_values))


class AddPartnership(BaseHandler):

    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded
        quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        quarter     = self.request.get('quarter')                           # try grabbing quarter/year from URL
        year        = self.request.get('year')

        if not quarter or not year:                                         # if they don't exist, try grabbing from session
            temp = get_sess_vals(self.session, 'quarter', 'year')
            if not temp:                                                    # if they don't exist there, redirect with error
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp

        quarter,year = int(quarter), int(year)
        view         = self.request.get('view')                             # check URL for 'view by' options (lab vs class)
        view         = view if view else 'class'

        if view == 'class':
            students = StudentModel.get_students_by_active_status(quarter, year).fetch()
        else:
            students = StudentModel.get_students_by_lab(quarter, year, int(view)).fetch()

        current_assign = AssignmentModel.get_active_assign_with_latest_fade_in_date(quarter, year)
        current_num    = 1 if not current_assign else current_assign.number

        template        = JINJA_ENV.get_template('/templates/admin_add_partnership.html')
        template_values = {
            'students':    sorted(students, key=lambda x: x.last_name),
            'view':        str(view),
            'quarter':     quarter,
            'year':        year,
            'user':        users.get_current_user(),
            'sign_out':    users.create_logout_url('/'),
            'current_num': current_num,
            'num_labs':    SettingModel.num_labs() if SettingModel.num_labs() else 1,
        }
        return self.response.write(template.render(template_values))


class ViewPartnerships(BaseHandler):

    #@admin_required
    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded
        #    rethink logic
        quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        quarter     = self.request.get('quarter')                                   # try grabbing quarter/year from URL
        year        = self.request.get('year')

        if not quarter or not year:                                                 # if they don't exist, try grabbing from session
            temp = get_sess_vals(self.session, 'quarter', 'year')
            if not temp:                                                            # if they don't exist there, redirect with error
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp

        quarter,year = int(quarter), int(year)
        view_by      = self.request.get('view_by')                                  # check URL for 'view by' options (lab vs class)
        view_by      = view_by if view_by else 1

        if view_by == 'class':                                                      # if user wants to view by class, or the view by option wasn't specified...
            students = StudentModel.get_students_by_active_status(quarter, year).fetch()
        else:
            students = StudentModel.get_students_by_lab(quarter, year, int(view_by)).fetch()

        all_partners = PartnershipModel.get_all_partnerships(quarter, year).fetch()
        last_assign  = AssignmentModel.get_assign_n(quarter, year, -1)
        last_num     = 1 if not last_assign else last_assign.number
        first_assign = AssignmentModel.get_assign_n(quarter, year, 0)
        first_num    = 0 if not first_assign else first_assign.number

        keys_to_students     = dict(map(lambda x: (x.key,x), students))            # map student objects to keys for easy, fast access from partnership objects
        keys_to_partnerships = keys_to_partners(all_partners)                      # map student keys to partnerships for easy, fast access

        # create mapping of student info to partnership info that the partnership template expects
        partnership_dict = student_info_to_partner_list(last_num, first_num, keys_to_partnerships, keys_to_students, students)
        partnership_dict = sorted(partnership_dict.items(), key=lambda x: (x[0][4], x[0][2]))
        num_labs         = SettingModel.num_labs()

        template_values = {
            'partnerships': partnership_dict,
            'view_by':      str(view_by),
            'year':         year,
            'quarter':      quarter,
            'num_labs':     num_labs if num_labs else 0,
            'last_num':     last_num,
            'first_num':    first_num,
            'user':         users.get_current_user(),
            'sign_out':     users.create_logout_url('/'),
        }
        template = JINJA_ENV.get_template('/templates/admin_partnerships.html')
        return self.response.write(template.render(template_values))
