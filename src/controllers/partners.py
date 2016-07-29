import jinja2
import os

from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required

from models import Student, Invitation, Partnership, Evaluation, Setting
from src.handler.base_handler import BaseHandler
from src.models.assignment import AssignmentModel
from src.models.eval import EvalModel
from src.models.invitation import InvitationModel
from src.models.message import MessageModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel
from src.send_mail import SendMail 


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class CancelPartner(BaseHandler):
    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())

        cancel      = int(self.request.get('cancel'))
        partnership = ndb.Key(urlsafe=self.request.get('p')).get()

        if cancel:
            partnership = PartnershipModel.cancel_partnership(student, partnership)
            if not partnership.active:
                EvalModel.cancel_evals_for_partnership(partnership)
            return self.redirect('/partner/history?message=' + MessageModel.partnership_cancelled())
        else:
            PartnershipModel.uncancel_partnership(student, partnership)
            return self.redirect('/partner/history?message=' + MessageModel.partnership_uncancelled())


class ConfirmInvitation(BaseHandler):

    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()

        invitation      = ndb.Key(urlsafe=self.request.get('confirmed')).get()
        confirming      = StudentModel.get_student_by_email(quarter, year, user.email())
        being_confirmed = invitation.invitor.get()
        for_assign      = invitation.assignment_number

        partnership = None
        if not confirming and PartnershipModel.student_has_partner_for_assign(being_confirmed, for_assign):
            message = MessageModel.already_has_partner(False)
        elif PartnershipModel.student_has_partner_for_assign(being_confirmed, for_assign):
            message = MessageModel.already_has_partner(False)
        elif PartnershipModel.student_has_partner_for_assign(confirming, for_assign):
            message = MessageModel.already_has_partner(False)
        else:
            message     = MessageModel.confirm_partnership([being_confirmed, confirming], False, being_confirmed)
            partnership = PartnershipModel.create_partnership([being_confirmed, confirming], for_assign)

        # set invitations between invitor and invitee (for current assignment) to inactive
        if partnership:
            InvitationModel.deactivate_invitations_for_students_and_assign(confirming, being_confirmed, for_assign)
            # SendMail(partnership, 'partner_confirm')

        return self.redirect('/partner?message=' + message)


class ConfirmPartner(BaseHandler):
    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())

        active_assigns = AssignmentModel.get_active_assigns(quarter, year)
        invitations    = InvitationModel.get_recvd_invites_by_student_and_mult_assigns(student, [x.number for x in active_assigns], as_dict=False)

        # check to see if partner selection is still active
        selection_closed = len(active_assigns) == 0

        # pass template values...
        template_values = {
            'student':          student,             
            'selection_closed': selection_closed,
            'invitations':      invitations,
        }
        template = JINJA_ENV.get_template('/templates/partner_confirm.html')
        self.response.write(template.render(template_values))


    def post(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()

        # these will only have values if this request is coming from an admin
        confirming_key      = self.request.get('admin_confirming')
        being_confirmed_key = self.request.get('admin_being_confirmed')

        # if not admin...
        if not confirming_key or not being_confirmed_key:
            invitation      = ndb.Key(urlsafe=self.request.get('confirmed')).get()
            confirming      = StudentModel.get_student_by_email(quarter, year, user.email())
            being_confirmed = invitation.invitor.get()
            for_assign      = invitation.assignment_number
            admin           = False
        else:
            for_assign      = int(self.request.get('assign_num'))
            being_confirmed = ndb.Key(urlsafe=being_confirmed_key).get()
            confirming      = ndb.Key(urlsafe=confirming_key).get() if confirming_key != 'None' else None
            admin           = True

        partnership = None
        if not confirming and PartnershipModel.student_has_partner_for_assign(being_confirmed, for_assign):
            message = MessageModel.already_has_partner(admin)
        elif not confirming:
            message     = MessageModel.confirm_solo_partnership(being_confirmed)
            partnership = PartnershipModel.create_partnership([being_confirmed], for_assign)
        elif PartnershipModel.student_has_partner_for_assign(being_confirmed, for_assign):
            message = MessageModel.already_has_partner(admin)
#            message = ''
#            partnership = PartnershipModel.get_partnerships_for_students_by_assign([being_confirmed], for_assign)
#            partnership = PartnershipModel.add_members_to_partnership([confirming], partnership[0])
        elif PartnershipModel.student_has_partner_for_assign(confirming, for_assign):
            message = MessageModel.already_has_partner(admin)
        else:
            message     = MessageModel.confirm_partnership([being_confirmed, confirming], admin, being_confirmed)
            partnership = PartnershipModel.create_partnership([being_confirmed, confirming], for_assign)

        # set invitations between invitor and invitee (for current assignment) to inactive
        if partnership:
            InvitationModel.deactivate_invitations_for_students_and_assign(confirming, being_confirmed, for_assign)
            # SendMail(partnership, 'partner_confirm')

        if not admin:
            return self.redirect('/partner?message=' + message)
        else:
            return self.redirect('/admin/partners/add?message=' + message)


class DeclineInvitation(BaseHandler):

    @login_required
    def get(self):
        invitation = ndb.Key(urlsafe=self.request.get('confirmed')).get()
        InvitationModel.update_invitation_status(invitation.key, active=False)
        message = MessageModel.invitation_declined()
        return self.redirect('/partner?message=' + message)
            

class SelectPartner(BaseHandler):
    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()

        user     = users.get_current_user()
        selector = StudentModel.get_student_by_email(quarter, year, user.email())
        # if cross section partnership aren't allowed, use selector info to find students in same lab section
        if not SettingModel.cross_section_partners():
            selectees = StudentModel.get_students_by_lab(quarter, year, selector.lab)
        else:
            selectees = StudentModel.get_students_by_active_status(quarter, year)                

        active_assigns = AssignmentModel.get_active_assigns(quarter, year)
        # get error message, if any
        e = self.request.get('error')        
        # check to see if partner selection period has closed
        selection_closed = len(active_assigns) == 0

        template_values = {
            'error': e,
            'selector': selector,                                  
            'selectees': selectees.order(Student.last_name),    
            'selection_closed': selection_closed,
            'active': active_assigns,
        }
        template = JINJA_ENV.get_template('/templates/partner_selection.html')
        self.response.write(template.render(template_values))


    def post(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()

        user     = users.get_current_user()
        selector = StudentModel.get_student_by_email(quarter, year, user.email())
        selected = StudentModel.get_student_by_student_id(quarter, year, self.request.get('selected_partner'))
        try:
            selected_assign = int(self.request.get('selected_assign'))
        except ValueError:
            return self.redirect('/partner/selection?error=You must choose an assignment number')

        # redirect with errors...
        if PartnershipModel.were_partners_previously([selector, selected]) and not SettingModel.repeat_partners():
            return self.redirect('/partner/selection?error=' + MessageModel.worked_previously(selected))
        elif InvitationModel.have_open_invitations(selector, selected, selected_assign):
            return self.redirect('/partner/selection?error=' + MessageModel.have_open_invitations(selected))
        elif PartnershipModel.student_has_partner_for_assign(selector, selected_assign):
            return self.redirect('/partner/selection?error=' + MessageModel.already_has_partner(False, False))
        else:
            InvitationModel.create_invitation(selector, selected, selected_assign)
            return self.redirect('/partner?message=' + MessageModel.sent_invitation(selected))


