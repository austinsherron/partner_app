import webapp2

from datetime import datetime as dt, timedelta as td
from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras import sessions, auth

from models import Assignment, Student, Instructor, Invitation, Partnership, Evaluation


class CustomHandler(webapp2.RequestHandler):

	def get_student(self, quarter, year, identifier):
		return Student.query(
			Student.quarter == quarter, 
			Student.year == year, 
			Student.email == unicode(identifier),
			Student.active == True
		).get() 


	def get_active_students(self, quarter, year, active=True):
		return Student.query(
			Student.quarter == quarter, 
			Student.year == year, 
			Student.active == active
		)


	def current_assign(self, quarter, year):
		assigns_after_now = Assignment.query(
			Assignment.quarter == quarter,
			Assignment.year == year,
			Assignment.fade_in_date < dt.now() - td(hours=7)
		).order(Assignment.fade_in_date).fetch()

		return assigns_after_now[-1]


	def current_eval_assign(self, quarter, year):
		evals_after_now = Assignment.query(
			Assignment.quarter == quarter,
			Assignment.year == year,
			Assignment.eval_date > dt.now() - td(hours=7)
		).order(Assignment.eval_date).fetch()

		return evals_after_now[0]


	def received_invites(self, student, assign_num, active=True):
		return Invitation.query(
			Invitation.invitee == student.key,
			Invitation.assignment_number == assign_num,
			Invitation.active == active
		)


	def sent_invites(self, student, assign_num, active=True):
		return Invitation.query(
			Invitation.invitor == student.key, 
			Invitation.active == active, 
			Invitation.assignment_number == assign_num 
		)
		

	def student_by_id(self, quarter, year, studentid, active=True):
		return Student.query(
			Student.quarter == quarter,
			Student.year == year, 
			Student.studentid == int(studentid),
			Student.active == active
		).get()
		
		
	def open_invitations(self, confirming, being_confirmed, assign_num):
		return Invitation.query(
			ndb.OR(Invitation.invitee == confirming.key, Invitation.invitee == being_confirmed.key),
			ndb.OR(Invitation.invitor == being_confirmed.key, Invitation.invitor == confirming.key),
			Invitation.assignment_number == assign_num,
			Invitation.active == True
		)


	def all_invitations(self, confirming, being_confirmed, assign_num, active=True):
		return Invitation.query(
			ndb.OR(
					ndb.OR(
						Invitation.invitor == confirming.key, 
						Invitation.invitor == being_confirmed.key),
					ndb.OR(
						Invitation.invitee == confirming.key,
						Invitation.invitee == being_confirmed.key)),
			Invitation.assignment_number == assign_num,
			Invitation.active == active
		)


	def invitation_history(self, confirming):
		return Invitation.query(
			ndb.OR(
				Invitation.invitor == confirming.key, 
				Invitation.invitee == confirming.key),
			)
		

	def open_partnerships(self, confirming, being_confirmed, assign_num):
		return Partnership.query(
			ndb.OR(
					ndb.OR(
						Partnership.initiator == confirming.key, 
						Partnership.initiator == being_confirmed.key),
					ndb.OR(
						Partnership.acceptor == confirming.key,
						Partnership.acceptor == being_confirmed.key)),
			Partnership.assignment_number == assign_num,
			Partnership.active == True
		)

	
	def partner_history(self, student, quarter, year):
		return Partnership.query(
			ndb.OR(Partnership.initiator == student.key, Partnership.acceptor == student.key),
			Partnership.active == True,
			Partnership.quarter == quarter,
			Partnership.year == year
		).order(Partnership.assignment_number)


	def all_partner_history(self, student, quarter, year):
		return Partnership.query(
			ndb.OR(Partnership.initiator == student.key, Partnership.acceptor == student.key),
			Partnership.quarter == quarter,
			Partnership.year == year
		).order(Partnership.assignment_number)
		
		
	def current_partner(self, student, partners, assign_num):
		current_partnership = partners.filter(
			Partnership.active == True,
			Partnership.assignment_number == assign_num
		).get()

		if current_partnership:
			if current_partnership.initiator.get().studentid != student.studentid:
				return current_partnership.initiator.get()
			else: 
				if current_partnership.acceptor:
					return current_partnership.acceptor.get()
				else:
					return 'No Partner'
		

	def students_by_lab(self, quarter, year, lab):
		return Student.query(
			Student.quarter == quarter,
			Student.year == year, 
			Student.lab == lab,
			Student.active == True
		)
		

	def partners_previously(self, selector, selected):
		return Partnership.query(
			ndb.OR(Partnership.initiator == selector.key, Partnership.initiator == selected.key),
			ndb.OR(Partnership.acceptor == selector.key, Partnership.acceptor == selected.key),
			Partnership.active == True
		).fetch()
		

	def inactive_partners(self, student, assign_num):
		dropped = Partnership.query(
			ndb.OR(Partnership.initiator == student.key, Partnership.acceptor == student.key),
			Partnership.assignment_number == assign_num,
			Partnership.active == False
		)
		return dropped
#		if dropped:
#			if dropped.initiator.get().studentid == student.studentid:
#				if dropped.acceptor:
#					return dropped.acceptor.get()
#			else:
#				return dropped.initiator.get()


	def existing_eval(self, evaluator, current_partner, assign_num):
		return Evaluation.query(
			Evaluation.evaluator == evaluator.key, 
			Evaluation.evaluatee == current_partner.key,
			Evaluation.assignment_number == assign_num
		)


	def dropped_partners(self, open_partnerships, confirming, being_confirmed):
		dropped = []
		for partnership in open_partnerships:
			if partnership.initiator.get() in [confirming, being_confirmed]:
				if partnership.acceptor:
					dropped.append(partnership.acceptor.get())
			else:
				dropped.append(partnership.initiator.get())
		return dropped


	def get_assign(self, quarter, year, number):
		return Assignment.query(
			Assignment.quarter == quarter,
			Assignment.year == year,
			Assignment.number == number,
		).get()


	def get_eval_history(self, student, active, quarter, year):
		return Evaluation.query(
			Evaluation.evaluator == student.key,
			Evaluation.active == active,
			Evaluation.quarter == quarter,
			Evaluation.year == year
		)
