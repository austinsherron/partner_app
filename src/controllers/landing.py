import jinja2
import os
import webapp2

from google.appengine.api import users
from webapp2_extras.appengine.users import login_required

from handler import CustomHandler
from src.models.assignment import AssignmentModel
from src.models.eval import EvalModel
from src.models.invitation import InvitationModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class MainPage(CustomHandler):
    @login_required
    def get(self):

        # delcare page template
        template = JINJA_ENV.get_template('/templates/partners_main.html')
        # get current user
        user = users.get_current_user()
        student = None

        try:
            quarter = SettingModel.quarter()
            year    = SettingModel.year()
            # use user info to find student int DB
            student = StudentModel.get_student_by_email(quarter, year, user.email())

            self.session['quarter'] = quarter
            self.session['year']    = year
            self.session['student'] = student.key.urlsafe()

            # get active assignments
            active_assigns = sorted(AssignmentModel.get_active_assigns(quarter, year), key=lambda x: x.number)
            # get active eval assigns
            eval_assigns = sorted(AssignmentModel.get_active_eval_assigns(quarter, year), key=lambda x: x.number)
            # find any active invitations for the current assignment that student has sent
            sent_invitations = InvitationModel.get_sent_invites_by_student_and_mult_assigns(student, [x.number for x in active_assigns])
            # find any active invitations for the current assignment that the student has received
            received_invitations = InvitationModel.get_recvd_invites_by_student_and_mult_assigns(student, [x.number for x in active_assigns])
            # find any partnerships in which the student has been involved
            partners = PartnershipModel.get_active_partner_history_for_student(student, quarter, year)
            partners = dict([(x.number,PartnershipModel.get_partner_from_partner_history_by_assign(student, partners, x.number)) for x in active_assigns])
            # find evals the student has submitted
            evals = EvalModel.get_eval_history_by_evaluator(student, True, quarter, year)
            evals = dict([(x.assignment_number,x) for x in evals])
            # get activity message, if any
            message = self.request.get('message')
            dropped = []
            for x in active_assigns:
                dropped += PartnershipModel.get_inactive_partnerships_by_student_and_assign(student, x.number).fetch()
            dropped = sorted(dropped, key=lambda x: x.assignment_number)

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
            'user': user,
            'student': student,                             # ...student object
            'active': active_assigns,
            'evals': eval_assigns,
            'submitted_evals': evals,
            'sent_invitations': sorted(sent_invitations, key=lambda x: x.assignment_number),    # ...list of invitation objects
            'received_invitations': sorted(received_invitations.items(), key=lambda x: x[0]),    # ...list of invitation objects
            'partners': partners,                            # ...dict of partnership objects
            'sign_out': users.create_logout_url('/'),        # sign out url
            'message': message,
            'profile': student.bio is None or student.availability is None or student.programming_ability is None,
            'dropped': dropped,
            'show_dropped': len(dropped) > 0 and len(filter(lambda x: x != None, partners.values())) < len(active_assigns),
        }
        self.response.write(template.render(template_values))


class Main(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        template = JINJA_ENV.get_template('/templates/index.html')
        template_values = {}

        if user:
            template_values['user'] = user.email()
            template_values['sign_out'] = users.create_logout_url('/')
        else:
            template_values['sign_in'] = users.create_login_url('/partner')

        self.response.write(template.render(template_values))

