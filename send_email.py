import smtplib


class SendMail():
	def __init__(self, sender="sherronb@uci.edu", password="T33diethemans!", targets=[], msg=""):
		self.sender = sender
		self.password = password
		self.targets = targets
		self.msg = msg
		self.smtp_server = 'smtp.gmail.com'
		self.smtp_port = 587
		self.server = None

	
	def __str__(self):
		return "SendMail Object: sender = "+self.sender


	def __repr__(self):
		return 'SendMail('+self.sender+', '+'*'*len(self.password)+')'


	# mutators

	def set_sender(self, new):
		self.sender = new


	def set_password(self, new):
		self.password = new


	def add_targets_man(self, *args):
		for email in args:
			self.targets.append(email)


	def add_targets_list(self, targets):
		for email in targets:
			self.targets.append(email)


	def delete_target(self, target):
		i = self.targets.index(target)
		del self.targets[i]


	def clear_targets(self):
		self.targets = []


	def set_msg(self, msg):
		self.msg = msg


	def set_server(self, new):
		self.smtp_server = new


	def set_port(self, new):
		self.smtp_port = new

	# accessors

	def get_sender(self):
		return self.sender
	
	
	def get_password(self):
		if self.server:
			return self.password
		else:
			return '*'*len(self.password)

	
	def get_targets(self):
		return self.targets

	
	def get_msg(self):
		return self.msg


	def get_smtp_info(self):
		return self.smtp_server+" "+str(self.smtp_port)


	# send email
	
	def login(self):
		self.server = smtplib.SMTP(self.smtp_server, self.smtp_port)
		self.server.starttls()
		self.server.login(self.sender, self.password)


	def send_mail(self):
		for email in self.targets:
			self.server.sendmail(self.sender, email, self.msg)
		




