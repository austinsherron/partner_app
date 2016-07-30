

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
    def sent_invitation(student):
        message  = 'Invitation to ' + str(student.last_name) + ', '
        message += str(student.first_name) + ' confirmed. Please refresh the page.'
        return message


    @staticmethod
    def partnership_cancelled():
        message  = 'You have requested to opt-out of this partnership.'
        message += ' All group members must opt-out before the partnership is dissolved.'
        return message


    @staticmethod
    def partnership_uncancelled():
        message  = 'You have requested to opt-in to this partnership.'
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
    def invitation_declined():
        return 'Invitation declined.'


    @staticmethod
    def choose_a_course():
        return 'Please choose a course'


    @staticmethod
    def course_added(name):
        return 'You have successfully added a course (' + name + ')'


    @staticmethod
    def deactivated_course(name):
        return 'You have deactivated course ' + name


    @staticmethod
    def activated_course(name):
        return 'You have activated course ' + name
