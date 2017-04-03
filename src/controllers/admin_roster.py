import jinja2
import os

from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras.appengine.users import admin_required

from models import Student, Setting
from src.handler.base_handler import BaseHandler
from src.helpers.helpers import get_sess_val, get_sess_vals
from src.models.assignment import AssignmentModel
from src.models.student import StudentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class UploadRoster(BaseHandler):

    @admin_required
    def get(self):
        quarter = self.request.get('quarter')                                  # try grabbing quarter/year from URL
        year    = self.request.get('year')

        if not quarter or not year:                                            # if they don't exist, try grabbing from session
            temp = get_sess_vals(self.session, 'quarter', 'year')              # try grabbing quarter/year from session
            if not temp:                                                       # redirect with error if it doesn't exist
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp

        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded 
        quarters = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}

        template_values = {                                                        
            'user':     users.get_current_user(),
            'sign_out': users.create_logout_url('/'),
            'quarter':  int(quarter),
            'year':     int(year),
            'quarters': sorted(quarters.items()),
            'message':  self.request.get('message'),
        }
        template = JINJA_ENV.get_template('/templates/admin_upload.html')
        return self.response.write(template.render(template_values))            


    def post(self):
        try:
            file = self.request.get('the_file')                               
            file = file.strip().split('\n')                                    

            quarter  = int(self.request.get('quarter'))                       
            year     = int(self.request.get('year'))
            num_labs = 0
            
            # students to be uploaded 
            students = []
            # to check for duplicates in roster
            student_cache = set()

            # grab students in DB (active and not active) 
            existing_students  = StudentModel.get_students_by_active_status(quarter, year).fetch()    
            existing_students += StudentModel.get_students_by_active_status(quarter, year, active=False).fetch()
            existing_students  = dict(map(lambda x: (int(x.studentid), x), existing_students))

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

                    # ...or if they've switched labs; if so, update lab num...
                    if existing_student.lab != int(row[5]):
                        existing_student.lab = int(row[5])
                        students.append(existing_student)

                    # ...to see which students have dropped the class, remove active students from existing_students
                    del existing_students[studentid]
                    # ...and continue to next student
                    continue

                # create student object
                student = Student()

                student.studentid  = studentid
                student.last_name  = row[1].strip().title()
                student.last_name  = row[1].strip('"').title()
                student.first_name = row[2].strip().title()
                student.first_name = row[2].strip('"').title()
                student.ucinetid   = row[3].lower().strip()
                student.email      = row[4].lower().strip()
                student.lab        = int(row[5])
                student.quarter    = quarter
                student.year       = year
                student.active     = True
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


class ViewRoster(BaseHandler):

    @admin_required
    def get(self):
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded 
        quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        quarter     = self.request.get('quarter')                              # try grabbing quarter/year from URL
        year        = self.request.get('year')

        if not quarter or not year:                                            # if they don't exist, try grabbing from session
            temp = get_sess_vals(self.session, 'quarter', 'year')
            if not temp:                                                       # if they don't exist there, redirect with error
                return self.redirect('/admin?message=Please set a current quarter and year')
            quarter,year = temp                                                    

        quarter,year      = int(quarter), int(year)
        active_students   = StudentModel.get_students_by_active_status(quarter, year).fetch()    
        inactive_students = StudentModel.get_students_by_active_status(quarter, year, active=False).fetch()
        active_num        = len(active_students)                            
        inactive_num      = len(inactive_students)

        template        = JINJA_ENV.get_template('/templates/admin_view.html')
        template_values = {                            
            'students':     sorted(active_students + inactive_students, key=lambda x: (x.lab, x.last_name)),
            'quarter_name': quarter_map[int(quarter)],
            'quarter':      int(quarter),
            'year':         int(year),
            'student_num':  active_num + inactive_num,
            'active_num':   active_num,
            'inactive_num': inactive_num,
            'user':         users.get_current_user(),
            'sign_out':     users.create_logout_url('/'),
            'message':      self.request.get('message'),
        }
        return self.response.write(template.render(template_values))        


