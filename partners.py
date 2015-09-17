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
from webapp2_extras.appengine.users import login_required

from admin import AddAssignment, AddStudent, ClearDB, MainAdmin, ManageAssignments, UploadRoster, ViewRoster, DeactivateStudents
from admin import AddPartnership, EditAssignment, EditStudent, ViewEvals, ViewPartnerships, UpdateSettings
from handler import CustomHandler
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
		selection_closed = (datetime.now() - timedelta(hours=7) > current_assignment.close_date)
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
		# get current user
		user = users.get_current_user() 
		# use user info to find student in DB (the invitee)
		student = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())
		# find the current assignment
		current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)
		# find open invitations for current assignment
		invitations = self.received_invites(student, current_assignment.number)
		# check to see if partner selection is still active
		selection_closed = (datetime.now() - timedelta(hours=7) > current_assignment.close_date)
		# pass template values...
		template_values = {
			'student': student, 			# ...a student object
			'selection_closed': selection_closed,
			'current': current_assignment,
			'invitations': invitations		# ...and a query object of invitation objects
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
			# use user info to find student in DB (the invitee)
			confirming = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())
			# find student being confirmed (the invitor)
			being_confirmed = self.student_by_id(Setting.query().get().quarter, Setting.query().get().year, self.request.get('confirmed'))
			admin = False
		else:
			being_confirmed = ndb.Key(urlsafe=being_confirmed_key).get()
			confirming = ndb.Key(urlsafe=confirming_key).get() if confirming_key != 'None' else None
			admin = True

		# find current assignment
		current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)
		# find all open invitation involving both the student being confirmed and the student confirming
		# invitations = self.all_invitations(confirming, being_confirmed, current_assignment.number)
		if confirming:
			invitations = self.all_invites_for_student(confirming, current_assignment.number)
			invitations += self.all_invites_for_student(being_confirmed, current_assignment.number)
			open_partnerships = self.students_partners_for_assign(confirming, quarter, year, current_assignment.number).fetch()
			open_partnerships += self.students_partners_for_assign(being_confirmed, quarter, year, current_assignment.number).fetch()
		else:
			invitations = self.all_invites_for_student(being_confirmed, current_assignment.number)
			open_partnerships = self.students_partners_for_assign(being_confirmed, quarter, year, current_assignment.number).fetch()

		# find any active partnerships for confirming student and the student  being confirmed
		# open_partnerships = self.open_partnerships(confirming, being_confirmed, current_assignment.number)

		# deactivate those partnerships
		for partnership in open_partnerships:
			partnership.active = False
			partnership.put()

		dropped = self.dropped_partners(open_partnerships, confirming, being_confirmed)
		msg = "Hello,\n\nThis is an automated message send to inform you that"
		msg += " your partner for assignment " + str(current_assignment.number)
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
			assignment_number = current_assignment.number, active = True,
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
			return self.redirect('/admin?message=' + message)
			


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

		programming_ability = ['0 - A What Loop?']
		programming_ability += [str(i) for i in range(1, 5)]
		programming_ability += ['5 - I know my way around a keyboard']
		programming_ability += [str(i) for i in range(6, 10)]
		programming_ability += ['10 - I\'m actually teaching this class']

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
		user = users.get_current_user()
		evaluator = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())
		partners = self.partner_history(evaluator, Setting.query().get().quarter, Setting.query().get().year)
		current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)
		eval_assign = self.current_eval_assign(Setting.query().get().quarter, Setting.query().get().year)
		current_partner = self.current_partner(evaluator, partners, eval_assign.number)

		eval_closed = (datetime.now() - timedelta(hours=7) > eval_assign.eval_date or
			datetime.now() - timedelta(hours=7) < eval_assign.eval_open_date)
	
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
			'current_partner': current_partner,
			'eval': eval_assign,
			'current': current_assignment
		}
		template = JINJA_ENV.get_template('/templates/partner_eval.html')
		self.response.write(template.render(template_values))


	def post(self):
		user = users.get_current_user()
		evaluator = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())
		partners = self.partner_history(evaluator, Setting.query().get().quarter, Setting.query().get().year)
		current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)
		eval_assign = self.current_eval_assign(Setting.query().get().quarter, Setting.query().get().year)
		current_partner = self.current_partner(evaluator, partners, eval_assign.number)

		evaluations = self.existing_eval(evaluator, current_partner, eval_assign.number)

		for eval in evaluations:
			eval.active = False
			eval.put()

		evaluation = Evaluation(evaluator = evaluator.key, evaluatee = current_partner.key)

		evaluation.assignment_number = eval_assign.number
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
		template = JINJA_ENV.get_template('/templates/partners.html')
		# get current user
		user = users.get_current_user()
		student = None

		try:
			# use user info to find student int DB
			student = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())
			# find current assignment
			current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)
			# find assignment for which evals will be completed next
			eval_assign = self.current_eval_assign(Setting.query().get().quarter, Setting.query().get().year)
			# find any active invitations for the current assignment that student has sent
			sent_invitations = self.sent_invites(student, current_assignment.number)

		except (AttributeError, IndexError):
			template_values = {
				'user': user,
				'student': student,
				'sign_out': users.create_logout_url('/'),
				'email': user.email()
			}
			return self.response.write(template.render(template_values))

		# find any active invitations for the current assignment that the student has received
		received_invitations = self.received_invites(student, current_assignment.number)
		# find any partnerships in which the student has been involved
		partners = self.partner_history(student, Setting.query().get().quarter, Setting.query().get().year)
		# find current partner
		current_partner = self.current_partner(student, partners, current_assignment.number)
		# find most recently dropped partner, if any
		dropped_partners = self.inactive_partners(student, current_assignment.number).fetch()
		# get activity message, if any
		message = self.request.get('message')
		
		# pass template values...
		template_values = {
			'user': user,
			'student': student, 			# ...student object
			'current': current_assignment,	# ...assignment object
			'eval': eval_assign,			# ...assignment object
			# ...query object full of invitation objects
			'sent_invitations': sent_invitations if len(sent_invitations.fetch()) > 0 else None,
			# ...query object full of invitation objects
			'received_invitations': received_invitations if len(received_invitations.fetch()) > 0 else None,
			'current_partner': current_partner,		# ...student object or string
			# ...query object full of partnership objects
			'partners': partners,
			# ...sign out url
			'sign_out': users.create_logout_url('/'),
			'dropped': dropped_partners,
			'message': message,
			'days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
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
		# get current user info
		user = users.get_current_user()
		# use user info to find student in DB (the selector)
		selector = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())
		# if cross section partnership aren't allowed, use selector info to find students in same lab section
		if not self.cross_section_partners():
			selectees = self.students_by_lab(Setting.query().get().quarter, Setting.query().get().year, selector.lab)
		else:
			selectees = self.get_active_students(Setting.query().get().quarter, Setting.query().get().year)				
		# get current assignment
		current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)
		# get error message, if any
		e = self.request.get('error')		
		# check to see if partner selection period has closed
		selection_closed = (datetime.now() - timedelta(hours=7) > current_assignment.close_date)

		# pass template values...
		template_values = {
			'error': e,
			'selector': selector,  								# ...student object
			'selectees': selectees.order(Student.last_name),	# ...query of student objects
			'selection_closed': selection_closed,
			'current': current_assignment
		}
		template = JINJA_ENV.get_template('/templates/partner_selection.html')
		self.response.write(template.render(template_values))


	def post(self):
		# get current user info
		user = users.get_current_user()
		# use user info to find student in DB (the selector)
		selector = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())
		# use form data to find student that was selected (selected) 
		selected = self.student_by_id(Setting.query().get().quarter, Setting.query().get().year, self.request.get('selected_partner'))
		# find current assignment
		current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)
		# check if selector and selected have been partners
		previous_partners = self.partners_previously(selector, selected)
		# check if selector has and selected have open inviations for current assignment
		current_invitations = self.open_invitations(selector, selected, current_assignment.number).fetch()

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
				assignment_number = current_assignment.number, active = True)
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
			i = (invite.created - timedelta(hours=7)).strftime('%m-%d-%Y %H:%M:%S')
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
			quarter = Setting.query().get().quarter
			year = Setting.query().get().year
			student = self.get_student(Setting.query().get().quarter, Setting.query().get().year, user.email())
			current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)
			partners = self.partner_history(student, Setting.query().get().quarter, Setting.query().get().year)
			evaluations = self.get_eval_history(student, True, Setting.query().get().quarter, Setting.query().get().year,
				).order(Evaluation.assignment_number)
			last_num = self.get_assign_n(quarter, year, -1)
			last_num = last_num.number if last_num else current_assignment.number

		except AttributeError:
			self.redirect('/partner')
			return

		template = JINJA_ENV.get_template('templates/partner_history.html')
		template_values = {
			'user': user,
			'student': student,
			'partners': partners,
			'evals': evaluations,
			'sign_out': users.create_logout_url('/'),
			'last_num': last_num,
		}
		return self.response.write(template.render(template_values))


################################################################################
################################################################################
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
	('/admin/timing/update', UpdateSettings),
], config=config, debug=True)
