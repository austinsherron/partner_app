from models import Course
from models import Setting


class CourseModel:

    @staticmethod
    def get_courses_by_student(student, active=True):
        return Course.query(
            Course.students == student.key,
            Course.active == active,
        )
        

    @staticmethod
    def get_courses_by_instructor(instructor, active=True):
        return Course.query(
            Course.instructors == instructor.key,
            Course.active == active,
        )


    @staticmethod
    def get_all_courses_by_instructor(instructor):
        courses  = CourseModel.get_courses_by_instructor(instructor).fetch()
        courses += CourseModel.get_courses_by_instructor(instructor, active=False).fetch()
        return courses


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


    @staticmethod
    def update_active_status(course, active):
        course.active = active
        course.put()
        return course
