import webapp2

from google.appengine.api import mail


class SendMail:

	def __init__(self, recvr=None, type=None, **kargs):
		self.sender = 'sherronb+PartnerApp@uci.edu'

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

		extra = 'You will need to find another partner.'
		assign = recvr.assignment_number

		self.partner_message_one_student(p1, p2, n1, n2, assign, 'cancelled', extra)
		self.partner_message_one_student(p2, p1, n2, n1, assign, 'cancelled', extra)


	def partner_confirm(self, recvr):
		p1,p2,n1,n2 = SendMail.parse_partnership(recvr)
		assign = recvr.assignment_number

		self.partner_message_one_student(p1, p2, n1, n2, assign, 'confirmed')
		self.partner_message_one_student(p2, p1, n2, n1, assign, 'confirmed')


	def partner_message_one_student(self, p1, p2, n1, n2, assign, message, extra=''):
		if not p1:
			return

		subject = 'ICS 10 Lab Asst. ' + str(assign) + ' Partnership ' + message.capitalize()

		body  = 'This is an automated message from the partner app.\n\n\r'
		body += n1 + ':\n\n\rYour partnership with ' + n2 + ' for ICS 10 lab asst '
		body += str(assign) + ' has been ' + str(message) + '. ' + extra
		body += '\n\n\rIf this is a mistake, please contact your TA right away.'
		body += '\n\rNOTE: Please DO NOT reply to this message.'

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
			return (str(student.first_name) + ' ' + str(student.last_name) + ' (' + student.ucinetid + ')').strip()

		return 'No Partner (authorized solo)'
		
			
