################################################################################
## IMPORTS #####################################################################
################################################################################


import datetime as dt


################################################################################
################################################################################
################################################################################


################################################################################
## HELPERS #####################################################################
################################################################################


def get_sess_val(session, key):
	"""
	This is a helper function that returns the value
	in 'session' associated with the key 'key' if it
	exists, else None.

	Parameters
	----------
	session : dict-like, session object
		session will be searched for 'key'
	key : any immutable type 
		the key that session will be searched for

	Returns
	-------
	the value associated with key in session, if it
	exists, else None
	"""
	if key in session:
		return session.get(key)
	else:
		return None


def get_sess_vals(session, *args):
	"""
	This is a helper function that returns the
	values associated associated with the keys
	in *args if all of the keys exists in session.
	If one key doesn't exist, the method returns
	None.

	Parameters
	----------
	session : dict-like, session object
		session will be searched for 'key'
	*args : mixed immutable types
		the keys that session will be searched for

	Returns
	-------
	sess_vals : tuple of mixed
		the values associated with the keys in *args;
		if one or more keys don't exist in session,
		None is returned
	"""
	sess_vals = []

	for arg in args:
		sess_val = get_sess_val(session, arg)
		if sess_val:
			sess_vals.append(sess_val)
		else:
			return None

	return tuple(sess_vals)


def query_to_dict(*args):
	"""
	Converts google NDB query objects to dictionaries.

	Parameters
	----------
	*args : mixed
		Any number of query objects to convert to dictionaries.

	Returns
	-------
	mixed
		Dictionary representations of the arguments in args.
	"""
	return [x.to_dict() for x in args]


def split_last(s, char=','):
	print(s)
	splt = s.split(char)
	splt = [char.join(splt[:-1]), splt[-1]]	
	print(splt)
	return list(filter(lambda x: x != '', splt))


################################################################################
################################################################################
################################################################################
