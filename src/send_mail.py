import webapp2

from google.appengine.api import mail


class SendMail:

	def __init__(self, recvr=None, type=None, **kargs):
		self.sender = 'sherronb@uci.edu'

		if recvr:
			self.route_message(recvr, type, **kargs)


	def route_message(self, recvr, type, **kargs):
		if type == 'sign_up':
			pass
		elif type == 'partner_confirm':
			self.partner_confirm(recvr)
		elif type == 'recvd_invite':
			pass
		elif type == 'partner_deactivated':
			self.partner_deactivated(recvr)
		elif 'subject' in kargs and 'body' in kargs:
			mail.send_mail(self.sender, recvr, kargs['subject'], kargs['body'])
		else:
			raise ValueError('SendMail.route_message: invalid value for \'type\' ( ' + type + ')')


	def partner_deactivated(self, recvr):
		p1,p2,n1,n2 = SendMail.parse_partnership(recvr)

		self.partner_message_one_student(p1, p2, n1, n2, recvr.assignment_number, 'dissolved')
		self.partner_message_one_student(p2, p1, n2, n1, recvr.assignment_number, 'dissolved')


	def partner_confirm(self, recvr):
		p1,p2,n1,n2 = SendMail.parse_partnership(recvr)

		self.partner_message_one_student(p1, p2, n1, n2, recvr.assignment_number, 'confirmed')
		self.partner_message_one_student(p2, p1, n2, n1, recvr.assignment_number, 'confirmed')


	def partner_message_one_student(self, p1, p2, n1, n2, assign, message):
		if not p1:
			return

		name = p1.preferred_name if p1.preferred_name else p1.first_name

		subject =  'Partner App: Partnership with ' + n2
		subject += ' for Assign. ' + str(assign) + ' Has Been ' + message.capitalize()

		body =  'Hello ' + name + ',\n\n\rThis is a message sent to inform you (' + n1 + ') '
		body += 'that your partnership with ' + n2 + ' for assignment ' + str(assign) 
		body += ' has been ' + message + '.\n\n\rIf this is a mistake, please contact your TA.'

		print(body)

		mail.send_mail(self.sender, p1.email, subject, body)


## Helpers #####################################################################


	@staticmethod
	def parse_partnership(recvr):
		p1 = recvr.initiator.get()
		p2 = recvr.acceptor.get() if recvr.acceptor else None

		n1 = SendMail.extract_name(p1)
		n2 = SendMail.extract_name(p2)

		return p1,p2,n1,n2


	@staticmethod
	def extract_name(student):
		if student:
			return str(student.ucinetid) + ' - ' + str(student.last_name) + ', ' + (student.first_name)

		return 'No Partner (authorized solo)'
		
			
