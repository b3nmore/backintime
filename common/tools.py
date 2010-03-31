#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import os.path
import os
import sys
import subprocess
import hashlib
import commands


ON_AC = 0
ON_BATTERY = 1
POWER_ERROR = 255


def get_backintime_path( path ):
	return os.path.join( os.path.dirname( os.path.abspath( os.path.dirname( __file__ ) ) ), path )


def register_backintime_path( path ):
	path = get_backintime_path( path )
	if not path in sys.path:
		sys.path = [path] + sys.path


def read_file( path, default_value = None ):
	ret_val = default_value 

	try:
		file = open( path )
		ret_val = file.read()
		file.close()
	except:
		pass

	return ret_val


def read_file_lines( path, default_value = None ):
	ret_val = default_value 

	try:
		file = open( path )
		ret_val = file.readlines()
		file.close()
	except:
		pass

	return ret_val


def read_command_output( cmd ):
	ret_val = ''

	try:
		pipe = os.popen( cmd )
		ret_val = pipe.read().strip()
		pipe.close() 
	except:
		return ''

	return ret_val


def check_command( cmd ):
	cmd = cmd.strip()

	if len( cmd ) < 1:
		return False

	if os.path.isfile( cmd ):
		return True

	cmd = read_command_output( "which \"%s\"" % cmd )

	if len( cmd ) < 1:
		return False

	if os.path.isfile( cmd ):
		return True

	return False


def make_dirs( path ):
	path = path.rstrip( os.sep )
	if len( path ) <= 0:
		return

	if not os.path.isdir( path ):
		try:
			os.makedirs( path )
		except:
			pass


def process_exists( name ):
	output = read_command_output( "ps -o pid= -C %s" % name )
	return len( output ) > 0


def check_x_server():
	return 0 == os.system( 'xdpyinfo >/dev/null 2>&1' )


def prepare_path( path ):
	path = path.strip( "/" )
	path = os.sep + path
	return path


def power_status_available():
	"""Uses the on_ac_power command to detect if the the system is able
	to return the power status."""
	try:
		rt = subprocess.call( 'on_ac_power' )
		if rt == ON_AC or rt == ON_BATTERY:
			return True
	except:
		pass
	return False


def on_battery():
	"""Checks if the system is on battery power."""
	if power_status_available ():
		return subprocess.call ( 'on_ac_power' ) == ON_BATTERY
	else:
		return False


def get_snapshots_list_in_folder( folder, sort_reverse = True ):
	biglist = []
	#print folder

	try:
		biglist = os.listdir( folder )
		#print biglist
	except:
		pass

	list = []

	for item in biglist:
		#print item + ' ' + str(len( item ))
		if len( item ) != 15 and len( item ) != 19:
			continue
		if os.path.isdir( os.path.join( folder, item, 'backup' ) ):
			#print item
			list.append( item )

	list.sort( reverse = sort_reverse )
	return list


def get_nonsnapshots_list_in_folder( folder, sort_reverse = True ):
	biglist = []
	#print folder

	try:
		biglist = os.listdir( folder )
		#print biglist
	except:
		pass

	list = []

	for item in biglist:
		#print item + ' ' + str(len( item ))
		if len( item ) != 15 and len( item ) != 19:
			list.append( item )
		else: 
			if os.path.isdir( os.path.join( folder, item, 'backup' ) ):
				#print item
				continue
			else:
				list.append( item )

	list.sort( reverse = sort_reverse )
	return list


def move_snapshots_folder( old_folder, new_folder ):
	'''Moves all the snapshots from one folder to another'''
	print "\nMove snapshots from %s to %s" %( old_folder, new_folder )	

	# Fetch a list with snapshots for verification
	snapshots_to_move = get_snapshots_list_in_folder( old_folder )
	snapshots_already_there = []
	if os.path.exists( new_folder ) == True:
		snapshots_already_there = get_snapshots_list_in_folder( new_folder )
	else:
		tools.make_dirs( new_folder )	
	print "To move: %s" % snapshots_to_move
	print "Already there: %s" % snapshots_already_there
	snapshots_expected = snapshots_to_move + snapshots_already_there
	print "Snapshots expected: %s" % snapshots_expected
	
	# Check if both folders are within the same os
	device_old = os.stat( old_folder ).st_dev
	device_new = os.stat( new_folder ).st_dev
	if device_old == device_new:
		# Use move
		for snapshot in snapshots_to_move:
			cmd = "mv -f \"%s/%s\" \"%s\"" %( old_folder, snapshot, new_folder )
			_execute( cmd )
	else:
		# Use rsync
		# Prepare hardlinks 
		if len( snapshots_already_there ) > 0:
			first_snapshot_path = os.path.join( new_folder, snapshots_to_move[ len( snapshots_to_move ) - 1 ] )
			snapshot_to_hardlink_path =  os.path.join( new_folder, snapshots_already_there[0] )
			cmd = "cp -al \"%s\" \"%s\"" % ( snapshot_to_hardlink_path, first_snapshot_path )
			_execute( cmd )
	
		# Prepare excludes
		nonsnapshots = get_nonsnapshots_list_in_folder( old_folder )
		print "Nonsnapshots: %s" % nonsnapshots
		items = []
		for nonsnapshot in nonsnapshots:
			for item in items:
				if nonsnapshot == item:
					break
			items.append( "--exclude=\"%s\"" % nonsnapshot )
		rsync_exclude = ' '.join( items )
		#print rsync_exclude
		
		# Move move move
		cmd = "rsync -aEAXHv --delete " + old_folder + " " + new_folder + " " + rsync_exclude
		_execute( cmd )
		
	# Remove old ones
	snapshots_not_moved = []
	for snapshot in snapshots_to_move:
		if os.path.exists( os.path.join( new_folder, snapshot, "backup" ) ):
			if os.path.exists( os.path.join( old_folder, snapshot) ):
				print "Remove: %s" %snapshot
				path_to_remove = os.path.join( old_folder, snapshot )
				cmd = "find \"%s\" -type d -exec chmod u+wx {} \\;" % path_to_remove #Debian patch
				_execute( cmd )
				cmd = "rm -rfv \"%s\"" % path_to_remove
				_execute( cmd )
			else:
				print "%s was already removed" %snapshot
		else: 
			snapshots_not_moved.append( snapshot )
				
	# Check snapshot list
	if len( snapshots_not_moved ) == 0:
		print "Succes!\n"
		return True
	else:
		print "Error! Not moved: %s\n" %snapshots_not_moved
		return False


def _execute( cmd, callback = None, user_data = None ):
	ret_val = 0

	if callback is None:
		ret_val = os.system( cmd )
	else:
		pipe = os.popen( cmd, 'r' )

		while True:
			line = temp_failure_retry( pipe.readline )
			if len( line ) == 0:
				break
			callback( line.strip(), user_data )

		ret_val = pipe.close()
		if ret_val is None:
			ret_val = 0

	if ret_val != 0:
		print "Command \"%s\" returns %s" % ( cmd, ret_val ) 
	else:
		print "Command \"%s\" returns %s" % ( cmd, ret_val ) 

	return ret_val


def is_process_alive( pid ):
	try:
		os.kill( pid, 0 )	#this will raise an exception if the pid is not valid
	except:
		return False

	return True


def get_rsync_caps():
	data = read_command_output( 'rsync --version' )
	si = data.find( 'Capabilities:' )
	if si < 0:
		return []
	si = data.find( '\n', si )
	if si < 0:
		return []
	ei = data.find( '\n\n', si )
	if ei < 0:
		return []

	data = data[ si + 1 : ei - 1 ]
	data = data.split( '\n' )
	all_caps = ''

	for line in data:
		line = line.strip()
		if len( line ) <= 0:
			continue
		if len( all_caps ) > 0:
			all_caps = all_caps + ' '
		all_caps = all_caps + line

	caps = all_caps.split( ", " )
	#print caps
	#print ( "ACLs" in get_rsync_caps() )
	return caps


def get_rsync_prefix():
	caps = get_rsync_caps()
	cmd = 'rsync -aEH'

	if "ACLs" in caps:
		cmd = cmd + 'A'

	if "xattrs" in caps:
		cmd = cmd + 'X'

	return cmd + ' '


def temp_failure_retry(func, *args, **kwargs): 
	while True:
		try:
			return func(*args, **kwargs)
		except (os.error, IOError), ex:
			if ex.errno == errno.EINTR:
				continue
			else:
				raise


def _get_md5sum_from_path(path):
    '''return md5sum of path'''   
    # print "md5"
    if check_command("md5sum"):
        # md5sum utility, if available
        out = commands.getstatusoutput("md5sum " + path)
        md5sum = out[1].split(" ")[0]
        return md5sum
    else: 
        # python std lib (not a good idea for huge files)
        try:
            path = open(path, 'rb')
            md5sum = hashlib.md5(path.read())
        except IOError:
            return False  
        return md5sum.hexdigest()
        				

class UniquenessSet():
    ''' a class to check for uniqueness of snapshots'''
    def __init__(self, dc = False): 
        self.deep_check = dc
        self._sizes_dict = {}   # if self._sizes_dict[i] == None => already checked with md5sum
        
    def test_and_add(self, path):
        '''store a unique key for path'''
        if self.deep_check:
            # store md5sum 
            size  = os.stat(path).st_size
            if size not in self._sizes_dict.keys(): 
                # first item of that size
                unique_key = size
            else: 
                previously = self._sizes_dict[size]
                if previously:
                    # store md5sum instead of previously stored size
                    md5sum_0 = _get_md5sum_from_path(previously)     
                    self._sizes_dict[size]     = None
                    self._sizes_dict[md5sum_0] = previously      
                unique_key = _get_md5sum_from_path(path) 
        else:
            # store a tuple of (size, modification time)
            obj  = os.stat(path)
            unique_key = (obj.st_size, int(obj.st_mtime)) 
        # store if not already, and return True
        if unique_key not in self._sizes_dict.keys():
            self._sizes_dict[unique_key] = path
            return True    
        return False

