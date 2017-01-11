from google.appengine.ext import ndb
from models import Evaluation
from models import Partnership


class PartnershipModel:

    @staticmethod
    def get_active_partnerships_involving_students_by_assign(students, assign_num):
        # this method returns all partnerships that involve AT LEAST ONE student in the pair
        return Partnership.query(
            Partnership.members.IN([student.key for student in students]),
            Partnership.assignment_number == assign_num,
            Partnership.active == True
        )


    @staticmethod
    def get_partnerships_for_students_by_assign(students, assign):
        # this method returns all partnerships that involve BOTH students in the pair
        constraints = [
            Partnership.active == True,
            Partnership.assignment_number == assign
        ]
        for student in students:
            constraints += [Partnership.members == student.key]
        return Partnership.query(*constraints).fetch()


    @staticmethod
    def get_active_partner_history_for_student(student, quarter, year, fill_gaps=None):
        history = Partnership.query(
            Partnership.members == student.key,
            Partnership.active == True,
            Partnership.quarter == quarter,
            Partnership.year == year
        ).order(Partnership.assignment_number)

        if type(fill_gaps) is list:
            partners = []
            for i in fill_gaps:
                partnership = history.filter(Partnership.assignment_number == i).get()

                if not partnership:
                    partners.append('No Selection')
                elif len(partnership.members) > 1:
                    #partners.append(', '.join([str(member.get().email for members in partnership.members if member != student.key)]))
                    emails = map(lambda x: str(x.get().email), partnership.members)
                    partners.append(', '.join(filter(lambda x: x != student.email, emails)))
                else:
                    partners.append('No Partner')
            return partners

        return history


    @staticmethod
    def get_all_partner_history_for_student(student, quarter, year):
        return Partnership.query(
            Partnership.members == student.key,
            Partnership.quarter == quarter,
            Partnership.year == year
        ).order(Partnership.assignment_number)


    @staticmethod
    def get_partner_from_partner_history_by_assign(student, partners, assign_num):
        current_partnership = partners.filter(
            Partnership.active == True,
            Partnership.assignment_number == assign_num
        ).get()

        if current_partnership:
            if len(current_partnership.members) == 1:
                return ['No Partner']
            else:
                return [member.get() for member in current_partnership.members if member != student.key]

        return []


    @staticmethod
    def get_all_partnerships_for_assign(quarter, year, assign_num, active=True):
        return Partnership.query(
            Partnership.quarter == quarter,
            Partnership.year == year,
            Partnership.assignment_number == assign_num,
            Partnership.active == active,
        ).fetch()


    @staticmethod
    def get_partnerships_by_student_and_assign(student, quarter, year, assign_num, active=True):
        return Partnership.query(
            Partnership.members == student.key,
            Partnership.quarter == quarter,
            Partnership.year == year,
            Partnership.assignment_number == assign_num,
            Partnership.active == active,
        )


    @staticmethod
    def get_partnerships_for_students(students):
        constraints = [Partnership.active == True]
        for student in students:
            constraints += [Partnership.members == student.key]
        return Partnership.query(*constraints).fetch()


    @staticmethod
    def get_inactive_partnerships_by_student_and_assign(student, assign_num):
        return Partnership.query(
            Partnership.members == student.key,
            Partnership.assignment_number == assign_num,
            Partnership.active == False
        )


    @staticmethod
    def get_solo_partnerships_by_assign(quarter, year, assign_num, active=True):
        return Partnership.query(
            Partnership.quarter == quarter,
            Partnership.year == year,
            Evaluation.assignment_number == assign_num,
            Partnership.solo == True,
            Partnership.active == active
        )


    @staticmethod
    def get_all_partnerships(quarter, year, active=True):
        return Partnership.query(
            Partnership.quarter == quarter,
            Partnership.year == year,
            Partnership.active == active,
        )


#    @staticmethod
#    def get_all_partnerships_by_lab(quarter, year, lab, active=True):
#        return Partnership.query(
#            Partnership.quarter == quarter,
#            Partnership.year == year,
#            Partnership.active == active,
#        )


    @staticmethod
    def student_has_partner_for_assign(student, assign):
        quarter  = student.quarter
        year     = student.year
        partners = PartnershipModel.get_partnerships_by_student_and_assign(student, quarter, year, assign).fetch()
        return bool(partners)


    @staticmethod
    def create_partnership(students, assign):
        partnership = Partnership(
            members           = map(lambda x: x.key, students),
            assignment_number = assign,
            active            = True,
            year              = students[0].year,
            quarter           = students[0].quarter
        )

        partnership.put()
        return partnership


    @staticmethod
    def were_partners_previously(students):
        return bool(PartnershipModel.get_partnerships_for_students(students))


    @staticmethod
    def cancel_partnership(student, partnership):
        partnership.cancelled.append(student)
        if set(partnership.members) == set(partnership.cancelled):
            partnership.active = False

        partnership.put()
        return partnership


    @staticmethod
    def uncancel_partnership(student, partnership):
        del partnership.cancelled[partnership.cancelled.index(student.key)]
        partnership.put()
        return partnership


    @staticmethod
    def add_members_to_partnership(students, partnership):
        partnership.members += [student.key for student in students]
        partnership.put()
        return partnership
