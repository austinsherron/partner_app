from collections import defaultdict as dd
from google.appengine.ext import ndb
from models import Invitation


class InvitationModel:

    @staticmethod
    def get_recvd_invites_by_student_and_assign(student, assign_num, active=True):
        return Invitation.query(
            Invitation.invitee == student.key,
            Invitation.assignment_number == assign_num,
            Invitation.active == active
        )


    @staticmethod
    def get_recvd_invites_by_student_and_mult_assigns(student, assigns, active=True, as_dict=True):
        invites = []
        for assign in assigns:
            invites += InvitationModel.get_recvd_invites_by_student_and_assign(student, assign, active)

        if as_dict:
            invite_dict = dd(list)
            for invite in invites:
                invite_dict[invite.assignment_number].append(invite)
            invites = invite_dict

        return invites


    @staticmethod
    def get_sent_invites_by_student_and_assign(student, assign_num, active=True):
        return Invitation.query(
            Invitation.invitor == student.key, 
            Invitation.active == active, 
            Invitation.assignment_number == assign_num 
        )


    @staticmethod
    def get_sent_invites_by_student_and_mult_assigns(student, assigns, active=True):
            invites = []

            for assign in assigns:
                invites += InvitationModel.get_sent_invites_by_student_and_assign(student, assign, active).fetch()

            return invites


    @staticmethod
    def get_all_invites_by_student_and_assign(student, assign_num, active=True, combine=True):
        if combine:
            invites  = InvitationModel.get_recvd_invites_by_student_and_assign(student, assign_num, active)
            invites += InvitationModel.get_sent_invites_by_student_and_assign(student, assign_num, active)
            return invites
        else:
            recvd = InvitationModel.get_recvd_invites_by_student_and_assign(student, assign_num, active)
            sent  = InvitationModel.get_sent_invites_by_student_and_assign(student, assign_num, active)
            return (recvd,sent)
        

    @staticmethod
    def get_open_invitations_for_pair_for_assign(confirming, being_confirmed, assign_num):
        return Invitation.query(
            ndb.OR(Invitation.invitee == confirming.key, Invitation.invitee == being_confirmed.key),
            ndb.OR(Invitation.invitor == being_confirmed.key, Invitation.invitor == confirming.key),
            Invitation.assignment_number == assign_num,
            Invitation.active == True
        )


    @staticmethod
    def get_all_invites_for_pair(confirming, being_confirmed, active=True):
        # this method returns all invitations that involve BOTH members of a student pair
        return Invitation.query(
            ndb.OR(Invitation.invitee == confirming.key, Invitation.invitee == being_confirmed.key),
            ndb.OR(Invitation.invitor == being_confirmed.key, Invitation.invitor == confirming.key),
            Invitation.active == active,
        ).fetch()


    @staticmethod
    def get_all_invitations_involving_students_in_pair(confirming, being_confirmed, assign_num, active=True):
        # this method returns all invitations that involve AT LEAST ONE member of a student pair
        return Invitation.query(
            ndb.OR(
                    ndb.OR(
                        Invitation.invitor == confirming.key, 
                        Invitation.invitor == being_confirmed.key),
                    ndb.OR(
                        Invitation.invitee == confirming.key,
                        Invitation.invitee == being_confirmed.key)),
            Invitation.assignment_number == assign_num,
            Invitation.active == active
        )


    @staticmethod
    def get_all_invitations_involving_student(confirming):
        return Invitation.query(
            ndb.OR(
                Invitation.invitor == confirming.key, 
                Invitation.invitee == confirming.key),
            )
