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


JINJA_ENV = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname('app.yaml')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape=True)


class AddInstructor(BaseHandler):

    #@admin_required
    def get(self):
        pass


    #@admin_required
    def post(self):
        pass


class ViewInstructors(BaseHandler):

    #@admin_required
    def get(self):
        pass

