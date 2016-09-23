from models import Student


class StudentModel:

    @staticmethod
    def get_student_by_email(quarter, year, email):
        return Student.query(
            Student.quarter == quarter, 
            Student.year == year, 
            Student.email == unicode(email),
            Student.active == True
        ).get() 


    @staticmethod
    def get_students_by_active_status(quarter, year, active=True):
        return Student.query(
            Student.quarter == quarter, 
            Student.year == year, 
            Student.active == active
        )


    @staticmethod
    def get_student_by_student_id(quarter, year, studentid, active=True):
        return Student.query(
            Student.quarter == quarter,
            Student.year == year, 
            Student.studentid == int(studentid),
            Student.active == active
        ).get()


    @staticmethod
    def get_students_by_lab(quarter, year, lab, active=True):
        return Student.query(
            Student.quarter == quarter,
            Student.year == year, 
            Student.lab == lab,
            Student.active == active
        )

    @staticmethod
    def get_students_by_student_ids(quarter, year, student_ids):
        return Student.query(
            Student.studentid.IN(student_ids),
            Student.year == year,
            Student.quarter == quarter
        )
