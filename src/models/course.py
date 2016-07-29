from models import Course
from models import Setting


class CourseModel:

    @staticmethod
    def get_courses_by_student(student):
        return Course.query(
            Course.students == student.key
        )
        

    @staticmethod
    def get_courses_by_instructor(instructor):
        return Course.query(
            Course.instructors == instructor.key
        )


    @staticmethod
    def create_course(quarter, year, name, abbr_name, instructor):
        course = Course()

        course.quarter   = quarter
        course.year      = year
        course.name      = name
        course.abbr_name = abbr_name
        course.instructors.append(instructor.key)

        setting = Setting(year=year, quarter=quarter)
        setting.put()

        course.setting = setting.key
        course.put()
        return course
