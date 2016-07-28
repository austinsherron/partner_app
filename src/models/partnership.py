from google.appengine.ext import ndb
from models import Evaluation
from models import Partnership


class PartnershipModel:

    @staticmethod
    def get_active_partnerships_involving_students_by_assign(students, assign_num):
        # this method returns all partnerships that involve AT LEAST ONE student in the pair
        return Partnership.query(
            Partnership.members.IN(students),
            Partnership.assignment_number == assign_num,
            Partnership.active == True
        )


    @staticmethod
    def get_partnerships_for_pair_by_assign(selector, selected, assign):
        # this method returns all partnerships that involve BOTH students in the pair
        return Partnership.query(
            ndb.OR(Partnership.initiator == selector.key, Partnership.initiator == selected.key),
            ndb.OR(Partnership.acceptor == selector.key, Partnership.acceptor == selected.key),
            Partnership.active == True,
            Partnership.assignment_number == assign
        ).fetch()

    
    @staticmethod
    def get_active_partner_history_for_student(student, quarter, year, fill_gaps=None):
        history = Partnership.query(
            ndb.OR(Partnership.initiator == student.key, Partnership.acceptor == student.key),
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
                elif partnership.acceptor and partnership.initiator:
                    acceptor = partnership.acceptor
                    initiator = partnership.initiator
                    partners.append(acceptor.get().email if acceptor != student.key else initiator.get().email)
                elif partnership.initiator and not partnership.acceptor:
                    partners.append('No Partner')
            return partners

        return history


    @staticmethod
    def get_all_partner_history_for_student(student, quarter, year):
        return Partnership.query(
            ndb.OR(Partnership.initiator == student.key, Partnership.acceptor == student.key),
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
            if current_partnership.initiator.get().studentid != student.studentid:
                return current_partnership.initiator.get()
            else: 
                if current_partnership.acceptor:
                    return current_partnership.acceptor.get()
                else:
                    return 'No Partner'


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
            ndb.OR(Partnership.initiator == student.key, Partnership.acceptor == student.key),
            Partnership.quarter == quarter,
            Partnership.year == year,
            Partnership.assignment_number == assign_num,
            Partnership.active == active,
        )


    @staticmethod
    def get_partnerships_for_pair(selector, selected):
        return Partnership.query(
            ndb.OR(Partnership.initiator == selector.key, Partnership.initiator == selected.key),
            ndb.OR(Partnership.acceptor == selector.key, Partnership.acceptor == selected.key),
            Partnership.active == True
        ).fetch()
        

    @staticmethod
    def get_inactive_partnerships_by_student_and_assign(student, assign_num):
        return Partnership.query(
            ndb.OR(Partnership.initiator == student.key, Partnership.acceptor == student.key),
            Partnership.assignment_number == assign_num,
            Partnership.active == False
        )


    @staticmethod
    def get_solo_partnerships_by_assign(quarter, year, assign_num, active=True):
        return Partnership.query(
            Partnership.quarter == quarter,
            Partnership.year == year,
            Evaluation.assignment_number == assign_num,
            Partnership.acceptor == None,
            Partnership.active == active
        )


    @staticmethod
    def get_all_partnerships(quarter, year, active=True):
        return Partnership.query(
            Partnership.quarter == quarter,
            Partnership.year == year,
            Partnership.active == active,
        )


    @staticmethod
    def get_all_partnerships_by_lab(quarter, year, lab, active=True):
        return Partnership.query(
            Partnership.quarter == quarter,
            Partnership.year == year,
            Partnership.active == active,
        )


    @staticmethod
    def student_has_partner_for_assign(student, assign):
        quarter  = student.quarter
        year     = student.year
        partners = PartnershipModel.get_partnerships_by_student_and_assign(student, quarter, year, assign).fetch()
        return bool(partners)


    @staticmethod
    def create_partnership(students, assign):
        partnership = Partnership(
            members           = students,
            assignment_number = for_assign, 
            active            = True,
            year              = students[0].year, 
            quarter           = students[0].quarter
        )

        partnership.put()
        return partnership
