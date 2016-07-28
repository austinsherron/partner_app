from models import Course


class CourseModel:

    @staticmethod
    def get_courses_by_student(student):
        return Course.query(
            Course.students == student.key
        )
