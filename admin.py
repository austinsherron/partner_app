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

from admin_helpers import make_date
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
		quarter = self.quarter()
		year = self.year()
		current_assignment = self.current_assign(quarter, year)
		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		quarters = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
		template_values = {
			'year': year,
			'quarter': quarter,
			'quarters': sorted(quarters.items()),
			'current': current_assignment,
			'today': datetime.date.today().strftime("%Y-%m-%d"),
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
		}
		self.response.write(template.render(template_values))


	def post(self):
		# create new assignment
		assignment = Assignment()
		# set PK values
		assignment.year = int(self.request.get('year'))
		assignment.quarter = int(self.request.get('quarter'))
		assignment.number = int(self.request.get('assign_num'))

		# if an assignment with the same PK values exist, redirect with error; assignment isn't created
		if self.get_assign(assignment.quarter, assignment.year, assignment.number):
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

			assignment.put()
	
			message = 'Assignment ' + str(assignment.number) + ' for quarter '
			message += str(assignment.quarter) + ' ' + str(assignment.year) + ' successfully added'

			return self.redirect('/admin/assignment/add?message=' + message)



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

		message = self.request.get('message')

		template_values = {
			'message': message,
			'year': datetime.date.today().year
		}
		
		template = JINJA_ENV.get_template('/templates/admin_add_student.html')
		self.response.write(template.render(template_values))


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


class DeleteStudents(CustomHandler):

	def post(self):
		quarter_dict = {'fall': 1, 'winter': 2, 'spring': 3, 'summer': 4}
		student_ids = [int(sid) for sid in self.request.POST.getall('student')]
		quarter = quarter_dict[self.request.get('quarter').lower()]
		year = int(self.request.get('year'))

		ndb.delete_multi(Student.query(
			Student.studentid.IN(student_ids),
			Student.year == year,
			Student.quarter == quarter
		).fetch(keys_only=True))
		
		message = 'Students successfully deleted'
		self.redirect('/admin?message=' + message)


class EditAssignment(CustomHandler):
	def get(self):
		assignment = Assignment.query(
			Assignment.number == int(self.request.get('number')),
			Assignment.year == int(self.request.get('year')),
			Assignment.quarter == int(self.request.get('quarter')),
		).get()
		template_values = {
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
		}
		template = JINJA_ENV.get_template('/templates/admin_assignment_edit.html')
		self.response.write(template.render(template_values))


	def post(self):
		assignment = Assignment.query(
			Assignment.number == int(self.request.get('number')),
			Assignment.year == int(self.request.get('year')),
			Assignment.quarter == int(self.request.get('quarter')),
		).get()

		fade_in_date = str(self.request.get('fade_in_date')).split('-')
		fade_in_time = str(self.request.get('fade_in_time')).split(':')

		assignment.fade_in_date = datetime.datetime(
			year=int(fade_in_date[0]),
			month=int(fade_in_date[1]),
			day=int(fade_in_date[2]),
			hour=int(fade_in_time[0]),
			minute=int(fade_in_time[1])
		)
		due_date = str(self.request.get('due_date')).split('-')
		due_time = str(self.request.get('due_time')).split(':')

		assignment.due_date = datetime.datetime(
			year=int(due_date[0]),
			month=int(due_date[1]),
			day=int(due_date[2]),
			hour=int(due_time[0]),
			minute=int(due_time[1])
		)
		close_date = str(self.request.get('close_date')).split('-')
		close_time = str(self.request.get('close_time')).split(':')

		assignment.close_date = datetime.datetime(
			year=int(close_date[0]),
			month=int(close_date[1]),
			day=int(close_date[2]),
			hour=int(close_time[0]),
			minute=int(close_time[1])
		)
		eval_open_date = str(self.request.get('eval_open_date')).split('-')
		eval_open_time = str(self.request.get('eval_open_time')).split(':')

		assignment.eval_open_date = datetime.datetime(
			year=int(eval_open_date[0]),
			month=int(eval_open_date[1]),
			day=int(eval_open_date[2]),
			hour=int(eval_open_time[0]),
			minute=int(eval_open_time[1])
		)
		eval_date = str(self.request.get('eval_date')).split('-')
		eval_time = str(self.request.get('eval_time')).split(':')

		assignment.eval_date = datetime.datetime(
			year=int(eval_date[0]),
			month=int(eval_date[1]),
			day=int(eval_date[2]),
			hour=int(eval_time[0]),
			minute=int(eval_time[1])
		)
		fade_out_date = str(self.request.get('fade_out_date')).split('-')
		fade_out_time = str(self.request.get('fade_out_time')).split(':')

		assignment.fade_out_date = datetime.datetime(
			year=int(fade_out_date[0]),
			month=int(fade_out_date[1]),
			day=int(fade_out_date[2]),
			hour=int(fade_out_time[0]),
			minute=int(fade_out_time[1])
		)

		# set 'current' value
		assignment.current = eval(self.request.get('current'))

		# if assignment is set to current...
		if assignment.current:
		# ...get all assignments for year/quarter of new assignment...
			assignments = Assignment.query(Assignment.year == assignment.year,
				Assignment.quarter == assignment.quarter)
		# ...and set them to inactive
			for assign in assignments:
				if assign != assignment:
					assign.current = False
					assign.put()

		assignment.put()

		message = 'Assignment ' + str(assignment.number) + ' for quarter '
		message += str(assignment.quarter) + ', ' + str(assignment.year)
		message += ' successfully updated'
	
		self.redirect('/admin?message=' + message)



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
		template = JINJA_ENV.get_template('/templates/admin_assignment_view.html')
		self.response.write(template.render())

	
	def post(self):
		quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
		quarter = self.request.get('quarter')
		year = self.request.get('year')
		assignments = Assignment.query(Assignment.year == int(year), Assignment.quarter == int(quarter))

		template = JINJA_ENV.get_template('/templates/admin_assignment_view.html')
		template_values = {
			'assignments': assignments.order(Assignment.number),
			'quarter': quarter_map[int(quarter)],
			'year': int(year)
		}
		self.response.write(template.render(template_values))



class MainAdmin(CustomHandler):
	#@admin_required
	def get(self):
		user = users.get_current_user()
		message = self.request.get('message')

		template = JINJA_ENV.get_template('/templates/admin.html')
		template_values = {
			'message': message,
			'user': user,
			'sign_out': users.create_logout_url('/')
		}
		self.response.write(template.render(template_values))



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

		self.redirect('/admin/timing/update')



class UploadRoster(CustomHandler):
	#@admin_required
	def get(self):
		template = JINJA_ENV.get_template('/templates/admin_upload.html')
		self.response.write(template.render())


	def post(self):
		try:
			file = self.request.get('the_file')
			file = file.strip().split('\n')
			
			students = []
			for row in file:
				row = row.split(',')
				print('ROW =', row)
				student = Student()

				student_exists = Student.query(
					Student.studentid == int(row[0].strip()),
					Student.quarter == int(self.request.get('quarter')),
					Student.year == int(self.request.get('year')),
					Student.active == True
				).get()

				if not student_exists:
					student.studentid = int(row[0].strip())
					student.last_name = row[1].strip().title()
					student.first_name = row[2].strip().title()
					student.ucinetid = row[3].lower().strip()
					student.email = row[4].lower().strip()
					student.lab = int(row[5])
					student.quarter = int(self.request.get('quarter'))
					student.year = int(self.request.get('year'))
					student.active = True
					students.append(student)

			ndb.put_multi(students)
			self.redirect('/admin?message=' + 'Successfully uploaded new roster')			

		except Exception, e:
			self.redirect('/admin?message=' + 'There was a problem uploading the roster: ' + str(e))			




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
		template = JINJA_ENV.get_template('/templates/admin_view.html')
		self.response.write(template.render({'year': datetime.date.today().year}))

	
	def post(self):
		quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
		quarter = self.request.get('quarter')
		year = self.request.get('year')
		students = Student.query(Student.year == int(year), Student.quarter == int(quarter))

		template = JINJA_ENV.get_template('/templates/admin_view.html')
		template_values = {
			'students': students.order(Student.lab, Student.last_name),
			'quarter': quarter_map[int(quarter)],
			'year': int(year)
		}

		self.response.write(template.render(template_values))
		

