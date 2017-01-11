import jinja2
import os

from datetime import date, datetime, timedelta
from google.appengine.api import images, users
from webapp2_extras.appengine.users import login_required

from src.handler.base_handler import BaseHandler
from src.models.assignment import AssignmentModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel
from src.models.message import MessageModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class PartnerMoreInfo(BaseHandler):

    @login_required
    def get(self):
        # delcare page template
        template = JINJA_ENV.get_template('/templates/partners_main.html')
        # get current user
        user = users.get_current_user()
        student = None

        try:
            quarter  = SettingModel.quarter()
            year     = SettingModel.year()
            user     = users.get_current_user()
            selector = StudentModel.get_student_by_email(quarter, year, user.email())
            if not selector:
                return self.redirect('/partner')
            # get error message, if any
            e = self.request.get('error')

            # get own email to query partner information.
            assgn_num = int(self.request.get('assgn'))

            # get list of all partners for student (roundabout solution)
            all_assigns = sorted(AssignmentModel.get_all_assign(quarter, year), key = lambda x: x.number)
            partner_history = PartnershipModel.get_all_partner_history_for_student(selector, quarter, year)
            all_partners = dict([(x.number,PartnershipModel.get_partner_from_partner_history_by_assign(selector, partner_history, x.number)) for x in all_assigns])

            # get queried partnership
            partnership = None
            for p in partner_history:
                if p.assignment_number == assgn_num:
                    partnership = p

            # Redirect to landing if query for that assignment's partnership turns up empty
            if not len(all_partners[assgn_num]):
                message = MessageModel.page_not_found()
                return self.redirect('/partner?message=' + message)

        except (AttributeError, IndexError):
            template_values = {
                'user': user,
                'student': student,
                'sign_out': users.create_logout_url('/'),
                'email': user.email()
            }
            return self.response.write(template.render(template_values))
        # pass template values...
        template_values = {
            'error':            e,
            'selector':         selector,
            'partner':          all_partners[assgn_num][0],
            'partnership':      partnership,
            'user':             user,
            'sign_out':         users.create_logout_url('/'),
        }
        template = JINJA_ENV.get_template('/templates/partner_more_info.html')
        self.response.write(template.render(template_values))
