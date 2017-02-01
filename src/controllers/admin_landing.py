import jinja2
import os

from google.appengine.api import users
from webapp2_extras.appengine.users import admin_required

from src.handler.base_handler import BaseHandler
from src.models.assignment import AssignmentModel
from src.models.eval import EvalModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class MainAdmin(BaseHandler):

    #@admin_required
    def get(self):
        user    = users.get_current_user()                                        
        quarter = SettingModel.quarter()
        year    = SettingModel.year()

        # grab message from URL, if it exists
        message = self.request.get('message')                                

        if (not quarter or not year) and not message:
            message = 'Please set a current year and quarter'

        template_values = {                                                    
            'message':  message,
            'user':     user,
            'sign_out': users.create_logout_url('/'),
            'quarter':  quarter,
            'year':     year,
        }

        self.session['quarter'] = quarter                                     
        self.session['year']    = year

        if quarter and year:
            template_values['active_students']   = len(StudentModel.get_students_by_active_status(quarter, year).fetch())
            template_values['inactive_students'] = len(StudentModel.get_students_by_active_status(quarter, year, active=False).fetch())
            cur_assign                           = AssignmentModel.get_active_assign_with_latest_fade_in_date(quarter, year)

            if cur_assign:
                template_values['cur_assign'] = cur_assign
                # grab number of active partnerships for the current assignment
                template_values['assign_partners'] = len(PartnershipModel.get_all_partnerships_for_assign(quarter, year, cur_assign.number))
                eval_assign                        = AssignmentModel.get_active_assign_with_earliest_eval_due_date(quarter, year)            

                if eval_assign:
                    template_values['eval_assign'] = eval_assign
                    # grab number of evals for the current eval assignment
                    template_values['assign_eval'] = len(EvalModel.get_all_evals_for_assign(quarter, year, cur_assign.number).fetch())

        template = JINJA_ENV.get_template('/templates/admin.html')
        return self.response.write(template.render(template_values))        


