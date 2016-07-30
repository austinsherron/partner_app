from models import Instructor


class InstructorModel:

    @staticmethod
    def get_instructor_by_email(email):
        return Instructor.query(
            Instructor.email == unicode(email),
        ).get() 
