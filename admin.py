################################################################################
## IMPORTS #####################################################################
################################################################################


import cgi
import csv
import datetime 
import jinja2
import os
import webapp2

from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import admin_required

from helpers.admin_helpers import make_date
from helpers.helpers import get_sess_val, get_sess_vals
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


class AddAssignment(CustomHandler):

	#@admin_required
	def get(self):
		template = JINJA_ENV.get_template('/templates/admin_add_assignment.html')

		temp = get_sess_vals(self.session, 'quarter', 'year')					# try grabbing quarter/year from session
		if not temp:															# redirect with error if it doesn't exist
			return self.redirect('/admin?message=Please set a current quarter and year')
		quarter,year = temp

		current_assignment = self.current_assign(quarter, year)					# grab current assignment
		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		quarters = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
		template_values = {														# build template value map...
			'year': year,
			'quarter': quarter,
			'quarters': sorted(quarters.items()),
			'current': current_assignment,
			'today': datetime.date.today().strftime("%Y-%m-%d"),
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
		}
		return self.response.write(template.render(template_values))			# ...and render the response


	def post(self):
		# URL will contain 'edit' argument if this request is coming from an assignment edit form
		edit = self.request.get('edit')
		# grab assignment info from URL
		year = int(self.request.get('year'))			
		quarter = int(self.request.get('quarter'))
		number = int(self.request.get('assign_num'))

		# if this request didn't come from the edit form...
		if not edit:
			# ...create new assignment and set PK values
			assignment = Assignment()
			assignment.year = int(self.request.get('year'))
			assignment.quarter = int(self.request.get('quarter'))
			assignment.number = int(self.request.get('assign_num'))
		else:
			# ...else get assignment
			assignment = self.get_assign(quarter, year, number)

		# if an assignment with the same PK values exist, redirect with error; assignment isn't created
		if self.get_assign(assignment.quarter, assignment.year, assignment.number) and not edit:
			message = 'That assignment is already in the database'
			return self.redirect('/admin/assignment/add?message=' + message)
		else:
			# set dates/times
			fade_in_date = str(self.request.get('fade_in_date')).split('-')
			fade_in_time = str(self.request.get('fade_in_time')).split(':')
			assignment.fade_in_date = make_date(fade_in_date, fade_in_time)

			due_date = str(self.request.get('due_date')).split('-')
			due_time = str(self.request.get('due_time')).split(':')
			assignment.due_date = make_date(due_date, due_time)

			close_date = str(self.request.get('close_date')).split('-')
			close_time = str(self.request.get('close_time')).split(':')
			assignment.close_date = make_date(close_date, close_time)

			eval_date = str(self.request.get('eval_date')).split('-')
			eval_time = str(self.request.get('eval_time')).split(':')
			assignment.eval_date = make_date(eval_date, eval_time)

			eval_open_date = str(self.request.get('eval_open_date')).split('-')
			eval_open_time = str(self.request.get('eval_open_time')).split(':')
			assignment.eval_open_date = make_date(eval_open_date, eval_open_time)

			fade_out_date = str(self.request.get('fade_out_date')).split('-')
			fade_out_time = str(self.request.get('fade_out_time')).split(':')
			assignment.fade_out_date = make_date(fade_out_date, fade_out_time)

			# set 'current' value (always false due to query updates)
			assignment.current = False

			# save assignment object
			assignment.put()
	
			message = 'Assignment ' + str(assignment.number) + ' for quarter '
			message += str(assignment.quarter) + ' ' + str(assignment.year) 
			# changed success message depending on whether an assignment was just create/updated
			message += ' successfully ' + ('updated' if edit else 'added')		

			# redirct according to action (add vs edit)
			redirect_link = '/admin/assignment/' + ('view' if edit else 'add') 

			return self.redirect(redirect_link + '?message=' + message)



class AddPartnership(CustomHandler):

	def get(self):
		template = JINJA_ENV.get_template('/templates/admin_add_partnership.html')
		self.response.write(template.render())


	def post(self):
		if self.request.get('form_1'):
			students = Student.query(
				Student.year == int(self.request.get('year')),
				Student.quarter == int(self.request.get('quarter')),
				Student.active == True,
			)

			current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)

			template_values = {
				'students': students.order(Student.last_name),
				'quarter': int(self.request.get('quarter')),
				'year': int(self.request.get('year')),
				'current': current_assignment
			}
			template = JINJA_ENV.get_template('/templates/admin_add_partnership.html')
			self.response.write(template.render(template_values))
		elif self.request.get('form_2'):
		
			initiator = Student.query(
				Student.studentid == int(self.request.get('initiator')),
				Student.year == int(self.request.get('year')),
				Student.quarter == int(self.request.get('quarter')),
			).get()

			if self.request.get('acceptor') != 'None':
				acceptor = Student.query(
					Student.studentid == int(self.request.get('acceptor')),
					Student.year == int(self.request.get('year')),
					Student.quarter == int(self.request.get('quarter')),
				).get()
			else:
				acceptor = None

			assign_num = int(self.request.get('assign_num'))

			if acceptor:
				invitations = Invitation.query(
					ndb.OR(Invitation.invitee == initiator.key, Invitation.invitee == acceptor.key),
					ndb.OR(Invitation.invitor == initiator.key, Invitation.invitor == acceptor.key),
					Invitation.assignment_number == assign_num,
					Invitation.active == True
				)
			else:
				invitations = Invitation.query(
					ndb.OR(Invitation.invitee == initiator.key, Invitation.invitor == initiator.key),
					Invitation.assignment_number == assign_num,
					Invitation.active == True
				)

			if acceptor:
				open_partnerships = Partnership.query(
					ndb.OR(
							ndb.OR(
								Partnership.initiator == initiator.key, 
								Partnership.initiator == acceptor.key),
							ndb.OR(
								Partnership.acceptor == initiator.key,
								Partnership.acceptor == acceptor.key)),
					Partnership.assignment_number == assign_num,
					Partnership.active == True
				)
			else:
				open_partnerships = Partnership.query(
					ndb.OR(Partnership.initiator == initiator.key, Partnership.acceptor == initiator.key),
					Partnership.assignment_number == assign_num,
					Partnership.active == True
				)
			
			# deactivate those partnerships
			for partnership in open_partnerships:
				partnership.active = False
				partnership.put()

			# set invitations between invitor and invitee (for current assignment)
			# to inactive
			for invitation in invitations:
				invitation.active = False
				invitation.put()

			partnership = Partnership(initiator = initiator.key, acceptor = acceptor.key if acceptor else None, 
				assignment_number = assign_num, active = eval(self.request.get('active')),
				year = initiator.year, quarter = initiator.quarter)

			partnership.put()

			message = 'Partnership between ' + initiator.ucinetid + ' and '
			message += (acceptor.ucinetid if acceptor else 'No Partner') + ' added'

			self.redirect('/admin?message=' + message)



class AddStudent(CustomHandler):

	#@admin_required
	def get(self):

		temp = get_sess_vals(self.session, 'quarter', 'year')					# try grabbing quarter/year from session
		if not temp:															# redirect with error if it doesn't exist
			return self.redirect('/admin?message=Please set a current quarter and year')
		quarter,year = temp

		message = self.request.get('message')									# grab message if it exsits

		template_values = {
			'message': message,
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
			'quarter': quarter,
			'year': year,
		}
		template = JINJA_ENV.get_template('/templates/admin_add_student.html')
		return self.response.write(template.render(template_values))


	def post(self):
		student = Student()
		student.studentid = int(self.request.get('studentid').strip())
		student.first_name = self.request.get('first_name').strip().title()	
		student.last_name = self.request.get('last_name').strip().title()
		student.ucinetid = self.request.get('ucinetid').strip().lower()
		student.email = self.request.get('email').strip().lower()
		student.lab = int(self.request.get('lab').strip())
		student.quarter = int(self.request.get('quarter').strip())
		student.year = int(self.request.get('year').strip())
		student.active = True
		
		student.put()

		message = 'Student ' + student.ucinetid + ' has been added'

		self.redirect('/admin/student/add?message=' + message)



class ClearDB(CustomHandler):

	#@admin_required
	def get(self):
		template = JINJA_ENV.get_template('/templates/admin_cleardb.html')
		self.response.write(template.render())


	def post(self):
		if bool(self.request.get('choice')):
			ndb.delete_multi(Student.query().fetch(keys_only=True))
			ndb.delete_multi(Assignment.query().fetch(keys_only=True))

		self.redirect('/admin')


class DeactivateStudents(CustomHandler):

	def post(self):
		quarter = int(self.request.get('quarter'))									# grab quarter from URL
		year = int(self.request.get('year'))										# grab year from URL

		student_ids = [int(sid) for sid in self.request.POST.getall('student')]		# get selected student IDs
		students = []																# init container for students to deactivate
		to_deactivate = self.students_by_ids(quarter, year, student_ids)			# query students to deactivate

		for student in to_deactivate:												# deactivate each student...
			student.active = False
			students.append(student)

		ndb.put_multi(students)														# ...and then save student objects to DB
		
		message = 'Students successfully deactivated'								# create success message
		return self.redirect('/admin/roster/view?message=' + message)				# render the response


class EditAssignment(CustomHandler):

	def get(self):
		quarter = int(self.request.get('quarter'))						# grab quarter, year, and assign num from URL
		year = int(self.request.get('year'))						
		number = int(self.request.get('number'))
		assignment = self.get_assign(quarter, year, number)				# query assignment

		temp = get_sess_vals(self.session, 'quarter', 'year')			# try to grab current quarter/year from session
		if not temp:													# redirect with error if it doesn't exist
			return self.redirect('/admin?message=Please set a current quarter and year')
		quarter,year = temp
		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		quarters = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}

		template_values = {												# build template value map...
			'a': assignment,
			'fid': assignment.fade_in_date.strftime('%Y-%m-%d'),
			'fit': assignment.fade_in_date.strftime('%H:%M'),
			'dd': assignment.due_date.strftime('%Y-%m-%d'),
			'dt': assignment.due_date.strftime('%H:%M'),
			'cd': assignment.close_date.strftime('%Y-%m-%d'),
			'ct': assignment.close_date.strftime('%H:%M'),
			'eod': assignment.eval_open_date.strftime('%Y-%m-%d'),
			'eot': assignment.eval_open_date.strftime('%H:%M'),
			'ecd': assignment.eval_date.strftime('%Y-%m-%d'),
			'ect': assignment.eval_date.strftime('%H:%M'),
			'fod': assignment.fade_out_date.strftime('%Y-%m-%d'),
			'fot': assignment.fade_out_date.strftime('%H:%M'),
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
			'quarter': quarter,
			'quarters': sorted(quarters.items()),
			'year': year,
			'number': number,
		}
		template = JINJA_ENV.get_template('/templates/admin_assignment_edit.html')
		return self.response.write(template.render(template_values))	# ...and render the response


class EditStudent(CustomHandler):

	#@admin_required
	def get(self):
		student = Student.query(
			Student.studentid == int(self.request.get('studentid')),
			Student.quarter == int(self.request.get('quarter')),
			Student.year == int(self.request.get('year')),
		).get()
		template_values = {'student': student}
		template = JINJA_ENV.get_template('/templates/admin_student_edit.html')
		self.response.write(template.render(template_values))


	def post(self):
		student = Student.query(
			Student.studentid == int(self.request.get('studentid')),
			Student.quarter == int(self.request.get('quarter')),
			Student.year == int(self.request.get('year')),
		).get()

		message = ''

		if student:
			if self.request.get('to_delete') == 'yes':
				message += 'Student ' + student.first_name + ', ' + student.last_name
				message += ' (' + str(student.studentid) + ') successfully deleted'

				student.key.delete()
			else:
				student.ucinetid = self.request.get('ucinetid').strip()
				student.first_name = self.request.get('first_name').strip()
				student.last_name = self.request.get('last_name').strip()
				student.email = self.request.get('email').strip()
				student.lab = int(self.request.get('lab').strip())
				student.active = eval(self.request.get('active'))
				print(student.active)

				student.put()

				message += 'Student ' + student.first_name + ', ' + student.last_name
				message += ' (' + str(student.studentid) + ') successfully updated'

		self.redirect('/admin?message=' + message) 



class ManageAssignments(CustomHandler):

	#@admin_required
	def get(self):
		quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}

		quarter = self.request.get('quarter')								# try grabbing quarter/year from URL
		year = self.request.get('year')

		if not quarter or not year:											# if they don't exist, try grabbing from session
			temp = get_sess_vals(self.session, 'quarter', 'year')

			if not temp:													# if they don't exist there, redirect with error
				return self.redirect('/admin?message=Please set a current quarter and year')
		
			quarter,year = temp													

		assignments = self.assigns_for_quarter(int(quarter), int(year))		# grab all assignment for quarter/year

		template = JINJA_ENV.get_template('/templates/admin_assignment_view.html')
		template_values = {													# build template value map...
			'assignments': assignments.order(Assignment.number),
			'quarter_name': quarter_map[int(quarter)],
			'quarter': int(quarter),
			'year': int(year),
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
		}
		return self.response.write(template.render(template_values))		# ...and render the response


class MainAdmin(CustomHandler):

	#@admin_required
	def get(self):
		user = users.get_current_user()										# grab current user
		message = self.request.get('message')								# grab message from URL, if it exists

		self.session['quarter'] = self.quarter()							# load current quarter/year into session
		self.session['year'] = self.year()

		template = JINJA_ENV.get_template('/templates/admin.html')
		template_values = {													# build template value map...
			'message': message,
			'user': user,
			'sign_out': users.create_logout_url('/'),
			'quarter': self.session.get('quarter'),
			'year': self.session.get('year'),
		}
		return self.response.write(template.render(template_values))		# ...and render the response


class UpdateQuarterYear(CustomHandler):

	def get(self):
		setting = Setting.query().get()
		template_values = {
			'year': setting.year if setting else None,
			'quarter': setting.quarter if setting else None,
			'current_year': datetime.date.today().year
		}
		template = JINJA_ENV.get_template('/templates/admin_quarter_year.html')
		self.response.write(template.render(template_values))


	def post(self):
		setting = Setting.query().get()

		if not setting:
			setting = Setting()

		setting.year = int(self.request.get('year'))
		setting.quarter = int(self.request.get('quarter'))

		setting.put()

		return self.redirect('/admin?message=Quarter and Year Updated')



class UploadRoster(CustomHandler):

	#@admin_required
	def get(self):
		quarter = self.request.get('quarter')									# try grabbing quarter/year from URL
		year = self.request.get('year')

		if not quarter or not year:												# if they don't exist, try grabbing from session
			temp = get_sess_vals(self.session, 'quarter', 'year')				# try grabbing quarter/year from session
			if not temp:														# redirect with error if it doesn't exist
				return self.redirect('/admin?message=Please set a current quarter and year')
			quarter,year = temp

		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		quarters = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}

		template_values = {														# build template values...
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
			'quarter': int(quarter),
			'year': int(year),
			'quarters': sorted(quarters.items()),
		}
		template = JINJA_ENV.get_template('/templates/admin_upload.html')
		return self.response.write(template.render(template_values))			# ...and render the response


	def post(self):
		try:
			file = self.request.get('the_file')									# try grabbing file...
			file = file.strip().split('\n')										# ...and parsing it into lines

			quarter = int(self.request.get('quarter'))							# grab year/quarter info
			year = int(self.request.get('year'))
			
			# students to be uploaded (is set because students must be unique; be careful!)
			students = []
			# to check for duplicates in roster
			student_cache = set()

			# grab students in DB (active and not active) (have to do it twice because of DB limitations)
			existing_students = self.get_active_students(quarter, year).fetch()	
			existing_students += self.get_active_students(quarter, year, active=False).fetch()
			# convert to dict for O(1) access time
			existing_students = dict(map(lambda x: (int(x.studentid), x), existing_students))

			for row in file:
				row = row.split(',')

				# grab student ID from current row of CSV roster
				studentid = int(row[0].strip())

				# if student w/ same studentid has already been found in roster, skip...
				if studentid in student_cache:
					continue

				# ...else, add them to 'seen' cache
				student_cache.add(studentid)

				# if student in DB, skip to next student...
				if studentid in existing_students:
					existing_student = existing_students[studentid]

					# ...unless they're inactive; if so, activate them...
					if not existing_student.active:
						existing_student.active = True
						students.append(existing_student)

					# ...to see which students have dropped the class, remove active students from existing_students
					del existing_students[studentid]
					# ...and continue to next student
					continue

				# create student object
				student = Student()

				student.studentid = studentid
				student.last_name = row[1].strip().title()
				student.first_name = row[2].strip().title()
				student.ucinetid = row[3].lower().strip()
				student.email = row[4].lower().strip()
				student.lab = int(row[5])
				student.quarter = quarter
				student.year = year
				student.active = True
				students.append(student)

				print(student)
				print(student.studentid in existing_students)

			# deactivate students who have dropped (students left in existing_students)
			for dropped in existing_students.values():
				dropped.active = False
				students.append(dropped)

			# save student objects...
			ndb.put_multi(students)
			# ...and render the response
			return self.redirect('/admin/roster/view?message=' + 'Successfully uploaded new roster')			

		except Exception, e:
			return self.redirect('/admin?message=' + 'There was a problem uploading the roster: ' + str(e))			




class ViewEvals(CustomHandler):

	def get(self):
		current_assignment = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)
		template_values = {
			'year': datetime.date.today().year,	
			'current': current_assignment
		}
		template = JINJA_ENV.get_template('/templates/admin_evals_view.html')
		self.response.write(template.render(template_values))


	def post(self):
		evaluations = Evaluation.query(
			Evaluation.year == int(self.request.get('year')),
			Evaluation.quarter == int(self.request.get('quarter')),
			Evaluation.assignment_number == int(self.request.get('assign_num')),
			Evaluation.active == True
		)

		solo_partners = Partnership.query(
			Partnership.year == int(self.request.get('year')),
			Partnership.quarter == int(self.request.get('quarter')),
			Evaluation.assignment_number == int(self.request.get('assign_num')),
			Partnership.acceptor == None,
			Partnership.active == True
		)

		template_values = {
			'year': self.request.get('year'),
			'quarter': self.request.get('quarter'),
			'evals': evaluations,
			'solos': solo_partners,
			'current': self.request.get('assign_num')
		}
		template = JINJA_ENV.get_template('/templates/admin_evals_view.html')
		self.response.write(template.render(template_values))



class ViewPartnerships(CustomHandler):

	#@admin_required
	def get(self):
		template = JINJA_ENV.get_template('/templates/admin_partnerships.html')
		self.response.write(template.render({'year': datetime.date.today().year}))


	def post(self):
		quarter = int(self.request.get('quarter'))
		year = int(self.request.get('year'))
		view_by = self.request.get('view_by')

		if view_by == 'class':
			students = Student.query(
				Student.year == year,
				Student.quarter == quarter
			).fetch()
		else:
			students = Student.query(
				Student.year == year,
				Student.quarter == quarter,
				Student.lab == int(self.request.get('lab'))
			).fetch()

		partnership_dict = {}
		for student in students:
			student_info = (student.studentid, student.ucinetid, student.last_name, 
				student.first_name, student.lab)

			current_assign = self.current_assign(Setting.query().get().quarter, Setting.query().get().year)

			partners = []
			for i in range(1, current_assign.number + 1):
				partnership = Partnership.query(
					ndb.OR(Partnership.acceptor == student.key, Partnership.initiator == student.key),
					Partnership.assignment_number == i,
					Partnership.active == True,
				).get()
				
				if partnership and student and partnership.initiator.get():
					if partnership.initiator.get().studentid != student.studentid:
						partners.append(partnership.initiator.get().email)
					else:
						if partnership.acceptor.get():
							partners.append(partnership.acceptor.get().email)
						else:
							partners.append('No Partner')
				else:
					partners.append('No Selection')

				partnership_dict[student_info] = partners


		template_values = {
			'partnerships': sorted(partnership_dict.items(), key=lambda x: (x[0][4], x[0][2])),
			'view_by': view_by,
			'year': datetime.date.today().year
		}
		template = JINJA_ENV.get_template('/templates/admin_partnerships.html')
		self.response.write(template.render(template_values))
			


class ViewRoster(CustomHandler):

	#@admin_required
	def get(self):
		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
		quarter = self.request.get('quarter')								# try grabbing quarter/year from URL
		year = self.request.get('year')

		if not quarter or not year:											# if they don't exist, try grabbing from session
			temp = get_sess_vals(self.session, 'quarter', 'year')
			if not temp:													# if they don't exist there, redirect with error
				return self.redirect('/admin?message=Please set a current quarter and year')
			quarter,year = temp													

		quarter,year = int(quarter), int(year)
		active_students = self.get_active_students(quarter, year).fetch()	# grab lists of active/inactive students
		inactive_students = self.get_active_students(quarter, year, active=False).fetch()
		active_num = len(active_students)									# get number of active/inactive students
		inactive_num = len(inactive_students)

		template = JINJA_ENV.get_template('/templates/admin_view.html')
		template_values = {													# build map of template values...
			'students': sorted(active_students + inactive_students, key=lambda x: (x.lab, x.last_name)),
			'quarter_name': quarter_map[int(quarter)],
			'quarter': int(quarter),
			'year': int(year),
			'student_num': active_num + inactive_num,
			'active_num': active_num,
			'inactive_num': inactive_num,
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
		}
		return self.response.write(template.render(template_values))		# ...and render the response
		

################################################################################
################################################################################
################################################################################
