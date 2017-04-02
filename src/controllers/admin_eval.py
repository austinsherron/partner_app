import jinja2
import os

from google.appengine.api import users
from webapp2_extras.appengine.users import admin_required

from src.helpers.admin_helpers import keys_to_partners, student_info_to_partner_list
from src.handler.base_handler import BaseHandler
from src.helpers.helpers import get_sess_val, get_sess_vals
from src.models.assignment import AssignmentModel
from src.models.eval import EvalModel
from src.models.settings import SettingModel
from src.models.student import StudentModel
from src.models.partnership import PartnershipModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)

class ExtendEvals(BaseHandler):

    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        quarter     = self.request.get('quarter')                                   # try grabbing quarter/year from URL
        year        = self.request.get('year')

        if not quarter or not year:                                                 # if they don't exist, try grabbing from session
            temp = get_sess_vals(self.session, 'quarter', 'year')
            if not temp:                                                            # if they don't exist there, redirect with error
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp

        quarter, year = int(quarter), int(year)
        view_by       = self.request.get('view_by')                                  # check URL for 'view by' options (lab vs class)
        view_by       = view_by if view_by else 1

        if view_by == 'class':                                                      # if user wants to view by class, or the view by option wasn't specified...
            students = StudentModel.get_students_by_active_status(quarter, year).fetch()
        else:
            students = StudentModel.get_students_by_lab(quarter, year, int(view_by)).fetch()

        all_partners = PartnershipModel.get_all_partnerships(quarter, year).fetch()
        print all_partners
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
        template = JINJA_ENV.get_template('/templates/admin_eval_exception.html')
        return self.response.write(template.render(template_values))


class ViewEvals(BaseHandler):

    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded
        quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        quarter     = self.request.get('quarter')                                   # try grabbing quarter/year from URL
        year        = self.request.get('year')
        assign_num  = self.request.get('assign_num')                                # try grabbing assignment number from URL

        if not quarter or not year:                                                 # if they don't exist, try grabbing from session
            temp = get_sess_vals(self.session, 'quarter', 'year')
            if not temp:                                                            # if they don't exist there, redirect with error
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp

        quarter,year       = int(quarter), int(year)
        current_assignment = AssignmentModel.get_active_assign_with_latest_fade_in_date(quarter, year)

        if current_assignment and not assign_num:
            assign_num = current_assignment.number

        assign_num    = int(assign_num) if assign_num else 1                          # (to avoid errors if there are no assignments in the DB
        last_num      = AssignmentModel.get_assign_n(quarter, year, -1)
        last_num      = last_num.number if last_num else assign_num                   # (to avoid errors if there are no assignments in the DB)
        first_assign  = AssignmentModel.get_assign_n(quarter, year, 0)
        first_num     = 0 if not first_assign else first_assign.number
        evals         = EvalModel.get_all_evals_for_assign(quarter, year, assign_num)                # grab evals for assignment...
        solo_partners = PartnershipModel.get_solo_partnerships_by_assign(quarter, year, assign_num)  # ...and grab endorsed solos (they're exempt from evals)

        template_values = {
            'user':         users.get_current_user(),
            'sign_out':     users.create_logout_url('/'),
            'quarter':      quarter,
            'quarter_name': quarter_map[quarter],
            'year':         year,
            'assign_num':   assign_num,
            'message':      self.request.get('message'),
            'evals':        evals,
            'solos':        solo_partners,
            'first_num':    first_num,
            'last_num':     last_num,
        }
        template = JINJA_ENV.get_template('/templates/admin_evals_view.html')
        return self.response.write(template.render(template_values))
