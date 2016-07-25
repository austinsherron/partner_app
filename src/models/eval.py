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


