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
'YAFFS2',
'HFS'
]


def hilite(string, status, bold):
    attr = []
    if status == "green":
        # green
        attr.append('32')
    elif status == "gray":
    	attr.append('37')
    else:
        # red
        attr.append('30')
    if bold:
        attr.append('1')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), string)

def conformance_check():
	disk_images = glob.glob(args.input+'*.E01')
	csvs = glob.glob(args.input+'*.csv')

	for img in disk_images:
		csvconvert = img[:-3]+'csv'
		if csvconvert not in csvs:
			print img+" is missing a CSV"
			return False
	for csv in csvs:
		imgconvert = csv[:-3]+'E01'
		if imgconvert not in disk_images:
			print csv+" is missing a disk image"
			return False
	return (disk_images, csvs, True)


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

		print "Pinging the TMS API for object: "+objectnumber

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
			print "All components in disk image are accounted for in TMS. \nMaking directories for these components"
			for item in dirlist:
				os.makedirs(args.input+item+'/data', 0755)
			return dirlist
		else:
			print "wasn't able to find all of the components from the disk image in TMS. Stopping here."
			SystemExit


# For when the CSV indicates that the disk image contains material associated with more than one object record
def tms_when_multiple_objects(csvpath):
	with open(csvpath, 'rb') as csvfile:
		reader = csv.reader(csvfile, delimiter=',')
		reader = list(reader)
		index = 1
		previous_row_index = 1

		objectnumber = reader[index][0]

		print "Pinging the TMS API for object: "+objectnumber
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
		md5result = lines[4]
		sha1result = lines[9]
	elif out[1] == False:
		md5result = lines[4]
		sha1result = lines[9]

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
	print "\nGenerating DFXML"
	try:
		out = subprocess.check_output(['fiwalk', '-X'+args.input+os.path.basename(os.path.normpath(imagepath))[:-4]+'.xml', imagepath])
		return out
	except subprocess.CalledProcessError as e:
		return e.output

def get_offset(imagepath):
	try:
		out = subprocess.Popen(['mmls', imagepath],stdout=subprocess.PIPE)
		x = 0
		volume_dictionary = {}
		new_volume_dictionary = {}
		for line in iter(out.stdout.readline,''):
   			lineofoutput = line.rstrip()
   			x = x+1
   			for item in filesystem_list:
	   			if item in lineofoutput:
	   				# print "MATCHED!!!"+lineofoutput
	   				lineofoutput = lineofoutput.split('   ')
	   				# print lineofoutput
	   				byte_offset = lineofoutput[1].lstrip('0')
	   				volume_description = lineofoutput[4]
	   				# print volume_description+" Volume found at byte offset "+byte_offset
	   				volume_dictionary[volume_description] = byte_offset
	   	for vol, offset in volume_dictionary.iteritems():
	   		print 'checking '+vol+' at '+offset+" offset in "+imagepath
			out = subprocess.Popen(['fsstat', '-o '+offset, imagepath],stdout=subprocess.PIPE)
			for line in iter(out.stdout.readline,''):
				lineofoutput = line.rstrip()
				# print lineofoutput
				if 'Volume Name:' in lineofoutput or 'Volume Label' in lineofoutput:
					print 'found a match!'
					lineofoutput = lineofoutput.split(':')
					if lineofoutput is not '':
						print lineofoutput
						volumename = lineofoutput[1][1:]
						if offset not in new_volume_dictionary:
							new_volume_dictionary[offset] = volumename, vol
		print new_volume_dictionary


		if x < 2:
			return False
		else:
			# print "This appears to be a physical image"
			return (new_volume_dictionary, True)
			# print "\n\n\n\n\n\n\nHere comes the volume dictionary"
			# print volume_dictionary
			# print "that was the volume dictionary\n\n\n\n\n\n\n"
	except subprocess.CalledProcessError as e:
		return (e.output, False)

def make_bag_from_DFXML(csvpath):
	print "assembling bags from the fiwalk generated MD5 checksums..."

	# need to accomodate for multi-volume, physical images
	# get volume name from CSV

	tree = ET.parse(csvpath[:-4]+".xml")
	root = tree.getroot()
	ns = "{http://www.forensicswiki.org/wiki/Category:Digital_Forensics_XML}"

	imagepath = csvpath[:-3]+"E01"

	

	# for volume in root.iter(ns+'volume'):
	# 	# print 'here is the volume offset'
	# 	dfxmloffset = int(volume[0].text)
	# 	for vol, offset in volume_dictionary.iteritems():
	# 		# print vol
	# 		multipliedOffset = int(offset)*512
	# 		# print multipliedOffset
	# 		# print dfxmloffset
	# 		if dfxmloffset == multipliedOffset:
	# 			print "matched"
	# 			print offset
	# 			print "with"
	# 			print dfxmloffset
		

	# it appears that fiwalk doesn't display the volume name for *all* filesystems in the dfxml... 
	# so instead of relying on name, we will run get_offset() to get the volume dictionary, and then...
	# find iterate the volumes

	new_volume_dictionary = get_offset(imagepath)[0]

	print new_volume_dictionary

	for item in new_volume_dictionary.iteritems():
		print item
			
	# for volume in root.iter(ns+'volume'):
		
	# 	for fileobject in volume.iter(ns+'fileobject'):
	# 		print "Looking at the volume at offset "+volume[4].text+" to try and find its name"
	# 		volgen = (v for v in fileobject.iter(ns+'filename') if 'Volume Label Entry' in v.text)
	# 		for vol in volgen:
	# 			print vol.text
	# 			print 'yes yes yes match'
	# 	print "what now\n\n\n\n\n\n\n\n\n"
		

	for fileobject in root.iter(ns+'fileobject'):


		## only do this for files, not dirs
		filegen = (f for f in fileobject.iter(ns+'name_type') if f.text != 'd')
		for f in filegen:
			# for every allocated file that is an 'actual' file (not a directory, . or ..)
			for allocationStatus in fileobject.iter(ns+'alloc'):
				filename = fileobject[1].text
				# print "looking at file...\n"
				# print f
				# print "\nlet's see what the parent node of the file is"
				# parent_map = dict((f, p) for p in tree.getiterator() for f in p)
				# for item in parent_map:
				# 	print item
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
								# print "\n\n\n\ndestDir is:"
								# print destDir
								# print destDir[0]
								bagmanifest = open(destDir[0]+'/manifest-md5.txt', 'a')
								manifestLine = checksum.text+'  '+'data/'+filename+'\n'
								# print manifestLine
								bagmanifest.write(manifestLine)
								bagmanifest.close()
						csvfile.seek(0)




def expand_image_and_move_files(imagepath):
	print 'expanding disk image...'+imagepath
	print imagelist
	if get_offset(imagepath) is False:
		print "This appears to be a logical image"
		try:
			out = subprocess.check_output(['tsk_recover', '-a', imagepath, args.input+'expanded_image'])
			ls = subprocess.check_output(['ls', args.input+'expanded_image'])
			print ls

			return (out, True)
		except subprocess.CalledProcessError as e:
			return (e.output, False)
	else:
		print "This is a physical image"
		# print get_offset(args.input)
		offset_dict = get_offset(imagepath)[0]
		print offset_dict
		for entry, values in offset_dict.iteritems():
			offset = entry
			volume = values[0]
			filesystem = values[1]
			print "There is a "+filesystem+" volume called "+volume+" at byte offset "+offset
			try:
				out = subprocess.check_output(['tsk_recover', '-o'+ offset, '-a', imagepath, args.input+offset+'---expanded_image'])
				# return (out, True)

				# this is all from below
				csvpath = imagepath[:-3]+'csv'
				print "oppening csv "+csvpath
				with open(csvpath, 'rb') as csvfile:
					reader = csv.reader(csvfile, delimiter=',')
					csvfile.readline()
					for row in reader:
						compnum = row[1]
						compnum = compnum.strip()
						fromdir = row[2]





						# TODO NEXT ! act only if the Volume name from the path in the CSV matches the curently iterating volume name in the dictionary







						fromdirBaselen = len(os.path.dirname(fromdir))+1
						fromdir = offset+'---expanded_image/'+fromdir[fromdirBaselen:]
						# print "\n\n\n\n\n\n\nthis is the fromdir: \n"+fromdir+"\nthat was the fromdir\n\n\n\n\n\n"
						destDir = glob.glob(args.input+compnum+'*')
						destDir = destDir[0]+'/data'
						# print destDir
						try:
							print "Moving: \n"+args.input+fromdir+'\nto ---------------------->   \n'+destDir+'\n'
							out = subprocess.check_output(['mv', args.input+fromdir, destDir])
						except subprocess.CalledProcessError as e:
							out = hilite(e.output, "red", "bold")
					print "deleting "+ args.input+offset+'---expanded_image'
					# out = subprocess.check_output(['rm', '-R', args.input+offset+'---expanded_image'])

			except subprocess.CalledProcessError as e:
				print "\n\n\n\nEXCEPTION!"
				print e.output
				return (e.output, False)


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def complete_bags():
	for bag in next(os.walk(args.input))[1]:
		print bag

		baginfo = open(args.input+bag+'/bag-info.txt', 'a+')
		baginfoLine = 'bagging date: '+str(datetime.datetime.now().date())
		baginfo.write(baginfoLine)
		baginfo.close()

		bagit = open(args.input+bag+'/bagit.txt', 'a+')
		bagitLine = 'BagIt-Version: 0.97'
		bagit.write(bagitLine)
		bagitLine = '\nTag-File-Character-Encoding: UTF-8'
		bagit.write(bagitLine)
		bagit.close()

		baginfoTXThash = md5(args.input+bag+'/bag-info.txt')
		bagitTXThash = md5(args.input+bag+'/bagit.txt')
		manifestTXThash = md5(args.input+bag+'/manifest-md5.txt')

		tagmanifest = open(args.input+bag+'/tagmanifest-md5.txt', 'a+')
		tagmanifestLine = baginfoTXThash+'\tbag-info.txt\n'+bagitTXThash+'\tbagit.txt\n'+manifestTXThash+'\tmanifest-md5.txt'
		tagmanifest.write(tagmanifestLine)
		tagmanifest.close()






#####################
#
# main program flow /\/\/\/\/\/\/ 
#
# check conformance, and if OK, validate the disk image(s)
imagelist, csvlist, state = conformance_check()
if state is True:
	# print "this is the image list"
	# print imagelist
	# print "\n\n\n\n\n\n"
	print "File attendence conformance check: "+hilite("passed", "green", "bold")
	# for image in imagelist:
	# 	# will it exit / fail if image does not validate? it should
	# 	print "Proceeding to validate "+image
	# 	print validate_disk_images(image)
	for image in imagelist:
		print run_fiwalk(image)
	for csvpath in csvlist:
		if check_if_same(csvpath):
			print csvpath+" contains components that belong to one object"
			tms_when_same(csvpath)
			print make_bag_from_DFXML(csvpath)
		else:
			print csvpath+" contains components that are for more than one object record"
			tms_when_multiple_objects(csvpath)
			### to-do: need to figure out if make_bag_fromDFXML() will work for multiple cases
	for image in imagelist:
		expand_image_and_move_files(image)
	complete_bags()
	print "All done!"
	print u'\U0001f604'



else:
	print "failed conformance check."
	raise SystemExit


