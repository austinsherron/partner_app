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

from admin import AddAssignment, AddStudent, ClearDB, MainAdmin, ManageAssignments, UploadRoster, ViewRoster, DeactivateStudents
from admin import AddPartnership, EditAssignment, EditStudent, ViewEvals, ViewPartnerships, UpdateSettings, ViewStudent
from handler import CustomHandler
from helpers.helpers import query_to_dict, split_last
from models import Assignment, Student, Instructor, Invitation, Partnership, Evaluation, Setting


################################################################################
################################################################################
################################################################################


################################################################################
## LOAD JINJA ##################################################################
################################################################################


JINJA_ENV = jinja2.Environment(
	loader = jinja2.FileSystemLoader(os.path.dirname(__file__)),
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
			'selector': selector,  								# ...student object
			'selectees': selectees,								# ...query of student objects
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
			'student': student, 			# ...a student object
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
			invitations += self.all_invites_for_pair(confirming, being_confirmed)
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

		# decativate active evals
		for eval in active_evals:
			eval.active = False
			eval.put()

		dropped = self.dropped_partners(open_partnerships, confirming, being_confirmed)
		msg = "Hello,\n\nThis is an automated message sent to inform you that"
		msg += " your partner for assignment " + str(for_assign)
		msg += " has dissolved your partnership by confirming a partnership with another student."
		msg += "\n\nIf this is an error, please contact your former partner."
		msg += "\n\nIf you can't find a partner, please contact your TA."

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
		# get current user...
		user = users.get_current_user()
		# ...and try to find him/her in the DB
		student = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())

		if not student:
			# redirect to main page if the student doesn't exist in the DB
			return self.redirect('/partner')

		programming_ability = ['0: Never, or just a few times', '1: Occaisionally, but not regularly']
		programming_ability += ['2: Regularly, but without much comfort or expertise']
		programming_ability += ['3: Regularly, with comfortable proficiency', '4: Frequently and with some expertise']

		template_values = {
			'user': user,
			'sign_out': users.create_logout_url('/'),
			'student': student,
			'programming_ability': programming_ability,
			'key': student.key.urlsafe(),
		}
		return self.response.write(template.render(template_values))


	def post(self):
		# get current user...
		user = users.get_current_user()
		# ...and try to find him/her in the DB
		student = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())

		# grab form value of preferred name (will be the same if student didn't enter anything)
		student.preferred_name = self.request.get('preferred_name').strip()
		# grab form value of bio...
		bio = self.request.get('bio').strip()
		# ...and save it if the student entered anything
		student.bio = bio if bio != '' else student.bio
		# grab form value of availability...
		availability = self.request.get('availability').strip()
		# ...and save it if the student entered anything
		student.availability = availability if availability != '' else student.availability
		# grab form value of programming ability...
		programming_ability = self.request.get('programming_ability')
		# ...and save it
		student.programming_ability = programming_ability
		# grab form value of avatar pic...
		avatar = str(self.request.get('avatar'))
		# ...and resize/save it if it exists
		student.avatar = images.resize(avatar, 320, 320) if avatar != '' else student.avatar
		# get phone number from for...
		phone_number = self.request.get('phone_number')
		# ...and save it if it isn't the default (000-000-0000)
		student.phone_number = phone_number if phone_number != '000-000-0000' else student.phone_number
		# save updated student object
		student.put()
		# redirect to main page
		return self.redirect('/partner/edit/profile')


class EvaluatePartner(CustomHandler):
	@login_required
	def get(self):
		quarter = Setting.query().get().quarter
		year = Setting.query().get().year

		# get user
		user = users.get_current_user()
		# get student from user info
		evaluator = self.get_student(quarter, year, user.email())
		# get student's partner history
		partners = self.partner_history(evaluator, quarter, year)
		# grab the active eval assignments
		eval_assigns = self.active_eval_assigns(quarter, year)
		# grab partners for eval assignments
		partners = [(eval_assign.number,self.current_partner(evaluator, partners, eval_assign.number)) for eval_assign in eval_assigns]
		# filter out No Partner partnerships
		partners = list(filter(lambda x: x[1] != "No Partner" and x[1] != None, partners))
		eval_closed = len(eval_assigns) == 0
	
		rate20scale = ["0 -- Never, completely inadequate", "1", "2", "3", "4"]
		rate20scale += ["5 -- Seldom, poor quality", "6", "7", "8", "9"]
		rate20scale += ["10 -- About half the time, average", "11", "12", "13", "14"]
		rate20scale += ["15 -- Most of the time, good quality", "16", "17", "18", "19"]
		rate20scale += ["20 -- Always, excellent"]

		rate5scale = ['1 - My partner was much more capable than I was']
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
		quarter = Setting.query().get().quarter
		year = Setting.query().get().year

		user = users.get_current_user()
		evaluator = self.get_student(quarter, year, user.email())
		partners = self.partner_history(evaluator, quarter, year)
		print(self.request.get('evaluatee'))
		eval_key,num = split_last(self.request.get('evaluatee'))
		eval_assign = int(num)
		current_partner = ndb.Key(urlsafe=eval_key).get()

		evaluations = self.existing_eval(evaluator, current_partner, eval_assign)

		for eval in evaluations:
			eval.active = False
			eval.put()

		evaluation = Evaluation(evaluator = evaluator.key, evaluatee = current_partner.key)

		evaluation.assignment_number = eval_assign
		evaluation.year = evaluator.year
		evaluation.quarter = evaluator.quarter
		evaluation.active = True
		evaluation.responses.append(self.request.get('q1'))
		evaluation.responses.append(self.request.get('q2'))
		evaluation.responses.append(self.request.get('q3'))
		evaluation.responses.append(self.request.get('q4'))
		evaluation.responses.append(self.request.get('q5'))
		evaluation.responses.append(self.request.get('q6'))
		evaluation.responses.append(self.request.get('q7'))
		evaluation.responses.append(self.request.get('q8'))
		evaluation.responses.append(self.request.get('q9'))
		evaluation.responses.append(self.request.get('q10'))

		evaluation.put()

		message = 'Evaluation for ' + str(current_partner.last_name) + ', '
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
		template = JINJA_ENV.get_template('/templates/app_is_down.html')
		# get current user
		user = users.get_current_user()
		student = None

		try:
			quarter = Setting.query().get().quarter
			year = Setting.query().get().year
			# use user info to find student int DB
			student = self.get_student(quarter, year, user.email())
			# get active assignments
			active_assigns = sorted(self.active_assigns(quarter, year), key=lambda x: x.number)
			# get active eval assigns
			eval_assigns = sorted(self.active_eval_assigns(quarter, year), key=lambda x: x.number)
			# find any active invitations for the current assignment that student has sent
			sent_invitations = self.sent_invites_mult_assign(student, [x.number for x in active_assigns])
			# find any active invitations for the current assignment that the student has received
			received_invitations = self.received_invites_mult_assign(student, [x.number for x in active_assigns])
			# find any partnerships in which the student has been involved
			partners = self.partner_history(student, quarter, year)
			partners = dict([(x.number,self.current_partner(student, partners, x.number)) for x in active_assigns])
			# find evals the student has submitted
			evals = self.get_eval_history(student, True, quarter, year)
			evals = dict([(x.assignment_number,x) for x in evals])
			# get activity message, if any
			message = self.request.get('message')
			dropped = []
			for x in active_assigns:
				dropped += self.inactive_partners(student, x.number).fetch()
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
			'student': student, 							# ...student object
			'active': active_assigns,
			'evals': eval_assigns,
			'submitted_evals': evals,
			'sent_invitations': sorted(sent_invitations, key=lambda x: x.assignment_number),	# ...list of invitation objects
			'received_invitations': sorted(received_invitations.items(), key=lambda x: x[0]),	# ...list of invitation objects
			'partners': partners,							# ...dict of partnership objects
			'sign_out': users.create_logout_url('/'),		# sign out url
			'message': message,
			'profile': student.bio is None or student.availability is None or student.programming_ability is None,
			'dropped': dropped,
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
		quarter = Setting.query().get().quarter
		year = Setting.query().get().year

		# get current user info
		user = users.get_current_user()
		# use user info to find student in DB (the selector)
		selector = self.get_student(quarter, year, user.email())
		# if cross section partnership aren't allowed, use selector info to find students in same lab section
		if not self.cross_section_partners():
			selectees = self.students_by_lab(quarter, year, selector.lab)
		else:
			selectees = self.get_active_students(quarter, year)				
		# get active assignments
		active_assigns = self.active_assigns(quarter, year)
		# get error message, if any
		e = self.request.get('error')		
		# check to see if partner selection period has closed
		selection_closed = len(active_assigns) == 0

		# pass template values...
		template_values = {
			'error': e,
			'selector': selector,  								# ...student object
			'selectees': selectees.order(Student.last_name),	# ...query of student objects
			'selection_closed': selection_closed,
			'active': active_assigns,
		}
		template = JINJA_ENV.get_template('/templates/partner_selection.html')
		self.response.write(template.render(template_values))


	def post(self):
		quarter = Setting.query().get().quarter
		year = Setting.query().get().year

		# get current user info
		user = users.get_current_user()
		# use user info to find student in DB (the selector)
		selector = self.get_student(quarter, year, user.email())
		# use form data to find student that was selected (selected) 
		selected = self.student_by_id(quarter, year, self.request.get('selected_partner'))
		# use from data to get assignment for which student is choosing partner
		selected_assign = int(self.request.get('selected_assign'))
		# check if selector and selected have been partners
		previous_partners = self.partners_previously(selector, selected)
		# check if selector has and selected have open inviations for current assignment
		current_invitations = self.open_invitations(selector, selected, selected_assign).fetch()

		# redirect with error...
		# ...if selected and selector have worked together previously
		if previous_partners and not self.repeat_partners():
			e = 'Sorry, you\'ve already worked with, or are currently working with '
			e += str(selected.last_name) + ', ' + str(selected.first_name)
			e += '. If you think you have a legitimate reason to repeat a partnership'
			e += ', please contact your TA'
			return self.redirect('/partner/selection?error=' + e)
		# ... or if selected and selector have open invitations for the current assignment
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
		# grab current user 
		user = users.get_current_user()
		# use user info to find student in DB 
		student = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())
	
		# redirect to main page if student doesn't exist
		if not student:
			return self.redirect('/partner')

		# grab all invites (including inactive ones)
		invites = self.invitation_history(student).order(Invitation.assignment_number).fetch()
		current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)

		# if there are no assignments for this quarter, render early to avoid errors
		if not current_assignment:
			return self.response.write(template.render({'user': user, 'sign_out': users.create_logout_url('/')}))

		partners = self.partner_history(student, Setting.query().get().quarter, Setting.query().get().year)
		# grab current partner for reporting 
		current_partner = self.current_partner(student, partners, current_assignment.number)

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
			quarter = self.quarter()
			year = self.year()
			student = self.get_student(quarter, year, user.email())
			assign_range = self.assign_range(quarter, year)
			partner_history = self.partner_history(student, quarter, year, fill_gaps=assign_range)
			all_partner_history = self.all_partner_history(student, quarter, year)
			evals = self.get_eval_history(student, True, quarter, year).fetch()
			evals += self.get_eval_history(student, False, quarter, year).fetch()
			evals = sorted(evals, key=lambda x: x.assignment_number)

		except AttributeError:
			self.redirect('/partner')
			return

		template = JINJA_ENV.get_template('/templates/partner_student_view.html')
		template_values = {
			'student': student,
			'partners': partner_history,
			'all_partners': all_partner_history,
			'assign_range': assign_range,
			'evals': evals,
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
		}
		return self.response.write(template.render(template_values))


################################################################################
################################################################################
################################################################################


################################################################################
## CONFIGURE AND START APP #####################################################
################################################################################


config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'some-secret-key',
}

application = webapp2.WSGIApplication([
	('/', Main),
	('/partner', MainPage),
	('/partner/edit/profile', EditProfile),
	('/partner/evaluation', EvaluatePartner),
	('/partner/selection', SelectPartner),
	('/partner/browse', BrowseForPartners),
	('/partner/confirm', ConfirmPartner),
	('/partner/history', ViewHistory),
	('/partner/history/invitations', ViewInvitationHistory),
	('/partner/instructions', HelpPage),
	('/images/(.*)', ImageHandler),
	('/admin', MainAdmin),
	('/admin/assignment/add', AddAssignment),
	('/admin/assignment/edit', EditAssignment),
	('/admin/assignment/view', ManageAssignments),
	('/admin/cleardb', ClearDB),
	('/admin/evaluations/view', ViewEvals),
	('/admin/partners/add', AddPartnership),
	('/admin/partners/view', ViewPartnerships),
	('/admin/roster/upload', UploadRoster),
	('/admin/roster/view', ViewRoster),
	('/admin/student/add', AddStudent),
	('/admin/students/deactivate', DeactivateStudents),
	('/admin/student/edit', EditStudent),
	('/admin/student/view', ViewStudent),
	('/admin/settings/update', UpdateSettings),
], config=config, debug=True)


################################################################################
################################################################################
################################################################################
