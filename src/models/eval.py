from google.appengine.ext import ndb
from models import Evaluation


class EvalModel:

    @staticmethod
    def get_existing_eval_by_assign(evaluator, current_partner, assign_num):
        return Evaluation.query(
            Evaluation.evaluator == evaluator.key, 
            Evaluation.evaluatee == current_partner.key,
            Evaluation.assignment_number == assign_num
        )


    @staticmethod
    def get_eval_history_by_evaluator(student, active, quarter, year):
        return Evaluation.query(
            Evaluation.evaluator == student.key,
            Evaluation.active == active,
            Evaluation.quarter == quarter,
            Evaluation.year == year
        )


    @staticmethod
    def get_eval_history_by_evaluatee(student, active, quarter, year):
        return Evaluation.query(
            Evaluation.evaluatee == student.key,
            Evaluation.active == active,
            Evaluation.quarter == quarter,
            Evaluation.year == year
        )


    @staticmethod
    def get_eval_by_evaluator_and_assign(student, assign_num, active=True):
        return Evaluation.query(
            Evaluation.evaluator == student,
            Evaluation.active == active,
            Evaluation.assignment_number == assign_num,
        ).fetch()


    @staticmethod
    def get_all_evals_for_assign(quarter, year, assign_num, active=True):
        return Evaluation.query(
            Evaluation.quarter == quarter,
            Evaluation.year == year,
            Evaluation.assignment_number == assign_num,
            Evaluation.active == active
        )


    @staticmethod
    def get_eval_for_pair_by_assign(evaluator, evaluatee, assign, active=True):
        return Evaluation.query(
            Evaluation.evaluatee == evaluatee.key,
            Evaluation.evaluator == evaluator.key,
            Evaluation.assignment_number == assign,
            Evaluation.active == active,
            Evaluation.year == evaluator.year,
            Evaluation.quarter == evaluator.quarter,
        )


    @staticmethod
    def cancel_evals_for_partnership(partnership):
        members = partnership.members
        to_save = []

        for member1 in members:
            for member2 in members:
                if member1 != member2:
                    evals = EvalModel.get_eval_for_pair_by_assign(member1.get(), member2.get(), partnership.assignment_number)

                    for eval in evals:
                        eval.active = False
                        to_save.append(eval)

        ndb.put_multi(to_save)
        return True
