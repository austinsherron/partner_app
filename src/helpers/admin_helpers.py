################################################################################
## IMPORTS #####################################################################
################################################################################


import datetime as dt
from collections import defaultdict


################################################################################
################################################################################
################################################################################


################################################################################
## ADMIN HELPERS ###############################################################
################################################################################



def make_date(date, time):
	"""
	This is a function that takes a date and time in the form of lists
	and creates/returns a datetime object from them.

	Paramters
	---------
	date : list
		date in the form of a list: [year, month, day]
	time : list
		time in the form of a list: [hour, minute]

	Returns
	-------
	datetime.datetime object
	"""
	return dt.datetime(
		year=int(date[0]),
		month=int(date[1]),
		day=int(date[2]),
		hour=int(time[0]),
		minute=int(time[1])
	)


def keys_to_partners(all_partners):
	"""
	This is a function that maps student keys to the partnership objects in which
	a key exists as a member of a partnership.
	
	Parameters
	----------
	all_partners : list (iterable)
		iterable of partnership obejcts
	
	Returns
	-------
	k_to_p : defaultdict of dicts
		mapping of keys to dicts of partnership objects

	TODO
	----
	Generalize
	"""
	k_to_p = defaultdict(dict)
	for partnership in all_partners:
            for member in partnership.members:
                k_to_p[member][partnership.assignment_number] = partnership

	return k_to_p


def student_info_to_partner_list(last_num, first_num, keys_to_partnerships, keys_to_students, students):
	"""
	This function creates and returns a tuple--containing student info--to list--containing
	partnership history info (strings)--mapping.

	Parameters
	----------
	last_num : int
		number of the last assignment for a given term
	keys_to_partnerships : dict<ndb.Key,Partnership objects>
		mapping of student object keys to the relevant partnership objects 
		(returned by the function 'keys_to_partners')
	keys_to_students : dict<ndb.Key,Student objects>
		mapping of student object keys to their associated objects
	students : list (iterable) of student objects

	Returns
	-------
	partnership_dict : dict<(str),[str]>
		mapping of student info to partnership strings

	TODO
	----
	Generalize
	Rethink logic
	"""
	partnership_dict = defaultdict(list)							# create mapping of students to sequential partner emails
	for student in students:
		student_info = (student.studentid,student.ucinetid,student.last_name,student.first_name,student.lab)
		for i in range(first_num, last_num + 1):					# need to check for each assignment, as gaps in partner history may exist
			to_append = 'No Selection'								# default status is 'No Selection'

			if i in keys_to_partnerships[student.key]:				# if 'i' isn't there, that student doesn't have a partnership for that assignment 
			    partnership = keys_to_partnerships[student.key][i]	

                            if len(partnership.members) == 1:
                                to_append = 'No Partner'
                            else:
                                to_append = ''
                                for member in partnership.members:
                                    if member != student.key:
                                        member_object = member.get() if member not in keys_to_students else keys_to_students[member]
                                        to_append    += member_object.email + ' '

			partnership_dict[student_info].append(to_append)

	return partnership_dict


################################################################################
################################################################################
################################################################################
