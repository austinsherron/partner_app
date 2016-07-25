################################################################################
## IMPORTS #####################################################################
################################################################################


import cgi
import jinja2
import os
import webapp2

from datetime import date, datetime, timedelta
from google.appengine.api import images, users
from google.appengine.ext import ndb
from json import dumps
from webapp2_extras.appengine.users import login_required

from handler import CustomHandler
from models import Student, Invitation, Partnership, Evaluation, Setting
from src.helpers.helpers import query_to_dict, split_last
from src.models.assignment import AssignmentModel
from src.models.eval import EvalModel
from src.models.invitation import InvitationModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel
from src.send_mail import SendMail 


################################################################################
################################################################################
################################################################################


################################################################################
## LOAD JINJA ##################################################################
################################################################################


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


################################################################################
################################################################################
################################################################################


################################################################################
## HANDLERS ####################################################################
################################################################################


class BrowseForPartners(CustomHandler):

    @login_required
    def get(self):
        # get current user info
        user = users.get_current_user()
        # get current quarter/year
        quarter,year = Setting.query().get().quarter, Setting.query().get().year
        # use user info to find student in DB (the selector)
        selector = self.get_student(quarter, year, user.email())
        if not selector:
            return self.redirect('/partner')
        # use selector info to find students in same lab section
        selectees = self.students_by_lab(quarter, year, selector.lab)
        # get current assignment
        current_assignment = self.current_assign(quarter, year)
        # if there are no assignments for this quarter, redirect to avoid errors
        if not current_assignment:
            return self.redirect('/partner?message=There are no assignments open for partner selection.')
            
        # get error message, if any
        e = self.request.get('error')        
        # check to see if partner selection period has closed
        selection_closed = (datetime.now() - timedelta(hours=8) > current_assignment.close_date)
        # get all current_partnerships for partnership status
        partnerships = self.all_partners_for_assign(quarter, year, current_assignment.number)
        partnerships = {p.initiator for p in partnerships} | {p.acceptor for p in partnerships}
        # build dict to store information about partnership status
        selectees = sorted({s.ucinetid: (s.key in partnerships,s) for s in selectees}.items(), key=lambda x: x[1][1].last_name)

        # pass template values...
        template_values = {
            'error': e,
            'selector': selector,                                  # ...student object
            'selectees': selectees,                                # ...query of student objects
            'selection_closed': selection_closed,
            'current': current_assignment,
            'user': user,
            'sign_out': users.create_logout_url('/'),
        }
        template = JINJA_ENV.get_template('/templates/partner_browse.html')
        self.response.write(template.render(template_values))


class ConfirmPartner(CustomHandler):
    @login_required
    def get(self):
        quarter = Setting.query().get().quarter
        year = Setting.query().get().year

        # get current user
        user = users.get_current_user() 
        # use user info to find student in DB (the invitee)
        student = self.get_student(quarter, year, user.email())
        # find active assignments
        active_assigns = self.active_assigns(quarter, year)
        # find open invitations for current assignment
        invitations = self.received_invites_mult_assign(student, [x.number for x in active_assigns], as_dict=False)
        #invitations = dict([(num,query_to_dict(*invites)) for num,invites in invitations.items()])
        # check to see if partner selection is still active
        selection_closed = len(active_assigns) == 0
        # pass template values...
        template_values = {
            'student': student,             # ...a student object
            'selection_closed': selection_closed,
            'invitations': invitations,
        }
        template = JINJA_ENV.get_template('/templates/partner_confirm.html')
        self.response.write(template.render(template_values))


    def post(self):
        # get current user
        user = users.get_current_user()

        confirming_key = self.request.get('admin_confirming')
        being_confirmed_key = self.request.get('admin_being_confirmed')

        quarter = Setting.query().get().quarter
        year = Setting.query().get().year

        if not confirming_key or not being_confirmed_key:
            # get invitation
            invitation = ndb.Key(urlsafe=self.request.get('confirmed')).get()
            # use user info to find student in DB (the invitee)
            confirming = self.get_student(quarter, year, user.email())
            # find student being confirmed (the invitor)
            being_confirmed = invitation.invitor.get()
            # get assign
            for_assign = invitation.assignment_number
            admin = False
        else:
            for_assign = int(self.request.get('assign_num'))
            being_confirmed = ndb.Key(urlsafe=being_confirmed_key).get()
            confirming = ndb.Key(urlsafe=confirming_key).get() if confirming_key != 'None' else None
            admin = True

        # find all open invitation involving both the student being confirmed and the student confirming
        # invitations = self.all_invitations(confirming, being_confirmed, current_assignment.number)
        if confirming:
            invitations = self.all_invites_for_student(confirming, for_assign)
            invitations += self.all_invites_for_student(being_confirmed, for_assign)
            open_partnerships = self.students_partners_for_assign(confirming, quarter, year, for_assign).fetch()
            open_partnerships += self.students_partners_for_assign(being_confirmed, quarter, year, for_assign).fetch()
        else:
            invitations = self.all_invites_for_student(being_confirmed, for_assign)
            open_partnerships = self.students_partners_for_assign(being_confirmed, quarter, year, for_assign).fetch()

        # find any active partnerships for confirming student and the student  being confirmed
        # open_partnerships = self.open_partnerships(confirming, being_confirmed, current_assignment.number)

        # deactivate those partnerships
        active_evals = []
        for partnership in open_partnerships:

            # find any active evals
            if partnership.initiator:
                active_evals += self.student_eval_for_assign(partnership.initiator, for_assign)
            if partnership.acceptor:
                active_evals += self.student_eval_for_assign(partnership.acceptor, for_assign)

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
            


class EditProfile(CustomHandler):

    @login_required
    def get(self):
        template = JINJA_ENV.get_template('/templates/partner_update_profile.html')

        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())

        if not student:
            # redirect to main page if the student doesn't exist in the DB
            return self.redirect('/partner')

        programming_ability  = ['0: Never, or just a few times', '1: Occaisionally, but not regularly']
        programming_ability += ['2: Regularly, but without much comfort or expertise']
        programming_ability += ['3: Regularly, with comfortable proficiency', '4: Frequently and with some expertise']

        template_values = {
            'user':                user,
            'sign_out':            users.create_logout_url('/'),
            'student':             student,
            'programming_ability': programming_ability,
            'key':                 student.key.urlsafe(),
        }
        return self.response.write(template.render(template_values))


    def post(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()
        student = StudentModel.get_student_by_email(quarter, year, user.email())

        student.preferred_name      = self.request.get('preferred_name').strip()
        bio                         = self.request.get('bio').strip()
        student.bio                 = bio if bio != '' else student.bio         
        availability                = self.request.get('availability').strip()
        student.availability        = availability if availability != '' else student.availability 
        programming_ability         = self.request.get('programming_ability')
        student.programming_ability = programming_ability

        # grab image and resize if necessary
        avatar         = str(self.request.get('avatar'))
        student.avatar = images.resize(avatar, 320, 320) if avatar != '' else student.avatar

        phone_number         = self.request.get('phone_number')
        student.phone_number = phone_number if phone_number != '000-000-0000' else student.phone_number
        student.put()

        # redirect to main page
        return self.redirect('/partner/edit/profile')


class EvaluatePartner(CustomHandler):
    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()

        # get user
        user = users.get_current_user()
        # get student from user info
        evaluator = StudentModel.get_student_by_email(quarter, year, user.email())
        # get student's partner history
        partners = PartnershipModel.get_active_partner_history_for_student(evaluator, quarter, year)
        # grab the active eval assignments
        eval_assigns = AssignmentModel.get_active_eval_assigns(quarter, year)
        # grab partners for eval assignments
        partners = [(eval_assign.number,PartnershipModel.get_partner_from_partner_history_by_assign(evaluator, partners, eval_assign.number)) for eval_assign in eval_assigns]
        # filter out No Partner partnerships
        partners = list(filter(lambda x: x[1] != "No Partner" and x[1] != None, partners))
        eval_closed = len(eval_assigns) == 0
    
        rate20scale  = ["0 -- Never, completely inadequate", "1", "2", "3", "4"]
        rate20scale += ["5 -- Seldom, poor quality", "6", "7", "8", "9"]
        rate20scale += ["10 -- About half the time, average", "11", "12", "13", "14"]
        rate20scale += ["15 -- Most of the time, good quality", "16", "17", "18", "19"]
        rate20scale += ["20 -- Always, excellent"]

        rate5scale  = ['1 - My partner was much more capable than I was']
        rate5scale += ['2 - My partner was a little more capable than I was']
        rate5scale += ['3 - We were about evenly matched, on average']
        rate5scale += ['4 - I was a little more capable than my partner']
        rate5scale += ['5 - I was a lot more capable than my partner']

        rate10scale = [str(x / 10.0) for x in range(0, 105, 5)]

        template_values = {
            'eval_closed': eval_closed,
            'rate_scale': rate20scale,
            'rate5scale': rate5scale,
            'rate10scale': rate10scale,
            'partners': partners,
        }
        template = JINJA_ENV.get_template('/templates/partner_eval.html')
        self.response.write(template.render(template_values))


    def post(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()

        evaluator       = StudentModel.get_student_by_email(quarter, year, user.email())
        partners        = PartnershipModel.get_active_partner_history_for_student(evaluator, quarter, year)
        eval_key,num    = split_last(self.request.get('evaluatee'))
        eval_assign     = int(num)
        current_partner = ndb.Key(urlsafe=eval_key).get()

        evaluations = EvalModel.get_existing_eval_by_assign(evaluator, current_partner, eval_assign)
        for eval in evaluations:
            eval.active = False
            eval.put()

        evaluation                   = Evaluation(evaluator = evaluator.key, evaluatee = current_partner.key)
        evaluation.assignment_number = eval_assign
        evaluation.year              = evaluator.year
        evaluation.quarter           = evaluator.quarter
        evaluation.active            = True
        for i in range(1, 11):
            evaluation.responses.append(self.request.get('q' + str(i)))
        evaluation.put()

        message  = 'Evaluation for ' + str(current_partner.last_name) + ', '
        message += str(current_partner.first_name) + ' successfully submitted'

        self.redirect('/partner?message=' + message)


class HelpPage(CustomHandler):
    def get(self):
        user = users.get_current_user()
        template_values = {}

        if user:
            template_values['user'] = user.email()
            template_values['sign_out'] = users.create_logout_url('/')
        else:
            template_values['sign_in'] = users.create_login_url('/partner')

        template = JINJA_ENV.get_template('/templates/partner_instructions.html')
        self.response.write(template.render(template_values))


class ImageHandler(CustomHandler):

    def get(self, key):
        # cast key from url from str to ndb.Key
        key = ndb.Key(urlsafe=key)
        # grab student associated w/ key and the corresponding avatar
        image = key.get().avatar 
        # set content type header...
        self.response.headers['Content-Type'] = 'image/png'
        # and 
        return self.response.out.write(image)


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
            partners = dict([(x.number,self.current_partner(student, partners, x.number)) for x in active_assigns])
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


class ViewInvitationHistory(CustomHandler):

    @login_required
    def get(self):
        template = JINJA_ENV.get_template('/templates/partner_invitation_history.html')
        quarter  = SettingModel.quarter()
        year     = SettingModel.year()
        # grab current user 
        user = users.get_current_user()
        # use user info to find student in DB 
        student = StudentModel.get_student_by_email(quarter, year, user.email())
    
        # redirect to main page if student doesn't exist
        if not student:
            return self.redirect('/partner')

        # grab all invites (including inactive ones)
        invites = InvitationModel.get_all_invitations_involving_student(student).order(Invitation.assignment_number).fetch()
        current_assignment = AssignmentModel.get_active_assign_with_latest_fade_in_date(quarter, year)

        # if there are no assignments for this quarter, render early to avoid errors
        if not current_assignment:
            return self.response.write(template.render({'user': user, 'sign_out': users.create_logout_url('/')}))

        partners = PartnershipModel.get_active_partner_history_for_student(student, quarter, year)
        # grab current partner for reporting 
        current_partner = PartnershipModel.get_partner_from_partner_history_by_assign(student, partners, current_assignment.number)

        invite_info = {}
        # dict for custom ordering of invite info fields
        ordering = {'Assign Num': 0, 'Who': 1, 'To/From': 2, 'Accepted': 3, 'Current Partner': 4}
        for invite in invites:
            # organize invite info by time 
            i = (invite.created - timedelta(hours=8)).strftime('%m-%d-%Y %H:%M:%S')
            invite_info[i] = {}
            # add assignment number to invite info
            invite_info[i]['Assign Num'] = invite.assignment_number
            # determine wheather invite was sent or received in relation to the user
            invite_info[i]['To/From'] = 'Sent' if invite.invitor == student.key else 'Received'
            who_key = invite.invitee if invite_info[i]['To/From'] == 'Sent' else invite.invitor
            who = who_key.get()
            # add invitor/invitee (depending on 'Sent'/'Received') to invite info
            invite_info[i]['Who'] = str(who.last_name) + ', ' + str(who.first_name) + ' - ' + str(who.ucinetid)
            # add invite acceptance information to the invite info
            invite_info[i]['Accepted'] = str(invite.accepted)
            # add info regarding partner in relation to this invite (was this invite from your current partner?)
            # NOTE: this field will be set to 'True' for any invitations from this partner that were previously accepted
            invite_info[i]['Current Partner'] = str(who == current_partner and invite.accepted)
            invite_info[i] = sorted(invite_info[i].items(), key=lambda x: ordering[x[0]])

        template_values = {
            'invites': sorted(invite_info.items(), reverse=True),
            'fields': sorted(ordering.items(), key=lambda x: x[1]),
            'user': user,
            'sign_out': users.create_logout_url('/'),
        }
        return self.response.write(template.render(template_values))


class ViewHistory(CustomHandler):
    @login_required
    def get(self):
        user = users.get_current_user()

        try:
            quarter = SettingModel.quarter()
            year    = SettingModel.year()
            student = StudentModel.get_student_by_email(quarter, year, user.email())

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
            'evals':        evals,
            'user':         users.get_current_user(),
            'sign_out':     users.create_logout_url('/'),
        }
        return self.response.write(template.render(template_values))


################################################################################
################################################################################
################################################################################
