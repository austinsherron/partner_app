from datetime import datetime as dt, timedelta as td
from models import Assignment
from src.helpers.admin_helpers import make_date


class AssignmentModel:

    @staticmethod
    def get_all_assign(quarter, year):
        return Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year
        ).order(Assignment.number).fetch()

    @staticmethod
    def get_active_assign_with_latest_fade_in_date(quarter, year):
        assigns_after_now = Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
            Assignment.fade_in_date < dt.now() - td(hours=7)
        ).order(Assignment.fade_in_date).fetch()

        try:
            return assigns_after_now[-1]
        except IndexError:
            return None


    @staticmethod
    def get_active_assign_with_earliest_eval_due_date(quarter, year):
        evals_after_now = Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
            Assignment.eval_date > dt.now() - td(hours=7)
        ).order(Assignment.eval_date).fetch()

        if len(evals_after_now) > 0:
            return evals_after_now[0]
        else:
            return None


    @staticmethod
    def get_active_assigns(quarter, year):
        assigns_before_now = Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
            Assignment.fade_in_date < dt.now() - td(hours=7)
        ).order(Assignment.fade_in_date).fetch()

        to_return = []

        for i in range(len(assigns_before_now) - 1, -1, -1):
            if assigns_before_now[i].fade_out_date > dt.now() - td(hours=7):
                to_return.append(assigns_before_now[i])

        return to_return

    @staticmethod
    def get_inactive_assigns(quarter, year):
        all_assigns = Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year
        ).order(Assignment.fade_in_date).fetch()

        to_return = []

        for i in range(len(all_assigns) - 1, -1, -1):
            if all_assigns[i].fade_out_date < dt.now() - td(hours=7) or all_assigns[i].fade_in_date > dt.now() - td(hours=7):
                to_return.append(all_assigns[i])

        return to_return

    @staticmethod
    def get_active_eval_assigns(quarter, year):
        assigns_before_now = Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
            Assignment.eval_date > dt.now() - td(hours=7)
        ).order(Assignment.eval_date).fetch()

        to_return = []

        for i in range(len(assigns_before_now)):
            if assigns_before_now[i].eval_open_date < dt.now() - td(hours=7):
                to_return.append(assigns_before_now[i])

        return to_return


    @staticmethod
    def get_assign_by_number(quarter, year, number):
        return Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
            Assignment.number == number,
        ).get()

    @staticmethod
    def delete_assign_by_number(quarter,year,number):
        assgn = Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
            Assignment.number == number,
        ).get()
        assgn.key.delete()


    @staticmethod
    def get_assigns_for_quarter(quarter, year):
        return Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
        )


    @staticmethod
    def get_assign_n(quarter, year, n):
        assigns = Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
        ).order(Assignment.number).fetch()

        try:
            return assigns[n]
        except IndexError:
            return None


    @staticmethod
    def get_assign_range(quarter, year):
        zeroth = AssignmentModel.get_assign_n(quarter, year, 0)

        if not zeroth:
            return range(0,0)

        last = AssignmentModel.get_assign_n(quarter, year, -1)
        return range(zeroth.number,last.number + 1)


    @staticmethod
    def save_assignment_with_dates(**kwargs):
        assignment = kwargs['assignment']

        assignment.fade_in_date   = make_date(kwargs['fade_in_date'], kwargs['fade_in_time'])
        assignment.due_date       = make_date(kwargs[ 'due_date' ], kwargs[ 'due_time' ])
        assignment.close_date     = make_date(kwargs['close_date'], kwargs['close_time'])
        assignment.eval_date      = make_date(kwargs['eval_date'], kwargs['eval_time'])
        assignment.eval_open_date = make_date(kwargs['eval_open_date'], kwargs['eval_open_time'])
        assignment.fade_out_date  = make_date(kwargs['fade_out_date'], kwargs['fade_out_time'])

        # set 'current' value (always false due to query updates)
        assignment.current = False
        assignment.put()
        return assignment


    @staticmethod
    def make_assignment_with_pk_vals(quarter, year, assign):
        assignment         = Assignment()
        assignment.year    = year
        assignment.quarter = quarter
        assignment.number  = assign

        return assignment
