

class MessageModel:

    @staticmethod
    def already_has_partner(admin, accepting=True):
        if admin:
            return 'This student already has a partner, and therefore can\'t enter into another partnership.'
        elif accepting:
            return 'You already have a partner, so you can\'t accept this invitation.'
        else:
            return 'You already have a partner, so you can\'t send this invitation.'


    @staticmethod
    def confirm_solo_partnership(student):
        return 'Solo partnership for ' + str(student.first_name) + ' ' + str(student.last_name) + ' confirmed.'


    @staticmethod
    def confirm_partnership(students, admin, student=None):
        if not admin and student:
            others   = filter(lambda x: x.key != student.key, students)
            others   = ', '.join(map(lambda x: str(x.first_name) + ' ' + str(x.last_name), others))
            message  = 'Partnership with ' + others + ' confirmed.'
            message += ' Please refresh the page.'
            return message
        elif admin:
            others  = ', '.join(map(lambda x: str(x.first_name) + ' ' + str(x.last_name), students))
            message = 'Partnership between ' + others + ' created.'
            return message
        else:
            ''

    @staticmethod
    def worked_previously(student):
        e  = 'Sorry, you\'ve already worked with, or are currently working with '
        e += str(student.last_name) + ', ' + str(student.first_name)
        e += '. If you think you have a legitimate reason to repeat a partnership'
        e += ', please contact your TA'
        return e


    @staticmethod
    def have_open_invitations(student):
        e  = 'You already have open invitations with '
        e += str(student.last_name) + ', ' + str(student.first_name)
        return e

    @staticmethod
    def page_not_found():
        return "The page you are looking for does not exist!"

    @staticmethod
    def sent_invitation(student):
        message  = 'Invitation to ' + str(student.last_name) + ', '
        message += str(student.first_name) + ' confirmed.'
        return message


    @staticmethod
    def partnership_cancelled(assgn_num):
        message  = 'You have requested to opt-out of your partnership for assignment %d.' % assgn_num
        message += 'Please make sure to notify your old partner of your decision.'
        return message


    @staticmethod
    def partnership_uncancelled():
        message  = 'You have requested to uncancel your partnership for this assignment.'
        message += ' This partnership can\'t be dissolved without your consent.'
        return message


    @staticmethod
    def assignment_edited_or_added(quarter, year, assign, edit):
        message  = 'Assignment ' + str(assign) + ' for quarter '
        message += str(quarter) + ' ' + str(year)
        # changed success message depending on whether an assignment was just create/updated
        message += ' successfully ' + ('updated' if edit else 'added')
        return message

    @staticmethod
    def assignment_deleted(quarter, year, assign):
        message  = 'Assignment ' + str(assign) + ' for quarter '
        message += str(quarter) + ' ' + str(year)
        # changed success message depending on whether an assignment was just create/updated
        message += ' successfully deleted'
        return message

    @staticmethod
    def invitation_declined():
        return 'Invitation declined.'
