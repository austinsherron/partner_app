from google.appengine.ext import ndb


class Assignment(ndb.Model):
	number = ndb.IntegerProperty()
	fade_in_date = ndb.DateTimeProperty()
	due_date = ndb.DateTimeProperty()
	close_date = ndb.DateTimeProperty()
	eval_open_date = ndb.DateTimeProperty()
	eval_date = ndb.DateTimeProperty()
	fade_out_date = ndb.DateTimeProperty()
	quarter = ndb.IntegerProperty()
	year = ndb.IntegerProperty()
	current = ndb.GenericProperty()



class Instructor(ndb.Model):
	ucinetid = ndb.StringProperty()
	name = ndb.StringProperty()
	email = ndb.StringProperty()



class Student(ndb.Model):
	ucinetid = ndb.StringProperty()
	studentid = ndb.IntegerProperty()
	first_name = ndb.StringProperty()
	last_name = ndb.StringProperty()
	preferred_name = ndb.StringProperty()
	email = ndb.StringProperty()
	lab = ndb.IntegerProperty()
	quarter = ndb.IntegerProperty()
	year = ndb.IntegerProperty()
	active = ndb.GenericProperty()
	bio = ndb.TextProperty()
	programming_ability = ndb.StringProperty()
	avatar = ndb.BlobProperty()
	phone_number = ndb.StringProperty()



class Invitation(ndb.Model):
	invitor = ndb.KeyProperty(kind=Student)
	invitee = ndb.KeyProperty(kind=Student)
	assignment_number = ndb.IntegerProperty()
	active = ndb.GenericProperty()
	accepted = ndb.BooleanProperty(default=False)
	created = ndb.DateTimeProperty(auto_now_add=True)



class Partnership(ndb.Model):
	initiator = ndb.KeyProperty(kind=Student)
	acceptor = ndb.KeyProperty(kind=Student)
	assignment_number = ndb.IntegerProperty()
	active = ndb.GenericProperty()
	quarter = ndb.IntegerProperty()
	year = ndb.IntegerProperty()
	


class Evaluation(ndb.Model):
	evaluator = ndb.KeyProperty(kind=Student)
	evaluatee = ndb.KeyProperty(kind=Student)
	assignment_number = ndb.IntegerProperty()
	responses = ndb.StringProperty(repeated=True)
	year = ndb.IntegerProperty()
	quarter = ndb.IntegerProperty()
	active = ndb.GenericProperty()



class Setting(ndb.Model):
	year = ndb.IntegerProperty()
	quarter = ndb.IntegerProperty()