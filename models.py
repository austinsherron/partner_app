################################################################################
## IMPORTS #####################################################################
################################################################################


from google.appengine.ext import ndb


################################################################################
################################################################################
################################################################################


################################################################################
## ASSIGNMENT MODEL ############################################################
################################################################################


class Assignment(ndb.Model):
	number         = ndb.IntegerProperty()
	fade_in_date   = ndb.DateTimeProperty()
	due_date       = ndb.DateTimeProperty()
	close_date     = ndb.DateTimeProperty()
	eval_open_date = ndb.DateTimeProperty()
	eval_date      = ndb.DateTimeProperty()
	fade_out_date  = ndb.DateTimeProperty()
	quarter        = ndb.IntegerProperty()
	year           = ndb.IntegerProperty()
	current        = ndb.GenericProperty()


################################################################################
################################################################################
################################################################################


################################################################################
## INSTRUCTOR MODEL ############################################################
################################################################################


class Instructor(ndb.Model):
	ucinetid = ndb.StringProperty()
	name     = ndb.StringProperty()
	email    = ndb.StringProperty()


################################################################################
################################################################################
################################################################################


################################################################################
## STUDENT MODEL ###############################################################
################################################################################

class EvalExtension(ndb.Model):
	assignment = ndb.IntegerProperty()
	exception = ndb.IntegerProperty()

class Student(ndb.Model):
	ucinetid            = ndb.StringProperty()
	studentid           = ndb.IntegerProperty()
	first_name          = ndb.StringProperty()
	last_name           = ndb.StringProperty()
	preferred_name      = ndb.StringProperty()
	email               = ndb.StringProperty()
	lab                 = ndb.IntegerProperty()
	quarter             = ndb.IntegerProperty()
	year                = ndb.IntegerProperty()
	active              = ndb.GenericProperty()
	eval_exceptions     = ndb.StructuredProperty(EvalExtension, repeated=True)
	bio                 = ndb.TextProperty()
	programming_ability = ndb.StringProperty()
	avatar              = ndb.BlobProperty()
	phone_number        = ndb.StringProperty()
	availability        = ndb.TextProperty()
	created             = ndb.DateTimeProperty(auto_now_add=True)

class Log(ndb.Model):
        owner               = ndb.KeyProperty(kind=Student)
        quarter             = ndb.IntegerProperty()
	year                = ndb.IntegerProperty() 
        log                 = ndb.StringProperty(repeated=True)



################################################################################
################################################################################
################################################################################


################################################################################
## INVITATION MODEL ############################################################
################################################################################


class Invitation(ndb.Model):
	invitor           = ndb.KeyProperty(kind=Student)
	invitee           = ndb.KeyProperty(kind=Student)
	assignment_number = ndb.IntegerProperty()
	active            = ndb.GenericProperty()
	accepted          = ndb.BooleanProperty(default=False)
	created           = ndb.DateTimeProperty(auto_now_add=True)


################################################################################
################################################################################
################################################################################


################################################################################
## PARTNERSHIP MODEL ###########################################################
################################################################################


class Partnership(ndb.Model):
        members           = ndb.KeyProperty(repeated=True)
	assignment_number = ndb.IntegerProperty()
	active            = ndb.GenericProperty()
	quarter           = ndb.IntegerProperty()
	year              = ndb.IntegerProperty()
	notes             = ndb.TextProperty(default='')
	created           = ndb.DateTimeProperty(auto_now_add=True)
        cancelled         = ndb.KeyProperty(repeated=True)
        solo              = ndb.ComputedProperty(lambda p: len(p.members) == 1)
	extension         = ndb.IntegerProperty(default=0)
	extension_date    = ndb.DateTimeProperty()


################################################################################
################################################################################
################################################################################


################################################################################
## EVALUATION MODEL ############################################################
################################################################################


class Evaluation(ndb.Model):
	evaluator         = ndb.KeyProperty(kind=Student)
	evaluatee         = ndb.KeyProperty(kind=Student)
	assignment_number = ndb.IntegerProperty()
	responses         = ndb.StringProperty(repeated=True)
	year              = ndb.IntegerProperty()
	quarter           = ndb.IntegerProperty()
	active            = ndb.GenericProperty()
	created           = ndb.DateTimeProperty(auto_now_add=True)

################################################################################
################################################################################
################################################################################


################################################################################
## SETTING MODEL ###############################################################
################################################################################


class Setting(ndb.Model):
	year                   = ndb.IntegerProperty()
	quarter                = ndb.IntegerProperty()
	num_labs               = ndb.IntegerProperty()
	repeat_partners        = ndb.BooleanProperty(default=False)
	cross_section_partners = ndb.BooleanProperty(default=False)
        group_max              = ndb.IntegerProperty()


################################################################################
################################################################################
################################################################################
