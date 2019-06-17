from google.appengine.ext import ndb
from models import Log


class LogModel:

    @staticmethod
    def get_log_by_student(student, quarter, year):
        return Log.query(
            Log.owner == student.key, 
            Log.quarter == quarter,
            Log.year == year
        )


    @staticmethod
    def get_all_quarter_logs(quarter, year):
        return Log.query(
            Log.quarter == quarter,
            Log.year == year
        )
