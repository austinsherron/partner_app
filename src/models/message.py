

class MessageModel:

    @staticmethod
    def already_has_partner(admin):
        if admin:
            return 'This student already has a partner, and therefore can\'t enter into another partnership.'
        else:
            return 'You already have a partner, so you can\'t accept this invitation.'


    @staticmethod
    def confirm_solo_partnership(student):
        return 'Solo partnership for ' + str(student.first_name) + ' ' + str(student.last_name) + ' confirmed.'


    @staticmethod
    def confirm_partnership(students, admin, student=None):
        if not admin and student:
            others   = filter(lambda x: x.key != student.key, students)
            others   = ', '.join(map(lambda x: str(x.first_name) + ' ' + str(x.last_name), others))
            message  = 'Partnership with ' + others + ' confirmed'.
            message += ' Please refresh the page.'
            return message
        elif admin:
            others  = ', '.join(map(lambda x: str(x.first_name) + ' ' + str(x.last_name), students))
            message = 'Partnership between ' + others + ' created.'
            return message
        else:
            ''


            



