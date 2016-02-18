#!/usr/bin/env python2

import argparse, hashlib, subprocess, StringIO, json, urllib2, os, glob, csv, ast

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


def conformance_check():
	disk_images = glob.glob(args.input+'*.E01')
	csvs = glob.glob(args.input+'*.csv')

	for img in disk_images:
		csvconvert = img[:-3]+'csv'
		if csvconvert in csvs:
			print "there is a CSV for every disk image"
		else:
			print img+" is missing a CSV"
			return False
	for csv in csvs:
		imgconvert = csv[:-3]+'E01'
		if imgconvert in disk_images:
			print "there is a disk image for every CSV"
		else:
			print csv+" is missing a disk image"
			return False
	return (disk_images, csvs)


	# for image in disk_images:
	# 	if os.path.isfile(image):
	# 		for image in disk_images:
	# 			imagepath = image[:-3]
	# 			print 'found this disk image: '+image
	# 			if os.path.isfile(imagepath+'csv'):
	# 				print 'found this corrseponding csv: '+imagepath+'csv'
	# 				return disk_images
	# 			else:
	# 				return False


# TMS STUFF

# for row in csv, get object id and poll API

def check_if_same(csvpath):
	with open(csvpath, 'rb') as csvfile:
		reader = csv.reader(csvfile, delimiter=',')
		reader = list(reader)
		index = 1
		previous_row_index = 1
		while index < len(reader):
			# print len(reader)
			# print "starting loop this is the index:"+str(index)
			# if reader[previous_row_index][0] == reader[index][0]:
			# 	# print reader[previous_row_index][0]+" is the same as "+reader[index][0]
			if reader[previous_row_index][0] != reader[index][0]:
				print reader[previous_row_index][0]+" is not the same as "+reader[index][0]
				return False
			# print reader[index]
			index = index + 1
			previous_row_index = index - 1
		return True

def tms_when_same(csvpath):
	with open(csvpath, 'rb') as csvfile:
		reader = csv.reader(csvfile, delimiter=',')
		# get the object number
		for i, row in enumerate(reader):
			if i == 1:
				objectnumber = row[0]

		print "hitting the TMS API with Object Number: "+objectnumber

		# get the object metadata
		object_url = "http://vmsqlsvcs.museum.moma.org/TMSAPI/TmsObjectSvc/TmsObjects.svc/GetTombstoneDataRest/Object/"+objectnumber
		object_request = json.load(urllib2.urlopen(object_url))
		object_request = object_request["GetTombstoneDataRestResult"]
		object_id = object_request["ObjectID"]

		components = object_request['Components']
		components = ast.literal_eval(components)

		csvfile.seek(0)

		csvfile.readline()

		componentcounter = 0
		dircounter = 0
		dirlist = []
		for row in reader:
			componentnumber = row[1]
			componentnumber = componentnumber.strip()
			componentcounter = componentcounter+1

			for item in components:
				if item['ComponentNumber'] == componentnumber:
					# print "found component number in json"
					componentID = item['ComponentID']
					dirname = str(componentnumber)+"---"+str(componentID)+"---"+str(object_id)
					dircounter = dircounter+1
					dirlist.append(dirname)
					print dirname
				# else:
				# 	print item['ComponentNumber']+" is not the same as "+componentnumber
		if componentcounter == dircounter == len(dirlist):
			print "was able to find all components from the CSV in the TMS API. Making dirs now."
			for item in dirlist:
				os.makedirs(args.input+item, 0755)
		else:
			print "wasn't able to find all of the components from the CSV in TMS. Stopping here."
			return False


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
def initiate_disk_image_validation(imagepath):
	try:
		out = subprocess.check_output(['/Users/bfino/Downloads/ftkimager', '--verify', imagepath])
		return (out, True)
	except subprocess.CalledProcessError as e:
		return (e.output, False)

def validate_disk_images(imagepath):
	out = initiate_disk_image_validation(imagepath)
	out2 = StringIO.StringIO(out[0])
	lines = out2.readlines()
	if out[1] == True:
		md5result = lines[3]
		sha1result = lines[7]
	elif out[1] == False:
		md5result = lines[3]
		sha1result = lines[7]

	if "Match" in md5result and "Match" in sha1result:
		print "MD5 and sha1 validated"
		return True
	elif "Mismatch" in md5result and "Mismatch" in sha1result:
		print "MD5 and sha1 did not validate"
		return False
	else:
		print "uncaught error or condition"
		return False



# check conformance, and if OK, validate the disk image(s)
if conformance_check():
	imagelist, csvlist = conformance_check()
	print "passed conformance check. Proceeding to disk image validation"
	# for image in imagelist:
	# 	print validate_disk_images(image)
else:
	print "failed conformance check."
	raise SystemExit

for csvpath in csvlist:
	if check_if_same(csvpath):
		print csvpath+" contains records that are all for the same object record"
		tms_when_same(csvpath)
	else:
		print csvpath+" contains records that are for more than one object record"
# parse the CSV(s)


# print check_if_same()

# if check_if_same() is True:
# 	tms_when_same()



