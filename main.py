import webapp2

from src.controllers import admin_assignment
from src.controllers import admin_eval
from src.controllers import admin_landing
from src.controllers import admin_misc
from src.controllers import admin_partnership
from src.controllers import admin_roster
from src.controllers import admin_student
from src.controllers import evaluations
from src.controllers import partners
from src.controllers import browse_partners
from src.controllers import landing
from src.controllers import misc
from src.controllers import profile
from src.controllers import view_history
from src.controllers import partner_more_info


config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'some-secret-key',
}

application = webapp2.WSGIApplication([
    ('/', landing.Main),
    ('/partner', landing.MainPage),
    ('/partner/edit/profile', profile.EditProfile),
    ('/partner/evaluation', evaluations.EvaluatePartner),
    ('/partner/selection', partners.SelectPartner),
    ('/partner/browse', browse_partners.BrowseForPartners),
    ('/partner/cancel', partners.CancelPartner),
    ('/partner/confirm', partners.ConfirmPartner),
    ('/partner/history', view_history.ViewHistory),
    ('/partner/history/invitations', view_history.ViewInvitationHistory),
    ('/partner/instructions', misc.HelpPage),
    ('/partner/invitation/confirm', partners.ConfirmInvitation),
    ('/partner/invitation/decline', partners.DeclineInvitation),
    ('/partner/more', partner_more_info.PartnerMoreInfo),
    ('/images/(.*)', misc.ImageHandler),
    ('/admin', admin_landing.MainAdmin),
    ('/admin/assignment/add', admin_assignment.AddAssignment),
    ('/admin/assignment/edit', admin_assignment.EditAssignment),
    ('/admin/assignment/view', admin_assignment.ManageAssignments),
    ('/admin/cleardb', admin_misc.ClearDB),
    ('/admin/evaluations/view', admin_eval.ViewEvals),
    ('/admin/partners/add', admin_partnership.AddPartnership),
    ('/admin/partners/view', admin_partnership.ViewPartnerships),
    ('/admin/roster/upload', admin_roster.UploadRoster),
    ('/admin/roster/view', admin_roster.ViewRoster),
    ('/admin/student/add', admin_student.AddStudent),
    ('/admin/students/deactivate', admin_student.DeactivateStudents),
    ('/admin/student/edit', admin_student.EditStudent),
    ('/admin/student/view', admin_student.ViewStudent),
    ('/admin/settings/update', admin_misc.UpdateSettings),
], config=config, debug=True)
