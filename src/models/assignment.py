from models import Assignment


class AssignmentModel:

    @staticmethod
    def get_active_assign_with_latest_fade_in_date(quarter, year):
        assigns_after_now = Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
            Assignment.fade_in_date < dt.now() - td(hours=8)
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
            Assignment.eval_date > dt.now() - td(hours=8)
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
            Assignment.fade_in_date < dt.now() - td(hours=8)
        ).order(Assignment.fade_in_date).fetch()

        to_return = []

        for i in range(len(assigns_before_now) - 1, -1, -1):
            if assigns_before_now[i].close_date > dt.now() - td(hours=8):
                to_return.append(assigns_before_now[i])

        return to_return


    @staticmethod
    def get_active_eval_assigns(quarter, year):
        assigns_before_now = Assignment.query(
            Assignment.quarter == quarter,
            Assignment.year == year,
            Assignment.eval_date > dt.now() - td(hours=8)
        ).order(Assignment.eval_date).fetch()

        to_return = []

        for i in range(len(assigns_before_now)):
            if assigns_before_now[i].eval_open_date < dt.now() - td(hours=8):
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
        return range(0,last.number + 1)


