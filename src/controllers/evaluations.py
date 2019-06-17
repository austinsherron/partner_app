import jinja2
import os

from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required

from models import Evaluation
from models import Log 
from src.handler.base_handler import BaseHandler
from src.helpers.helpers import split_last
from src.models.assignment import AssignmentModel
from src.models.eval import EvalModel
from src.models.log import LogModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel
import datetime


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class EvaluatePartner(BaseHandler):
    @login_required
    def get(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()

        # get user
        user = users.get_current_user()
        # get student from user info
        evaluator = StudentModel.get_student_by_email(quarter, year, user.email())
        # get student's partner history
        partners = PartnershipModel.get_active_partner_history_for_student(evaluator, quarter, year)
        # grab the active eval assignments
        eval_assigns = AssignmentModel.get_active_eval_assigns(quarter, year)
        # grab partners for eval assignments
        evaluatees = []
        for eval_assign in eval_assigns:
            for partner in PartnershipModel.get_partner_from_partner_history_by_assign(evaluator, partners, eval_assign.number):
                evaluatees.append((eval_assign.number,partner))
        # filter out No Partner partnerships
        partners = list(filter(lambda x: x[1] != "No Partner" and x[1] != None, evaluatees))
        eval_closed = len(eval_assigns) == 0

        #   Log when eval page is visited
        #get current date (for timestamp)
        cur_date  = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        #get current log, creating one if it does not exist
        current_log = LogModel.get_log_by_student(evaluator, quarter, year).get()
        if current_log == None:
            current_log = Log()
            current_log.owner = evaluator.key
            current_log.quarter=quarter
            current_log.year=year
        #log if the student visited the page with all evals closed
        if eval_closed:
            current_log.log.append(cur_date+" Viewed eval page: ALL EVALS CLOSED")
        else:
        #log all open evaluations when student visited the page
            open_evals = ""
            for ev in evaluatees:
                open_evals += ev[1].ucinetid + " assgt. " + str(ev[0]) + " , "
            current_log.log.append(cur_date+" Viewed eval page: " + open_evals)
        #save to log
        current_log.put()
            
            
    
        rate20scale  = ["0 -- Never, completely inadequate", "1", "2", "3", "4"]
        rate20scale += ["5 -- Seldom, poor quality", "6", "7", "8", "9"]
        rate20scale += ["10 -- About half the time, average", "11", "12", "13", "14"]
        rate20scale += ["15 -- Most of the time, good quality", "16", "17", "18", "19"]
        rate20scale += ["20 -- Always, excellent"]

        rate5scale  = ['1 - My partner was much more capable than I was']
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
            'partners': partners,
        }
        template = JINJA_ENV.get_template('/templates/partner_eval.html')
        self.response.write(template.render(template_values))


    def post(self):
        quarter = SettingModel.quarter()
        year    = SettingModel.year()
        user    = users.get_current_user()

        evaluator       = StudentModel.get_student_by_email(quarter, year, user.email())
        partners        = PartnershipModel.get_active_partner_history_for_student(evaluator, quarter, year)
        eval_key,num    = split_last(self.request.get('evaluatee'))
        eval_assign     = int(num)
        current_partner = ndb.Key(urlsafe=eval_key).get()

        #   Log when eval is submitted
        #current date for timestamp
        cur_date  = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        #get current log, creating one if it does not exist
        current_log = LogModel.get_log_by_student(evaluator, quarter, year).get()
        if current_log == None:
            current_log = Log()
            current_log.owner = evaluator.key
            current_log.quarter=quarter
            current_log.year=year
        #log the submission of the eval
        current_log.log.append(cur_date+" Submitted eval for: " + current_partner.ucinetid + " assgt. " + str(eval_assign))
        #save to log
        current_log.put()

        evaluations = EvalModel.get_existing_eval_by_assign(evaluator, current_partner, eval_assign)
        for eval in evaluations:
            eval.active = False
            eval.put()

        evaluation                   = Evaluation(evaluator = evaluator.key, evaluatee = current_partner.key)
        evaluation.assignment_number = eval_assign
        evaluation.year              = evaluator.year
        evaluation.quarter           = evaluator.quarter
        evaluation.active            = True
        for i in range(1, 11):
            evaluation.responses.append(self.request.get('q' + str(i)))
        evaluation.put()

        message  = 'Evaluation for ' + str(current_partner.last_name) + ', '
        message += str(current_partner.first_name) + ' confirmed: Please refresh the page and confirm the evaluation was submitted.'
        self.redirect('/partner?message=' + message)
