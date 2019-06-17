import jinja2
import os

from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import admin_required

from models import Student
from src.handler.base_handler import BaseHandler
from src.helpers.helpers import get_sess_val, get_sess_vals
from src.models.assignment import AssignmentModel
from src.models.eval import EvalModel
from src.models.partnership import PartnershipModel
from src.models.student import StudentModel
from src.models.log import LogModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class AddStudent(BaseHandler):

    @admin_required
    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded 
        quarters = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        temp     = get_sess_vals(self.session, 'quarter', 'year')               # try grabbing quarter/year from session
        if not temp:                                                            # redirect with error if it doesn't exist
            return self.redirect('/admin?message=Please set a current quarter and year')
        quarter,year = temp

        template_values = {                                                        
            'message':  self.request.get('message'),                                # grab message if it exists
            'user':     users.get_current_user(),
            'sign_out': users.create_logout_url('/'),
            'quarter':  quarter,
            'quarters': sorted(quarters.items()),
            'year':     year,
        }
        template = JINJA_ENV.get_template('/templates/admin_add_student.html')
        return self.response.write(template.render(template_values))            


    def post(self):
        try:                                                                    # try to create student from form values
            student            = Student()
            student.studentid  = int(self.request.get('studentid').strip())
            student.first_name = self.request.get('first_name').strip().title()    
            student.last_name  = self.request.get('last_name').strip().title()
            student.ucinetid   = self.request.get('ucinetid').strip().lower()
            student.email      = self.request.get('email').strip().lower()
            student.lab        = int(self.request.get('lab').strip())
            student.quarter    = int(self.request.get('quarter').strip())
            student.year       = int(self.request.get('year').strip())
            student.active     = True

        except Exception, e:                                                    
            return self.redirect('/admin?message=' + 'There was a problem adding that student: ' + str(e))            
        
        student.put()                                                            
        message = 'Student ' + student.ucinetid + ' has been added'                
        return self.redirect('/admin/student/add?message=' + message)            


class DeactivateStudents(BaseHandler):

    def post(self):
        quarter = int(self.request.get('quarter'))                                    
        year    = int(self.request.get('year'))                                      

        student_ids   = [int(sid) for sid in self.request.POST.getall('student')]     
        students      = []                                                                   # init container for students to deactivate
        to_deactivate = StudentModel.get_students_by_student_ids(quarter, year, student_ids) # query students to deactivate

        for student in to_deactivate:                                               
            student.active = False
            students.append(student)

        ndb.put_multi(students)                                                     # save student objects to DB
        
        message = 'Students successfully deactivated'                                
        return self.redirect('/admin/roster/view?message=' + message)                


class EditStudent(BaseHandler):

    @admin_required
    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded 
        quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        quarter     = self.request.get('quarter')                                
        year        = self.request.get('year')

        if not quarter or not year:                                         # if quarter/year aren't in URL, get from session
            temp = get_sess_vals(self.session, 'quarter', 'year')
            if not temp:                                                    # if they don't exist there, redirect with error
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp                                                    

        quarter,year = int(quarter), int(year)
        studentid    = int(self.request.get('studentid'))                   # grab studentid from URL (guaranteed to be there, unless URL was tinkered with)

        student = StudentModel.get_student_by_student_id(quarter, year, studentid)              
        # if the student wasn't found, he/she might be inactive
        student = student if student else StudentModel.get_student_by_student_id(quarter, year, studentid, active=False)

        template_values = {                                                    
            'user':     users.get_current_user(),
            'sign_out': users.create_logout_url('/'),
            'student':  student,
            'quarter':  quarter,
            'year':     year,
        }
        template = JINJA_ENV.get_template('/templates/admin_student_edit.html')
        return self.response.write(template.render(template_values))        


    def post(self):
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded 
        quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        quarter     = self.request.get('quarter')                                
        year        = self.request.get('year')

        if not quarter or not year:                                         # if quarter/year aren't in URL, check sessions
            temp = get_sess_vals(self.session, 'quarter', 'year')
            if not temp:                                                    # if they don't exist there, redirect with error
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp                                                    

        quarter,year = int(quarter), int(year)
        studentid    = int(self.request.get('studentid'))                   # grab studentid from URL (guaranteed to be there, unless URL was tinkered with)

        student = StudentModel.get_student_by_student_id(quarter, year, studentid)                
        # if the student wasn't found, he/she might be inactive
        student = student if student else StudentModel.get_student_by_student_id(quarter, year, studentid, active=False)
        message = ''

        if student:
            if self.request.get('to_delete') == 'yes':
                message += 'Student ' + student.first_name + ', ' + student.last_name
                message += ' (' + str(student.studentid) + ') successfully deleted'
                student.key.delete()
            else:
                student.ucinetid   = self.request.get('ucinetid').strip()
                student.first_name = self.request.get('first_name').strip()
                student.last_name  = self.request.get('last_name').strip()
                student.email      = self.request.get('email').strip()
                student.lab        = int(self.request.get('lab').strip())
                student.active     = eval(self.request.get('active'))

                student.put()

                message += 'Student ' + student.first_name + ', ' + student.last_name
                message += ' (' + str(student.studentid) + ') successfully updated'

        self.redirect('/admin/roster/view?message=' + message) 


class ViewStudent(BaseHandler):

    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded 
        quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        quarter     = self.request.get('quarter')                        
        year        = self.request.get('year')

        # try getting quarter/year from session
        if not quarter or not year:                                
            temp = get_sess_vals(self.session, 'quarter', 'year')
            if not temp:                                
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp                                                    

        quarter,year = int(quarter), int(year)
        student      = ndb.Key(urlsafe=self.request.get('student')).get()
        assign_range = AssignmentModel.get_assign_range(quarter, year)

        partner_history     = PartnershipModel.get_active_partner_history_for_student(student, quarter, year, fill_gaps=assign_range)
        all_partner_history = PartnershipModel.get_all_partner_history_for_student(student, quarter, year)

        evals  = EvalModel.get_eval_history_by_evaluator(student, True, quarter, year).fetch()
        evals += EvalModel.get_eval_history_by_evaluator(student, False, quarter, year).fetch()
        evals  = sorted(evals, key=lambda x: x.assignment_number)

        evals_for  = EvalModel.get_eval_history_by_evaluatee(student, True, quarter, year).fetch()
        evals_for += EvalModel.get_eval_history_by_evaluatee(student, False, quarter, year).fetch()
        evals_for  = sorted(evals_for, key=lambda x: x.assignment_number)

        log = LogModel.get_log_by_student(student, quarter, year).get()
        if log:
            log_arr = log.log
        else:
            log_arr = []

        template = JINJA_ENV.get_template('/templates/admin_student_view.html')
        template_values = {
            'student':      student,
            'partners':     partner_history,
            'all_partners': all_partner_history,
            'assign_range': assign_range,
            'evals':        evals,
            'evals_for':    evals_for,
            'user':         users.get_current_user(),
            'log':          log_arr,
            'sign_out':     users.create_logout_url('/'),
        }
        return self.response.write(template.render(template_values))

