#!/usr/bin/env python2

import argparse, hashlib, subprocess, StringIO, json, urllib2, os, glob, csv

'''
- validate disk image, 

- read DPX metadata file
- for each line
	- poll TMS object API endpoint, and get the correlating component include
	- make directory named with component number --- component id --- object id (get from file name)

- run fiwalk on disk image to get DFXML
- parse DPX CSV to find dir names of components
- search DFXML for files that include these folder names in their paths

- grab the MD5 - write hand assemble bag

- run 'mmls' (tsk tool) to see if there is a volume map
	- if there is, get the byte offset
- subprocess: tsk_recover -v -a [disk image] [destination]


- move DPX folders to their appropriate component dir
- continue ?

'''

parser = argparse.ArgumentParser(description="Tool for unpacking disk images at MoMA")
parser.add_argument('-i', '--input', type=str, help='path to disk image submission (dir, not img itself)')
args = parser.parse_args()


# CONFORMANCE CHECKS
# is the CSV there?
# is the disk image there?
# make sure there are only one of each
def check_conformance():
	csvpath = glob.glob(args.input+'*.csv')
	disk_image = glob.glob(args.input+'*.E01')

	if len(csvpath) == 1:
		does_csv_exist = os.path.isfile(csvpath[0])
	elif len(csvpath) < 1:
		does_csv_exist = False
	elif len(csvpath) > 1:
		does_csv_exist = "too many CSVs!"
	if len(disk_image) == 1:
		does_E01_exist = os.path.isfile(disk_image[0])
	elif len(disk_image) < 1:
		does_E01_exist = False
	elif len(disk_image) > 1:
		does_E01_exist = "too many Disk Images!"
	if len(disk_image) > 1 and len(csvpath) > 1:
		does_csv_exist = "too many CSVs!"
		does_E01_exist = "too many disk images!"
		return (False, does_csv_exist, does_E01_exist,)
	if does_E01_exist is True and does_csv_exist is True:
		return (True, disk_image[0], csvpath[0])
	elif does_E01_exist is True and does_csv_exist is False:
		return (False, "CSV is missing")
	elif does_E01_exist is False and does_csv_exist is True:
		return (False, "E01 disk image is missing")
	elif does_E01_exist is False and does_csv_exist is False:
		return (False, "E01 disk image AND csv are missing")
	elif does_csv_exist is not True and does_csv_exist is not False:
		return (False, does_csv_exist)
	elif does_E01_exist is not True and does_E01_exist is not False:
		return (False, does_E01_exist)


# TMS STUFF

# for row in csv, get object id and poll API

def check_if_same():
	with open(csvpath, 'rb') as csvfile:
		reader = csv.reader(csvfile, delimiter=',')
		reader = list(reader)
		index = 1
		previous_row_index = 1
		while index < len(reader):
			print len(reader)
			print index
			if reader[previous_row_index][0] == reader[index][0]:
				print reader[previous_row_index][0]+" is the same as "+reader[index][0]
			else:
				print reader[index]
				print reader[previous_row_index][0]+" is not the same as "+reader[index][0]
				return False
			print reader[index]
			previous_row_index = index - 1
			index = index + 1

		# get the object metadata
		# object_url = "http://vmsqlsvcs.museum.moma.org/TMSAPI/TmsObjectSvc/TmsObjects.svc/GetTombstoneDataRest/ObjectID/"+objectID
		# object_request = json.load(urllib2.urlopen(object_url))

		# # get the component metadata
		# # component_url = "http://vmsqlsvcs.museum.moma.org/TMSAPI/TmsObjectSvc/TmsObjects.svc/GetComponentDetails/Component/"+componentID
		# # component_request = json.load(urllib2.urlopen(component_url))

		# # put object metdata in its place
		# dc_ident1 = object_request["GetTombstoneDataRestIdResult"]["ObjectID"]
		# dc_ident2 = object_request["GetTombstoneDataRestIdResult"]["ObjectNumber"]
		# dc_title = object_request["GetTombstoneDataRestIdResult"]["Title"]
		# dc_creator = object_request["GetTombstoneDataRestIdResult"]["DisplayName"]
		# dc_date = object_request["GetTombstoneDataRestIdResult"]["Dated"]
		# dc_format1 = object_request["GetTombstoneDataRestIdResult"]["Classification"]
		# dc_format2 = object_request["GetTombstoneDataRestIdResult"]["Medium"]

		# # put component metadata in its place
		# componentName = component_request["GetComponentDetailsResult"]["ComponentName"]
		# componentNumber = component_request["GetComponentDetailsResult"]["ComponentNumber"]
		# componentID = component_request["GetComponentDetailsResult"]["ComponentID"]
		# Attributes = component_request["GetComponentDetailsResult"]["Attributes"]





# DISK IMAGE STUFF
def initiate_disk_image_validation():
	try:
		out = subprocess.check_output(['/Users/bfino/Downloads/ftkimager', '--verify', args.input])
		return (out, True)
	except subprocess.CalledProcessError as e:
		return (e.output, False)

def validate_disk_image():
	out = process()
	out2 = StringIO.StringIO(out[0])
	lines = out2.readlines()
	if out[1] == True:
		md5result = lines[4]
		sha1result = lines[9]
	elif out[1] == False:
		md5result = lines[3]
		sha1result = lines[7]

	if "Match" in md5result and "Match" in sha1result:
		print "MD5 and sha1 validated"
	elif "Mismatch" in md5result and "Mismatch" in sha1result:
		print "MD5 and sha1 did not validate"
	else:
		print "uncaught error or condition"

# validate_disk_image()

if len(check_conformance()) == 3 and check_conformance()[0] is True:
	print "everything checks out"
	# print check_conformance()
	disk_image_path = check_conformance()[1]
	csvpath = check_conformance()[2]
elif len(check_conformance()) == 2:
	print "something is wrong: "+ check_conformance()[1]
	raise SystemExit
elif len(check_conformance()) == 3:
	print "something is wrong: "+ check_conformance()[1]+" and "+check_conformance()[2]
	raise SystemExit

print check_if_same()

# i = 1

# while i < 100000:
# 	print i
# 	i = i + 1
# 	print "pretending to do stuff"


