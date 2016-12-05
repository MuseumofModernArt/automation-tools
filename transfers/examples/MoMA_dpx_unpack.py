#!/usr/bin/env python2

import argparse
import hashlib
import subprocess
import StringIO
import json
import urllib2
import os
import glob
import csv
import ast
import xml.etree.ElementTree as ET
import datetime

'''
to-do:

- DONE: validate disk image, 

- DONE: read DPX metadata file
- DONE: for each line
	- DONE: poll TMS object API endpoint, and get the correlating component include
	- DONE: make directory named with component number --- component id --- object id (get from file name)

- DONE: run fiwalk on disk image to get DFXML
- DONE parse DPX CSV to find dir names of components
- DONE search DFXML for files that include these folder names in their paths

- DONE grab the MD5 - write hand assembled bag using the fiwalk generated MD5s in the DFXML

- DONE run 'mmls' (tsk tool) to see if there is a volume map
	- DONE if there is, get the byte offset

- DONE: subprocess: tsk_recover -v -a [disk image] [destination]
- DONE move DPX folders to their appropriate component dir
'''

parser = argparse.ArgumentParser(description="Tool for unpacking disk images at MoMA")
parser.add_argument('-i', '--input', required=True, type=str, help='path to disk image submission (dir, not img itself)')
args = parser.parse_args()


filesystem_list = [
'ntfs',
'NTFS',
'fat',
'FAT (Auto Detection)',
'ext',
'ExtX (Auto Detection)',
'iso9660',
'ISO9660 CD',
'hfs',
'HFS+',
'ufs',
'UFS (Auto Detection)',
'raw',
'Raw Data',
'swap',
'Swap Space',
'fat12',
'FAT12',
'fat16',
'FAT16',
'fat32',
'FAT32',
'exfat',
'exFAT',
'ext2',
'Ext2',
'ext3',
'Ext3',
'ext4',
'Ext4',
'ufs1',
'UFS1',
'ufs2',
'UFS2',
'yaffs2',
'YAFFS2'
]

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


# TMS STUFF
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
				os.makedirs(args.input+item+'/data', 0755)
			return dirlist
		else:
			print "wasn't able to find all of the components from the CSV in TMS. Stopping here."
			return False

# For when the CSV indicates that the disk image contains material associated with more than one object record
def tms_when_multiple_objects(csvpath):
	with open(csvpath, 'rb') as csvfile:
		reader = csv.reader(csvfile, delimiter=',')
		reader = list(reader)
		index = 1
		previous_row_index = 1

		objectnumber = reader[index][0]

		print "hitting the TMS API with Object Number: "+objectnumber
		# get the object metadata
		object_url = "http://vmsqlsvcs.museum.moma.org/TMSAPI/TmsObjectSvc/TmsObjects.svc/GetTombstoneDataRest/Object/"+objectnumber
		object_request = json.load(urllib2.urlopen(object_url))
		object_request = object_request["GetTombstoneDataRestResult"]
		object_id = object_request["ObjectID"]
		components = object_request['Components']
		components = ast.literal_eval(components)
		componentcounter = 0
		dircounter = 0
		dirlist = []

		while index < len(reader):
			if reader[previous_row_index][0] == reader[index][0]:
				componentnumber = reader[index][1]
				componentnumber = componentnumber.strip()
				componentcounter = componentcounter+1
				for item in components:
					# print item['ComponentNumber']
					if item['ComponentNumber'] == componentnumber:
						# print "found component number in json"
						componentID = item['ComponentID']
						dirname = str(componentnumber)+"---"+str(componentID)+"---"+str(object_id)
						dircounter = dircounter+1
						dirlist.append(dirname)
						print dirname
					# else:
						# print item['ComponentNumber']+" is not the same as "+componentnumber
			else:
				componentnumber = reader[index][1]
				componentnumber = componentnumber.strip()
				componentcounter = componentcounter+1
				print reader[previous_row_index][0]+" is not the same as "+reader[index][0]
				objectnumber = reader[index][0]
				componentnumber = reader[index][1]
				componentnumber = componentnumber.strip()
				print "hitting the TMS API with Object Number: "+objectnumber
				# get the object metadata
				object_url = "http://vmsqlsvcs.museum.moma.org/TMSAPI/TmsObjectSvc/TmsObjects.svc/GetTombstoneDataRest/Object/"+objectnumber
				object_request = json.load(urllib2.urlopen(object_url))
				object_request = object_request["GetTombstoneDataRestResult"]
				object_id = object_request["ObjectID"]
				components = object_request['Components']
				components = ast.literal_eval(components)
				for item in components:
					# print item['ComponentNumber']
					if item['ComponentNumber'] == componentnumber:
						# print "found component number in json"
						componentID = item['ComponentID']
						dirname = str(componentnumber)+"---"+str(componentID)+"---"+str(object_id)
						dircounter = dircounter+1
						dirlist.append(dirname)
						print dirname
				# return False
			# print reader[index]
			index = index + 1
			previous_row_index = index - 1
		if componentcounter == dircounter == len(dirlist):
			print "was able to find all components from the CSV in the TMS API. Making dirs now."
			for item in dirlist:
				os.makedirs(args.input+item+'/data', 0755)
		else:
			print "wasn't able to find all of the components from the CSV in TMS. Stopping here."
			return False
		return True

def get_offset(imagepath):
	try:
		out = subprocess.Popen(['mmls', imagepath],stdout=subprocess.PIPE)
		x = 0
		for line in iter(out.stdout.readline,''):
   			newline = line.rstrip()
   			x = x+1
   			for item in filesystem_list:
	   			if item in newline:
	   				# print newline
	   				newline = newline.split('   ')
	   				byte_offset = newline[1]
	   				volume_description = newline[4]
	   				print volume_description+" Volume found at byte offset "+byte_offset
		if x < 2:
			print "This appears to be a logical image"
			return False
		else:
			print "This appears to be a physical image"
			return (byte_offset, True)
	except subprocess.CalledProcessError as e:
		return (e.output, False)


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
		print lines
		return False


def run_fiwalk(imagepath):
	print "running fiwalk"
	try:
		out = subprocess.check_output(['fiwalk', '-X'+args.input+'fiwalk.xml', imagepath])
		return out
	except subprocess.CalledProcessError as e:
		return e.output

def make_bag_from_DFXML(csvpath):
	print "assembling bags from the fiwalk generated MD5 checksums..."

	### right now, it is making one manifest -- how can I make it make one per component, and put it in the right folder?
	### ok - i have the list of directories within the function now.
	### now i just need to get this right.... I need to iterate the list within the DFXML stuff so as not to parse that file multiple times

	tree = ET.parse('fiwalk.xml')
	root = tree.getroot()
	ns = "{http://www.forensicswiki.org/wiki/Category:Digital_Forensics_XML}"
	for fileobject in root.iter(ns+'fileobject'):
		## only do this for files, not dirs
		filegen = (f for f in fileobject.iter(ns+'name_type') if f.text != 'd')
		for f in filegen:
			# for every allocated file that is an 'actual' file (not a directory, . or ..)
			for allocationStatus in fileobject.iter(ns+'alloc'):
				filename = fileobject[1].text
				generator = (checksum for checksum in fileobject.iter(ns+'hashdigest') if checksum.attrib['type'] == 'md5')
				for checksum in generator:
					# for each file that is a real file with a checksum, 
					# open the CSV
					# for each row in the CSV
						# see if row[2] is in filename (from DFXML)
							# if it is, then find the dir that starts with the comp number for this CSV row
							# write the manifest to this dir
					with open(csvpath, 'rb') as csvfile:
						reader = csv.reader(csvfile, delimiter=',')
						for row in reader:
							# print os.path.dirname(filename)
							lengthOfBaseOfPath = len(os.path.dirname(row[2]))+1
							csvpathhh = row[2]
							trimmedCSVpath = csvpathhh[lengthOfBaseOfPath:]
							if trimmedCSVpath in filename:
								# print trimmedCSVpath +" WAS FOUND "+filename
								# get the path to the right compenent dir
								compNum = row[1].strip()
								destDir = glob.glob(args.input+compNum+'*')
								# print "destDir is:"
								print destDir[0]
								bagmanifest = open(destDir[0]+'/manifest-md5.txt', 'a')
								manifestLine = checksum.text+'  '+'data/'+filename+'\n'
								# print manifestLine
								bagmanifest.write(manifestLine)
								bagmanifest.close()
						csvfile.seek(0)

def expand_image(imagepath):
	print 'expanding disk image...'
	if get_offset(args.input) is False:
		print "YASS logical easy"
		try:
			out = subprocess.check_output(['tsk_recover', '-a', imagepath, args.input+'expanded_image'])
			return (out, True)
		except subprocess.CalledProcessError as e:
			return (e.output, False)
	else:
		print "booo physical images are hard"
		try:
			out = subprocess.check_output(['tsk_recover', '-o'+ get_offset(args.input)[0], '-a', imagepath, args.input+'expanded_image'])
			return (out, True)
		except subprocess.CalledProcessError as e:
			return (e.output, False)

def move_files_to_bag(csvpath):
	with open(csvpath, 'rb') as csvfile:
		reader = csv.reader(csvfile, delimiter=',')
		csvfile.readline()
		for row in reader:
			compnum = row[1]
			compnum = compnum.strip()
			fromdir = row[2]
			fromdirBaselen = len(os.path.dirname(fromdir))+1
			fromdir = 'expanded_image/'+fromdir[fromdirBaselen:]
			destDir = glob.glob(args.input+compnum+'*')
			destDir = destDir[0]+'/data'
			print destDir
			print fromdir+'   ---------------------->   '+destDir
			try:
				out = subprocess.check_output(['mv', fromdir, destDir])
			except CalledProcessError as e:
				out = e.output
		out = subprocess.check_output(['rm', '-R', 'expanded_image'])


def complete_bags():
	for bag in next(os.walk(args.input))[1]:
		print bag

		baginfo = open(bag+'/bag-info.txt', 'a')
		baginfoLine = 'bagging date: '+str(datetime.datetime.now().date())
		baginfo.write(baginfoLine)
		baginfo.close()

		for f in next(os.walk(bag))[1]:

			tagmanifest = open(bag+'/tagmanifest-md5.txt', 'a')
			tagmanifestLine = 'here will go tsv checksums and paths'
			tagmanifest.write(tagmanifestLine)
			tagmanifest.close()






#####################
#
# main program flow
#
# check conformance, and if OK, validate the disk image(s)
# if conformance_check():
# 	imagelist, csvlist = conformance_check()
# 	print "passed conformance check. Proceeding to disk image validation"
# 	# for image in imagelist:
# 	# 	# will it exit / fail if image does not validate? it should
# 	# 	print validate_disk_images(image)
# 	for image in imagelist:
# 		print run_fiwalk(image)
# 	for csvpath in csvlist:
# 		if check_if_same(csvpath):
# 			print csvpath+" contains records that are all for the same object record"
# 			tms_when_same(csvpath)
# 			make_bag_from_DFXML(csvpath)
# 		else:
# 			print csvpath+" contains records that are for more than one object record"
# 			tms_when_multiple_objects(csvpath)
# 			### to-do: need to figure out if make_bag_fromDFXML() will work for multiple cases
# 	for image in imagelist:
# 		print image
# 		expand_image(image)
# 	for csvpath in csvlist:
# 		move_files_to_bag(csvpath)
# 	complete_bags()

# else:
# 	print "failed conformance check."
# 	raise SystemExit

# if get_offset(args.input) is False:
# 	print "YASS logical easy"
# else:
# 	print "boo physical images are hard... I think this is the byte offset? "+get_offset(args.input)[0]
# 	print get_offset(args.input)[0]

expand_image(args.input)