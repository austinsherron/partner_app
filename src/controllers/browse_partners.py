import jinja2
import os

from datetime import date, datetime, timedelta
from google.appengine.api import images, users
from webapp2_extras.appengine.users import login_required

from src.handler.base_handler import BaseHandler
from src.models.assignment import AssignmentModel
from src.models.partnership import PartnershipModel
from src.models.settings import SettingModel
from src.models.student import StudentModel


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class BrowseForPartners(BaseHandler):

    @login_required
    def get(self):
        quarter  = SettingModel.quarter()
        year     = SettingModel.year()
        user     = users.get_current_user()
        selector = StudentModel.get_student_by_email(quarter, year, user.email())
        student = StudentModel.get_student_by_email(quarter, year, user.email())
        repeat = SettingModel.repeat_partners()

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
        selection_closed = (datetime.now() - timedelta(hours=7) > current_assignment.close_date)

        # get all current_partnerships for partnership status
        partnerships = PartnershipModel.get_all_partnerships_for_assign(quarter, year, current_assignment.number)
        partner_history = PartnershipModel.get_all_partner_history_for_student(student, quarter, year)
        members      = []
        for p in partner_history:
            if p.active:
                members += p.members
        for p in partnerships:
            if p.members not in members:
                members += p.members
        # build dict to store information about partnership status
        available = []
        for s in selectees:
            if (s.key not in members) or repeat:
                available.append((s.ucinetid,(s.key in partnerships, s)))
        available = sorted(available, key=get_result_priority)
        # pass template values...
        template_values = {
            'error':            e,
            'student': student,
            'selector':         selector,
            'selectees':        available,
            'selection_closed': selection_closed,
            'current':          current_assignment,
            'user':             user,
            'sign_out':         users.create_logout_url('/'),
        }
        template = JINJA_ENV.get_template('/templates/partner_browse.html')
        self.response.write(template.render(template_values))

def get_shared_hours(a1, a2):
    return 0
    total = 0;
    for i in range(len(a1)):
        if a1[i]=="1" and a2[i] == "1":
            total += 1
    return total/2.0

def get_result_priority(result):
    return 0
    student = result[1][1]
    quarter  = SettingModel.quarter()
    year     = SettingModel.year()
    user     = users.get_current_user()
    selector = StudentModel.get_student_by_email(quarter, year, user.email())

    their_availability = student.availability
    my_availabiliy = selector.availability

    #TODO RE IMPLIMENT THIS
    shared_hours = 0#get_shared_hours(my_availability, their_availability)
    
    ability_dif = abs(student.programming_ability-selector.programming_ability)

    if shared_hours >= 4:
        return 10-ability_dif
    else:
        return 10-(ability_dif + (4-shared_hours)/(5*15))

    
