import datetime 
import jinja2
import os

from datetime import timedelta as td
from google.appengine.api import users
from webapp2_extras.appengine.users import admin_required

from models import Assignment
from src.handler.base_handler import BaseHandler
from src.helpers.admin_helpers import make_date
from src.helpers.helpers import get_sess_val, get_sess_vals
from src.models.assignment import AssignmentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class AddAssignment(BaseHandler):

    #@admin_required
    def get(self):
        template = JINJA_ENV.get_template('/templates/admin_add_assignment.html')

        temp = get_sess_vals(self.session, 'quarter', 'year')                   # try grabbing quarter/year from session
        if not temp:                                                            # redirect with error if it doesn't exist
            return self.redirect('/admin?message=Please set a current quarter and year')
        quarter,year = temp

        last_assign = AssignmentModel.get_assign_n(quarter, year, -1)
        last_num    = 0 if not last_assign else last_assign.number
        today       = datetime.date.today().strftime("%Y-%m-%d")

        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded 
        quarters        = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        template_values = {                                                        
            'year':     year,
            'quarter':  quarter,
            'quarters': sorted(quarters.items()),
            'last_num': last_num,
            'today':    today,
            'user':     users.get_current_user(),
            'sign_out': users.create_logout_url('/'),
            'fid':      (last_assign.fade_in_date + td(days=7)).strftime('%Y-%m-%d') if last_assign else today,
            'fit':      last_assign.fade_in_date.strftime('%H:%M') if last_assign else '00:00',
            'dd':       (last_assign.due_date + td(days=7)).strftime('%Y-%m-%d') if last_assign else today,
            'dt':       last_assign.due_date.strftime('%H:%M') if last_assign else '00:00',
            'cd':       (last_assign.close_date + td(days=7)).strftime('%Y-%m-%d') if last_assign else today,
            'ct':       last_assign.close_date.strftime('%H:%M') if last_assign else '00:00',
            'eod':      (last_assign.eval_open_date + td(days=7)).strftime('%Y-%m-%d') if last_assign else today,
            'eot':      last_assign.eval_open_date.strftime('%H:%M') if last_assign else '00:00',
            'ecd':      (last_assign.eval_date + td(days=7)).strftime('%Y-%m-%d') if last_assign else today,
            'ect':      last_assign.eval_date.strftime('%H:%M') if last_assign else '00:00',
            'fod':      (last_assign.fade_out_date + td(days=7)).strftime('%Y-%m-%d') if last_assign else today,
            'fot':      last_assign.fade_out_date.strftime('%H:%M') if last_assign else '00:00',
        }
        return self.response.write(template.render(template_values))            


    def post(self):
        # URL will contain 'edit' argument if this request is coming from an assignment edit form
        edit    = self.request.get('edit')
        year    = int(self.request.get('year'))            
        quarter = int(self.request.get('quarter'))
        number  = int(self.request.get('assign_num'))

        # if this request didn't come from the edit form...
        if not edit:
            # ...create new assignment and set PK values
            assignment         = Assignment()
            assignment.year    = int(self.request.get('year'))
            assignment.quarter = int(self.request.get('quarter'))
            assignment.number  = int(self.request.get('assign_num'))
        else:
            # ...else get assignment
            assignment = AssignmentModel.get_assign_by_number(quarter, year, number)

        # if an assignment with the same PK values exist, redirect with error; assignment isn't created
        if AssignmentModel.get_assign_by_number(assignment.quarter, assignment.year, assignment.number) and not edit:
            message = 'That assignment is already in the database'
            return self.redirect('/admin/assignment/add?message=' + message)
        else:
            # set dates/times
            fade_in_date            = str(self.request.get('fade_in_date')).split('-')
            fade_in_time            = str(self.request.get('fade_in_time')).split(':')
            assignment.fade_in_date = make_date(fade_in_date, fade_in_time)

            due_date            = str(self.request.get('due_date')).split('-')
            due_time            = str(self.request.get('due_time')).split(':')
            assignment.due_date = make_date(due_date, due_time)

            close_date            = str(self.request.get('close_date')).split('-')
            close_time            = str(self.request.get('close_time')).split(':')
            assignment.close_date = make_date(close_date, close_time)

            eval_date            = str(self.request.get('eval_date')).split('-')
            eval_time            = str(self.request.get('eval_time')).split(':')
            assignment.eval_date = make_date(eval_date, eval_time)

            eval_open_date            = str(self.request.get('eval_open_date')).split('-')
            eval_open_time            = str(self.request.get('eval_open_time')).split(':')
            assignment.eval_open_date = make_date(eval_open_date, eval_open_time)

            fade_out_date            = str(self.request.get('fade_out_date')).split('-')
            fade_out_time            = str(self.request.get('fade_out_time')).split(':')
            assignment.fade_out_date = make_date(fade_out_date, fade_out_time)

            # set 'current' value (always false due to query updates)
            assignment.current = False
            assignment.put()
    
            message  = 'Assignment ' + str(assignment.number) + ' for quarter '
            message += str(assignment.quarter) + ' ' + str(assignment.year) 
            # changed success message depending on whether an assignment was just create/updated
            message += ' successfully ' + ('updated' if edit else 'added')        

            # redirct according to action (add vs edit)
            redirect_link = '/admin/assignment/' + ('view' if edit else 'add') 

            return self.redirect(redirect_link + '?message=' + message)


class EditAssignment(BaseHandler):

    def get(self):
        quarter    = int(self.request.get('quarter'))                   # grab quarter, year, and assign num from URL
        year       = int(self.request.get('year'))                        
        number     = int(self.request.get('number'))
        assignment = AssignmentModel.get_assign_by_number(quarter, year, number)             

        temp = get_sess_vals(self.session, 'quarter', 'year')           # try to grab current quarter/year from session
        if not temp:                                                    # redirect with error if it doesn't exist
            return self.redirect('/admin?message=Please set a current quarter and year')
        quarter,year = temp
        # pass map of quarter DB representations (ints) to string representation
        # TODO:
        #    quarters should not be hardcoded 
        quarters        = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        template_values = {                                                
            'a':        assignment,
            'fid':      assignment.fade_in_date.strftime('%Y-%m-%d'),
            'fit':      assignment.fade_in_date.strftime('%H:%M'),
            'dd':       assignment.due_date.strftime('%Y-%m-%d'),
            'dt':       assignment.due_date.strftime('%H:%M'),
            'cd':       assignment.close_date.strftime('%Y-%m-%d'),
            'ct':       assignment.close_date.strftime('%H:%M'),
            'eod':      assignment.eval_open_date.strftime('%Y-%m-%d') if assignment.eval_open_date else '00-00-0000',
            'eot':      assignment.eval_open_date.strftime('%H:%M') if assignment.eval_open_date else '00:00',
            'ecd':      assignment.eval_date.strftime('%Y-%m-%d'),
            'ect':      assignment.eval_date.strftime('%H:%M'),
            'fod':      assignment.fade_out_date.strftime('%Y-%m-%d'),
            'fot':      assignment.fade_out_date.strftime('%H:%M'),
            'user':     users.get_current_user(),
            'sign_out': users.create_logout_url('/'),
            'quarter':  quarter,
            'quarters': sorted(quarters.items()),
            'year':     year,
            'number':   number,
        }
        template = JINJA_ENV.get_template('/templates/admin_assignment_edit.html')
        return self.response.write(template.render(template_values))    


class ManageAssignments(BaseHandler):

    #@admin_required
    def get(self):
        quarter_map = {1: 'Fall', 2: 'Winter', 3: 'Spring', 4: 'Summer'}
        quarter     = self.request.get('quarter')                           # try grabbing quarter/year from URL
        year        = self.request.get('year')

        if not quarter or not year:                                         # if they don't exist, try grabbing from session
            temp = get_sess_vals(self.session, 'quarter', 'year')

            if not temp:                                                    # if they don't exist there, redirect with error
                return self.redirect('/admin?message=Please set a current quarter and year')
        
            quarter,year = temp                                                    

        assignments = AssignmentModel.get_assigns_for_quarter(int(quarter), int(year))        

        template        = JINJA_ENV.get_template('/templates/admin_assignment_view.html')
        template_values = {                                                    
            'assignments':  assignments.order(Assignment.number),
            'quarter_name': quarter_map[int(quarter)],
            'quarter':      int(quarter),
            'year':         int(year),
            'user':         users.get_current_user(),
            'sign_out':     users.create_logout_url('/'),
        }
        return self.response.write(template.render(template_values))        


