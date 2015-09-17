################################################################################
## IMPORTS #####################################################################
################################################################################


import cgi
import csv
import datetime 
import jinja2
import os
import webapp2

from collections import defaultdict
from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import admin_required

from helpers.admin_helpers import keys_to_partners, make_date, student_info_to_partner_list
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

		last_num = self.get_assign_n(quarter, year, -1)
		last_num = 0 if not last_num else last_num.number
		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		quarters = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
		template_values = {														# build template value map...
			'year': year,
			'quarter': quarter,
			'quarters': sorted(quarters.items()),
			'last_num': last_num,
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
		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
		quarter = self.request.get('quarter')										# try grabbing quarter/year from URL
		year = self.request.get('year')

		if not quarter or not year:													# if they don't exist, try grabbing from session
			temp = get_sess_vals(self.session, 'quarter', 'year')
			if not temp:															# if they don't exist there, redirect with error
				return self.redirect('/admin?message=Please set a current quarter and year')
			quarter,year = temp													

		quarter,year = int(quarter), int(year)
		view = self.request.get('view')												# check URL for 'view by' options (lab vs class)
		view = view if view else 'class'

		if view == 'class':															# if user wants to veiw by class, or the view by option wasn't specified...
			students = self.get_active_students(quarter, year).fetch()				# ...grab all active students
		else:
			students = self.students_by_lab(quarter, year, int(view)).fetch()		# ...otherwise, grab students for the lab specified

		current_assign = self.current_assign(quarter, year)							# grab current assignment...
		current_num = 1 if not current_assign else current_assign.number			# ...and get its number, if it exists

		template = JINJA_ENV.get_template('/templates/admin_add_partnership.html')
		template_values = {															# build map of template values...
			'students': sorted(students, key=lambda x: x.last_name),
			'view': str(view),
			'quarter': quarter,
			'year': year,
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
			'current_num': current_num,
			'num_labs': self.num_labs() if self.num_labs() else 1,
		}
		return self.response.write(template.render(template_values))				# ...and render the response


class AddStudent(CustomHandler):

	#@admin_required
	def get(self):
		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		quarters = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}

		temp = get_sess_vals(self.session, 'quarter', 'year')					# try grabbing quarter/year from session
		if not temp:															# redirect with error if it doesn't exist
			return self.redirect('/admin?message=Please set a current quarter and year')
		quarter,year = temp

		template_values = {														# build map of template values...
			'message': self.request.get('message'),								# grab message if it exists
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
			'quarter': quarter,
			'quarters': sorted(quarters.items()),
			'year': year,
		}
		template = JINJA_ENV.get_template('/templates/admin_add_student.html')
		return self.response.write(template.render(template_values))			# ...and render the request


	def post(self):
		try:																	# try to create student from form values
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

		except Exception, e:													# on error, redirect with message
			return self.redirect('/admin?message=' + 'There was a problem adding that student: ' + str(e))			
		
		student.put()															# save student

		message = 'Student ' + student.ucinetid + ' has been added'				# create success message

		return self.redirect('/admin/student/add?message=' + message)			# render response



class ClearDB(CustomHandler):

	#@admin_required
	def get(self):
		template = JINJA_ENV.get_template('/templates/admin_cleardb.html')
		self.response.write(template.render())


	def post(self):
		if bool(self.request.get('choice')):
			ndb.delete_multi(Student.query().fetch(keys_only=True))
			ndb.delete_multi(Assignment.query().fetch(keys_only=True))
			ndb.delete_multi(Setting.query().fetch(keys_only=True))

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
			'eod': assignment.eval_open_date.strftime('%Y-%m-%d') if assignment.eval_open_date else '00-00-0000',
			'eot': assignment.eval_open_date.strftime('%H:%M') if assignment.eval_open_date else '00:00',
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
		studentid = int(self.request.get('studentid'))						# grab studentid from URL (guaranteed to be there, unless URL was tinkered with)

		student = self.student_by_id(quarter, year, studentid)				# grab student by ID (quarter, year, and student ID == PK)
		# if the student wasn't found, he/she might be inactive
		student = student if student else self.student_by_id(quarter, year, studentid, active=False)

		template_values = {													# build map of template values...
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
			'student': student,
			'quarter': quarter,
			'year': year,
		}
		template = JINJA_ENV.get_template('/templates/admin_student_edit.html')
		return self.response.write(template.render(template_values))		# ...and render the response


	def post(self):
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
		studentid = int(self.request.get('studentid'))						# grab studentid from URL (guaranteed to be there, unless URL was tinkered with)

		student = self.student_by_id(quarter, year, studentid)				# grab student by ID (quarter, year, and student ID == PK)
		# if the student wasn't found, he/she might be inactive
		student = student if student else self.student_by_id(quarter, year, studentid, active=False)
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

				student.put()

				message += 'Student ' + student.first_name + ', ' + student.last_name
				message += ' (' + str(student.studentid) + ') successfully updated'

		self.redirect('/admin/roster/view?message=' + message) 



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

		quarter,year = self.quarter(), self.year()

		if (not quarter or not year) and not message:
			message = 'Please set a current year and quarter'

		self.session['quarter'] = quarter 									# load current quarter/year into session
		self.session['year'] = year

		template = JINJA_ENV.get_template('/templates/admin.html')
		template_values = {													# build template value map...
			'message': message,
			'user': user,
			'sign_out': users.create_logout_url('/'),
			'quarter': self.session.get('quarter'),
			'year': self.session.get('year'),
		}
		return self.response.write(template.render(template_values))		# ...and render the response


class UpdateSettings(CustomHandler):

	def get(self):
		setting = Setting.query().get()
		template_values = {
			'year': setting.year if setting else None,
			'quarter': setting.quarter if setting else None,
			'num_labs': setting.num_labs if setting else None,
			'current_year': datetime.date.today().year
		}
		template = JINJA_ENV.get_template('/templates/admin_quarter_year.html')
		return self.response.write(template.render(template_values))


	def post(self):
		setting = Setting.query().get()

		if not setting:
			setting = Setting()

		setting.year = int(self.request.get('year'))
		setting.quarter = int(self.request.get('quarter'))
		setting.num_labs = int(self.request.get('num_labs'))

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
			'message': self.request.get('message'),
		}
		template = JINJA_ENV.get_template('/templates/admin_upload.html')
		return self.response.write(template.render(template_values))			# ...and render the response


	def post(self):
		try:
			file = self.request.get('the_file')									# try grabbing file...
			file = file.strip().split('\n')										# ...and parsing it into lines

			quarter = int(self.request.get('quarter'))							# grab year/quarter info
			year = int(self.request.get('year'))
			num_labs = 0
			
			# students to be uploaded 
			students = []
			# to check for duplicates in roster
			student_cache = set()

			# grab students in DB (active and not active) 
			existing_students = self.get_active_students(quarter, year).fetch()	
			existing_students += self.get_active_students(quarter, year, active=False).fetch()
			# convert to dict for O(1) access time
			existing_students = dict(map(lambda x: (int(x.studentid), x), existing_students))

			for row in file:
				row = row.split(',')

				# save highest lab number found
				if int(row[5]) > num_labs:
					num_labs = int(row[5])

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

			# deactivate students who have dropped (students left in existing_students)
			for dropped in existing_students.values():
				dropped.active = False
				students.append(dropped)

			# save student objects...
			ndb.put_multi(students)
			# ...save num_labs...
			setting = Setting.query().get()
			setting = setting if setting else Setting()
			setting.num_labs = num_labs
			setting.put()
			# ...and render the response
			return self.redirect('/admin/roster/view?message=' + 'Successfully uploaded new roster')			

		except Exception, e:
			return self.redirect('/admin?message=' + 'There was a problem uploading the roster: ' + str(e))			


class ViewEvals(CustomHandler):

	def get(self):
		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
		quarter = self.request.get('quarter')										# try grabbing quarter/year from URL
		year = self.request.get('year')
		assign_num = self.request.get('assign_num')									# try grabbing assignment number from URL

		if not quarter or not year:													# if they don't exist, try grabbing from session
			temp = get_sess_vals(self.session, 'quarter', 'year')
			if not temp:															# if they don't exist there, redirect with error
				return self.redirect('/admin?message=Please set a current quarter and year')
			quarter,year = temp													

		quarter,year = int(quarter), int(year)
		current_assignment = self.current_assign(quarter, year)						# grab current assignment

		if current_assignment and not assign_num:
			assign_num = current_assignment.number									# use assign_num if it exsits, else number of current assignment

		assign_num = int(assign_num) if assign_num else 1							# (to avoid errors if there are no assignments in the DB
		last_num = self.get_assign_n(quarter, year, -1)								# grab last assignment
		last_num = last_num.number if last_num else assign_num						# (to avoid errors if there are no assignments in the DB)
		evals = self.evals_for_assign(quarter, year, assign_num)					# grab evals for assignment...
		solo_partners = self.solo_partners(quarter, year, assign_num)				# ...and grab endorsed solos (they're exempt from evals)
		template_values = {															# build template value map...
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
			'quarter': quarter,
			'quarter_name': quarter_map[quarter],
			'year': year,
			'assign_num': assign_num,
			'message': self.request.get('message'),
			'evals': evals,
			'solos': solo_partners,
			'last_num': last_num,
		}
		template = JINJA_ENV.get_template('/templates/admin_evals_view.html')
		return self.response.write(template.render(template_values))			# ...and render the response


class ViewPartnerships(CustomHandler):

	#@admin_required
	def get(self):
		# pass map of quarter DB representations (ints) to string representation
		# TODO:
		#	quarters should not be hardcoded 
		#	rethink logic
		quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
		quarter = self.request.get('quarter')										# try grabbing quarter/year from URL
		year = self.request.get('year')

		if not quarter or not year:													# if they don't exist, try grabbing from session
			temp = get_sess_vals(self.session, 'quarter', 'year')
			if not temp:															# if they don't exist there, redirect with error
				return self.redirect('/admin?message=Please set a current quarter and year')
			quarter,year = temp													

		quarter,year = int(quarter), int(year)
		view_by = self.request.get('view_by')										# check URL for 'view by' options (lab vs class)
		view_by = view_by if view_by else 1

		if view_by == 'class':														# if user wants to veiw by class, or the view by option wasn't specified...
			students = self.get_active_students(quarter, year).fetch()				# ...grab all active students
		else:
			students = self.students_by_lab(quarter, year, int(view_by)).fetch()	# ...otherwise, grab students for the lab specified

		all_partners = self.all_partners(quarter, year).fetch()						# grab all partnerships 
		last_assign = self.get_assign_n(quarter, year, -1)							# grab most recent assignment...
		last_num = 1 if not last_assign else last_assign.number						# ...and its number

		keys_to_students = dict(map(lambda x: (x.key,x), students))					# map student objects to keys for easy, fast access from partnership objects
		keys_to_partnerships = keys_to_partners(all_partners)						# map student keys to partnerships for easy, fast access

		# create mapping of student info to partnership info that the partnership template expects
		partnership_dict = student_info_to_partner_list(last_num, keys_to_partnerships, keys_to_students, students)

		partnership_dict = sorted(partnership_dict.items(), key=lambda x: (x[0][4], x[0][2]))
		num_labs = self.num_labs()													

		template_values = {															# build map of template values...
			'partnerships': partnership_dict,
			'view_by': str(view_by),
			'year': year,
			'quarter': quarter,
			'num_labs': num_labs if num_labs else 0,
			'last_num': last_num,
			'user': users.get_current_user(),
			'sign_out': users.create_logout_url('/'),
		}
		template = JINJA_ENV.get_template('/templates/admin_partnerships.html')
		return self.response.write(template.render(template_values))				# ...and render the response


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
			'message': self.request.get('message'),
		}
		return self.response.write(template.render(template_values))		# ...and render the response


class ViewStudent(CustomHandler):

	def get(self):
		pass
		

################################################################################
################################################################################
################################################################################
