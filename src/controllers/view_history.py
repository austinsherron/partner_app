import jinja2
import os

from google.appengine.api import users
from webapp2_extras.appengine.users import login_required

from datetime import date, datetime, timedelta
from models import Invitation
from src.handler.base_handler import BaseHandler
from src.models.assignment import AssignmentModel
from src.models.eval import EvalModel
from src.models.partnership import PartnershipModel
from src.models.invitation import InvitationModel
from src.models.settings import SettingModel
from src.models.student import StudentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class ViewHistory(BaseHandler):
    @login_required
    def get(self):
        user = users.get_current_user()

        try:
            quarter = SettingModel.quarter()
            year    = SettingModel.year()
            student = StudentModel.get_student_by_email(quarter, year, user.email())

            active_assigns      = map(lambda x: x.number, AssignmentModel.get_active_assigns(quarter, year))
            assign_range        = AssignmentModel.get_assign_range(quarter, year)
            partner_history     = PartnershipModel.get_active_partner_history_for_student(student, quarter, year, fill_gaps=assign_range)
            all_partner_history = PartnershipModel.get_all_partner_history_for_student(student, quarter, year)

            evals  = EvalModel.get_eval_history_by_evaluator(student, True, quarter, year).fetch()
            evals += EvalModel.get_eval_history_by_evaluator(student, False, quarter, year).fetch()
            evals  = sorted(evals, key=lambda x: x.assignment_number)

        except AttributeError:
            return self.redirect('/partner')

        template = JINJA_ENV.get_template('/templates/partner_student_view.html')
        template_values = {
            'student':      student,
            'partners':     partner_history,
            'all_partners': all_partner_history,
            'assign_range': assign_range,
            'active':       active_assigns,
            'evals':        evals,
            'user':         users.get_current_user(),
            'sign_out':     users.create_logout_url('/'),
        }
        return self.response.write(template.render(template_values))


class ViewInvitationHistory(BaseHandler):

    @login_required
    def get(self):
        template = JINJA_ENV.get_template('/templates/partner_invitation_history.html')

        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())

        # redirect to main page if student doesn't exist
        if not student:
            return self.redirect('/partner')

        invites            = InvitationModel.get_all_invitations_involving_student(student).order(Invitation.assignment_number).fetch()
        current_assignment = AssignmentModel.get_active_assign_with_latest_fade_in_date(quarter, year)

        # if there are no assignments for this quarter, render early to avoid errors
        if not current_assignment:
            return self.response.write(template.render({'user': user, 'sign_out': users.create_logout_url('/')}))

        partners        = PartnershipModel.get_active_partner_history_for_student(student, quarter, year)
        current_partner = PartnershipModel.get_partner_from_partner_history_by_assign(student, partners, current_assignment.number)
        active_range    = set([a.number for a in AssignmentModel.get_active_assigns(quarter, year)])

        invite_info = {}
        # dict for custom ordering of invite info fields
        ordering = {'Assign Num': 0, 'Who': 1, 'To/From': 2, 'Accepted': 3, 'Active': 4}
        for invite in invites:
            # organize invite info by time
            i = (invite.created - timedelta(hours=8)).strftime('%m-%d-%Y %H:%M:%S')
            invite_info[i] = {}

            invite_info[i]['Assign Num'] = invite.assignment_number

            # determine wheather invite was sent or received in relation to the user
            invite_info[i]['To/From'] = 'Sent' if invite.invitor == student.key else 'Received'
            who_key                   = invite.invitee if invite_info[i]['To/From'] == 'Sent' else invite.invitor
            who                       = who_key.get()

            # add invitor/invitee (depending on 'Sent'/'Received') to invite info
            invite_info[i]['Who']      = str(who.last_name) + ', ' + str(who.first_name) + ' - ' + str(who.ucinetid)
            invite_info[i]['Accepted'] = str(invite.accepted)
            invite_info[i]['Active']   = str(invite.active)
            invite_info[i]['key']      = invite.key.urlsafe()

        template_values = {
            'invites':      sorted(invite_info.items(), reverse=True),
            'fields':       sorted(ordering.items(), key=lambda x: x[1]),
            'user':         user,
            'sign_out':     users.create_logout_url('/'),
            'active_range': active_range,
        }
        return self.response.write(template.render(template_values))
