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
from src.models.settings import MessageModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel
from src.send_mail import SendMail 


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


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
        elif PartnershipModel.student_has_partner_for_assign(confirming, for_assign):
            message = MessageModel.already_has_partner(admin)
        else:
            message     = MessageModel.confirm_partnership([being_confirmed, confirming], admin, being_confirmed)
            partnership = PartnershipModel.create_partnership([being_confirmed, confirming], for_assign)

        # set invitations between invitor and invitee (for current assignment) to inactive
        InvitationModel.deactivate_invitations_for_students_and_assign(confirming, being_confirmed, for_assign)
        # SendMail(partnership, 'partner_confirm')

        if not admin:
            return self.redirect('/partner?message=' + message)
        else:
            return self.redirect('/admin/partners/add?message=' + message)
            

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
        # check if selector and selected have been partners
        previous_partners = PartnershipModel.get_partnerships_for_pair(selector, selected)
        # check if selector has and selected have open inviations for current assignment
        current_invitations = InvitationModel.get_open_invitations_for_pair_for_assign(selector, selected, selected_assign).fetch()

        # redirect with error...
        # ...if selected and selector have worked together previously
        if previous_partners and not SettingModel.repeat_partners():
            e = 'Sorry, you\'ve already worked with, or are currently working with '
            e += str(selected.last_name) + ', ' + str(selected.first_name)
            e += '. If you think you have a legitimate reason to repeat a partnership'
            e += ', please contact your TA'
            return self.redirect('/partner/selection?error=' + e)
        # ... or if selected and selector have open invitations for the current assignment
        if len(PartnershipModel.get_partnerships_for_pair_by_assign(selector, selected, selected_assign)) > 0:
            e = 'Sorry, you are currently working with '
            e += str(selected.last_name) + ', ' + str(selected.first_name)
            return self.redirect('/partner/selection?error=' + e)
        if current_invitations:
            e = 'You already have open invitations with '
            e += str(selected.last_name) + ', ' + str(selected.first_name)
            return self.redirect('/partner/selection?error=' + e)
        else:
            invitation = Invitation(invitor = selector.key, invitee = selected.key,
                assignment_number = selected_assign, active = True)
            # ...and save it
            invitation.put()    

            message = 'Invitation to ' + str(selected.last_name) + ', '
            message += str(selected.first_name) + ' confirmed. Please refresh the page.'

            return self.redirect('/partner?message=' + message)


