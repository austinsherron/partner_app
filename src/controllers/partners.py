import jinja2
import os

from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required

from handler import CustomHandler
from models import Student, Invitation, Partnership, Evaluation, Setting
from src.models.assignment import AssignmentModel
from src.models.eval import EvalModel
from src.models.invitation import InvitationModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel
from src.send_mail import SendMail 


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class ConfirmPartner(CustomHandler):
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

        # find all active partnership and invitation involving students
        if confirming:
            invitations        = InvitationModel.get_all_invites_by_student_and_assign(confirming, for_assign)
            invitations       += InvitationModel.get_all_invites_by_student_and_assign(being_confirmed, for_assign)
            open_partnerships  = PartnershipModel.get_partnerships_by_student_and_assign(confirming, quarter, year, for_assign).fetch()
            open_partnerships += PartnershipModel.get_partnerships_by_student_and_assign(being_confirmed, quarter, year, for_assign).fetch()
        else:
            invitations       = InvitationModel.get_all_invites_by_student_and_assign(being_confirmed, for_assign)
            open_partnerships = PartnershipModel.get_partnerships_by_student_and_assign(being_confirmed, quarter, year, for_assign).fetch()

        # deactivate partnerships, keep track of active evals so they can be deactivated
        active_evals = []
        for partnership in open_partnerships:

            if partnership.initiator:
                active_evals += EvalModel.get_eval_by_evaluator_and_assign(partnership.initiator, for_assign)
            if partnership.acceptor:
                active_evals += EvalModel.get_eval_by_evaluator_and_assign(partnership.acceptor, for_assign)

            partnership.active = False
            partnership.put()
            SendMail(partnership, 'partner_deactivated')

        # decativate active evals
        for eval in active_evals:
            eval.active = False
            eval.put()

        # set invitations between invitor and invitee (for current assignment) to inactive
        for invitation in invitations:
            invitation.active = False

            # set the accepted invitation to accepted == True
            if confirming and (invitation.invitor == being_confirmed.key and invitation.invitee == confirming.key):
                invitation.accepted = True

            invitation.put()

        # create new partnership...
        partnership = Partnership(initiator = being_confirmed.key, acceptor = confirming.key if confirming else None,
            assignment_number = for_assign, active = True,
            year = being_confirmed.year, quarter = being_confirmed.quarter)

        # ...and save it
        partnership.put()
        SendMail(partnership, 'partner_confirm')

        if not admin:
            message = 'Partnership with ' + str(being_confirmed.last_name) + ', ' 
            message += str(being_confirmed.first_name) + ' confirmed.'
            message += ' Please refresh the page.'
            return self.redirect('/partner?message=' + message)
        else:
            message = 'Partnership between ' + str(being_confirmed.ucinetid) + ' and ' 
            message += (confirming.ucinetid if confirming else '"No Partner"') + ' successfully created.'
            return self.redirect('/admin/partners/add?message=' + message)
            

class SelectPartner(CustomHandler):
    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()

        # get current user info
        user = users.get_current_user()
        # use user info to find student in DB (the selector)
        selector = StudentModel.get_student_by_email(quarter, year, user.email())
        # if cross section partnership aren't allowed, use selector info to find students in same lab section
        if not SettingModel.cross_section_partners():
            selectees = StudentModel.get_students_by_lab(quarter, year, selector.lab)
        else:
            selectees = StudentModel.get_students_by_active_status(quarter, year)                
        # get active assignments
        active_assigns = AssignmentModel.get_active_assigns(quarter, year)
        # get error message, if any
        e = self.request.get('error')        
        # check to see if partner selection period has closed
        selection_closed = len(active_assigns) == 0

        # pass template values...
        template_values = {
            'error': e,
            'selector': selector,                                  # ...student object
            'selectees': selectees.order(Student.last_name),    # ...query of student objects
            'selection_closed': selection_closed,
            'active': active_assigns,
        }
        template = JINJA_ENV.get_template('/templates/partner_selection.html')
        self.response.write(template.render(template_values))


    def post(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()

        # get current user info
        user = users.get_current_user()
        # use user info to find student in DB (the selector)
        selector = StudentModel.get_student_by_email(quarter, year, user.email())
        # use form data to find student that was selected (selected) 
        selected = StudentModel.get_student_by_student_id(quarter, year, self.request.get('selected_partner'))
        # use from data to get assignment for which student is choosing partner
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
            # create invitation object with selector as invitor...
            invitation = Invitation(invitor = selector.key, invitee = selected.key,
                assignment_number = selected_assign, active = True)
            # ...and save it
            invitation.put()    

            message = 'Invitation to ' + str(selected.last_name) + ', '
            message += str(selected.first_name) + ' confirmed. Please refresh the page.'

            return self.redirect('/partner?message=' + message)


