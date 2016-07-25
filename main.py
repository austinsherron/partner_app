import webapp2

from src.controllers import admin
from src.controllers import evaluations
from src.controllers import partners
from src.controllers import browse_partners
from src.controllers import landing
from src.controllers import misc
from src.controllers import profile
from src.controllers import view_history


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
    ('/partner/confirm', partners.ConfirmPartner),
    ('/partner/history', view_history.ViewHistory),
    ('/partner/history/invitations', view_history.ViewInvitationHistory),
    ('/partner/instructions', misc.HelpPage),
    ('/images/(.*)', misc.ImageHandler),
    ('/admin', admin.MainAdmin),
    ('/admin/assignment/add', admin.AddAssignment),
    ('/admin/assignment/edit', admin.EditAssignment),
    ('/admin/assignment/view', admin.ManageAssignments),
    ('/admin/cleardb', admin.ClearDB),
    ('/admin/evaluations/view', admin.ViewEvals),
    ('/admin/partners/add', admin.AddPartnership),
    ('/admin/partners/view', admin.ViewPartnerships),
    ('/admin/roster/upload', admin.UploadRoster),
    ('/admin/roster/view', admin.ViewRoster),
    ('/admin/student/add', admin.AddStudent),
    ('/admin/students/deactivate', admin.DeactivateStudents),
    ('/admin/student/edit', admin.EditStudent),
    ('/admin/student/view', admin.ViewStudent),
    ('/admin/settings/update', admin.UpdateSettings),
], config=config, debug=True)
