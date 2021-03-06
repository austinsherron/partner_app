import jinja2
import os
import webapp2
import datetime
import time

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

class CancelModal(BaseHandler):
    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())

        assgn_num = int(self.request.get('n'))
        assignment = AssignmentModel.get_assign_by_number(quarter, year, assgn_num)
        partnership = PartnershipModel.get_active_partnerships_involving_students_by_assign([student], assgn_num).get()

        # get list of all partners for student (roundabout solution)
        all_assigns = sorted(AssignmentModel.get_all_assign(quarter, year), key = lambda x: x.number)
        partner_history = PartnershipModel.get_all_partner_history_for_student(student, quarter, year)
        all_partners = dict([(x.number,PartnershipModel.get_partner_from_partner_history_by_assign(student, partner_history, x.number)) for x in all_assigns])

        current_time = datetime.datetime.fromtimestamp(time.time())
        current_time = current_time - datetime.timedelta(hours=7)

        # pass template values...
        template_values = {
            'student':          student,
            'partnership':      partnership,
            'partner':          all_partners[assgn_num][0],
            'assignment':       assignment,
            'current_time':     current_time,
            'assgn_num':        assgn_num

        }
        template = JINJA_ENV.get_template('/templates/cancel_partner_modal.html')
        self.response.write(template.render(template_values))


class CancelPartner(BaseHandler):
    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())
        assgn_num = 0

        cancel      = int(self.request.get('cancel'))
        partnership = ndb.Key(urlsafe=self.request.get('p')).get()

        if cancel:
            assgn_num = partnership.assignment_number

        if cancel:
            # refine implementation of cancellation eventually
            for s in partnership.members:
                partnership = PartnershipModel.cancel_partnership(s, partnership)
            if not partnership.active:
                EvalModel.cancel_evals_for_partnership(partnership)
            time.sleep(0.1)
            return self.redirect('/partner?message=' + MessageModel.partnership_cancelled(assgn_num))
        else:
            PartnershipModel.uncancel_partnership(student, partnership)
            time.sleep(0.1)
            return self.redirect('/partner?message=' + MessageModel.partnership_uncancelled())


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
        time.sleep(0.1)
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

        if confirming_key == '':
            confirming_key = 'None'

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
            message     = MessageModel.confirm_partnership([being_confirmed, confirming], admin, confirming)
            partnership = PartnershipModel.create_partnership([being_confirmed, confirming], for_assign)

        # set invitations between invitor and invitee (for current assignment) to inactive
        if partnership:
            InvitationModel.deactivate_invitations_for_students_and_assign(confirming, being_confirmed, for_assign)
            # SendMail(partnership, 'partner_confirm')

        if not admin:
            time.sleep(0.1)
            return self.redirect('/partner?message=' + message)
        else:
            time.sleep(0.1)
            return self.redirect('/admin/partners/add?message=' + message)


class DeclineInvitation(BaseHandler):

    @login_required
    def get(self):
        invitation = ndb.Key(urlsafe=self.request.get('confirmed')).get()
        InvitationModel.update_invitation_status(invitation.key, active=False)
        message = MessageModel.invitation_declined()
        time.sleep(0.1)
        return self.redirect('/partner?message=' + message)


class SelectPartner(BaseHandler):
    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()

        user     = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())
        selector = StudentModel.get_student_by_email(quarter, year, user.email())

        selectees          = StudentModel.get_students_by_lab(quarter, year, selector.lab)

        active_assigns = AssignmentModel.get_active_assigns(quarter, year)

        # get course config
        repeat = SettingModel.repeat_partners()
        cross_section = SettingModel.cross_section_partners()

        # get default parameter
        default_assgn = int(self.request.get("assgn")) if self.request.get("assgn") is not "" else -1

        # get all current_partnerships for partnership status
        partnerships = PartnershipModel.get_all_partnerships_for_assign(quarter, year, default_assgn)
        partner_history = PartnershipModel.get_all_partner_history_for_student(student, quarter, year)
        members      = []
        for p in partner_history:
            if p.active:
                members += p.members
        for p in partnerships:
            if p.members not in members:
                members += p.members

        # build dict to store information about partnership status
        available = []
        for s in selectees:
            if (s.key not in members) or repeat:
                available.append((s.ucinetid,(s.key in partnerships, s)))
        available = sorted(available, key=get_result_priority)
        av_list = []
        for av in available:
            av_list.append((av[0],get_shared_hours(selector.availability, av[1][1].availability)))
        # get error message, if any
        e = self.request.get('error')
        # check to see if partner selection period has closed
        selection_closed = len(active_assigns) == 0
        template_values = {
            'error': e,
            'selector': selector,
            'selectees': available,
            'selection_closed': selection_closed,
            'assgn': default_assgn,
            'active': active_assigns,
            'default_assgn': default_assgn,
            'repeat': repeat,
            'cross_section': cross_section,
            'availability_list': av_list,
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
            time.sleep(0.1)
        except ValueError:
            return self.redirect('/partner/selection?error=You must choose an assignment number')

        # redirect with errors...
        if PartnershipModel.were_partners_previously([selector, selected]) and not SettingModel.repeat_partners():
            return self.redirect('/partner?message=' + MessageModel.worked_previously(selected))
        elif InvitationModel.have_open_invitations(selector, selected, selected_assign):
            return self.redirect('/partner?message=' + MessageModel.have_open_invitations(selected))
        elif PartnershipModel.student_has_partner_for_assign(selector, selected_assign):
            return self.redirect('/partner?message=' + MessageModel.already_has_partner(False, False))
        else:
            InvitationModel.create_invitation(selector, selected, selected_assign)
            return self.redirect('/partner?message=' + MessageModel.sent_invitation(selected))

def get_shared_hours(a1, a2):
    """Takes two availabilities (as strings of 0 and 1), and returns the number of hours in the overlap"""
    return 0
    total = 0
    for i in range(len(a1)):
        if a1[i]=="1" and a2[i] == "1":
            total += 1
    return total/2.0

def get_result_priority(result):
    """This function returns a priority associated with matches in partner selection,
        so that for example, people of the same programming are matched together
    """
    return 0
    student = result[1][1]
    quarter  = SettingModel.quarter()
    year     = SettingModel.year()
    user     = users.get_current_user()
    selector = StudentModel.get_student_by_email(quarter, year, user.email())

    #This used to take into account how many available hours in common the students
    #had. There was a when-to-meet like availablity selector available on the student
    #profiles that enabled this, but the system was unreliable and so we replaced it
    #with simple open response string availablity until we could iron out the issues.
    their_availability = student.availability
    my_availability = selector.availability
    shared_hours = get_shared_hours(my_availability, their_availability)
    
    ability_dif = abs(int(student.programming_ability[0])-int(selector.programming_ability[0]))

    return (shared_hours<4)*10+(ability_dif + 1 - float(shared_hours)/(5*15))
