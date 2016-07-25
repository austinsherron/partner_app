import jinja2
import os

from google.appengine.ext import ndb
from google.appengine.api import users
from webapp2_extras.appengine.users import login_required

from handler import CustomHandler


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class HelpPage(CustomHandler):
    def get(self):
        user = users.get_current_user()
        template_values = {}

        if user:
            template_values['user'] = user.email()
            template_values['sign_out'] = users.create_logout_url('/')
        else:
            template_values['sign_in'] = users.create_login_url('/partner')

        template = JINJA_ENV.get_template('/templates/partner_instructions.html')
        self.response.write(template.render(template_values))


class ImageHandler(CustomHandler):

    def get(self, key):
        # cast key from url from str to ndb.Key
        key = ndb.Key(urlsafe=key)
        # grab student associated w/ key and the corresponding avatar
        image = key.get().avatar 
        # set content type header...
        self.response.headers['Content-Type'] = 'image/png'
        # and 
        return self.response.out.write(image)
