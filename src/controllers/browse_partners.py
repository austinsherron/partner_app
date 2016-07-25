import jinja2
import os

from datetime import date, datetime, timedelta
from google.appengine.api import images, users
from webapp2_extras.appengine.users import login_required

from handler import CustomHandler
from src.models.assignment import AssignmentModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class BrowseForPartners(CustomHandler):

    @login_required
    def get(self):
        quarter  = SettingModel.quarter()
        year     = SettingModel.year()
        user     = users.get_current_user()
        selector = StudentModel.get_student_by_email(quarter, year, user.email())

        if not selector:
            return self.redirect('/partner')

        # use selector info to find students in same lab section
        selectees          = StudentModel.get_students_by_lab(quarter, year, selector.lab)
        current_assignment = AssignmentModel.get_active_assign_with_latest_fade_in_date(quarter, year)

        # if there are no assignments for this quarter, redirect to avoid errors
        if not current_assignment:
            return self.redirect('/partner?message=There are no assignments open for partner selection.')
            
        # get error message, if any
        e = self.request.get('error')        

        # check to see if partner selection period has closed
        selection_closed = (datetime.now() - timedelta(hours=8) > current_assignment.close_date)

        # get all current_partnerships for partnership status
        partnerships = PartnershipModel.get_all_partnerships_for_assign(quarter, year, current_assignment.number)
        partnerships = {p.initiator for p in partnerships} | {p.acceptor for p in partnerships}

        # build dict to store information about partnership status
        selectees = sorted({s.ucinetid: (s.key in partnerships,s) for s in selectees}.items(), key=lambda x: x[1][1].last_name)

        # pass template values...
        template_values = {
            'error':            e,
            'selector':         selector,                                  
            'selectees':        selectees,                                
            'selection_closed': selection_closed,
            'current':          current_assignment,
            'user':             user,
            'sign_out':         users.create_logout_url('/'),
        }
        template = JINJA_ENV.get_template('/templates/partner_browse.html')
        self.response.write(template.render(template_values))

