#!/usr/bin/env python

import argparse, os
import xml.etree.ElementTree as ET


parser = argparse.ArgumentParser(description="this is a rough draft of parsing dfxml")
parser.add_argument('-i', '--input', type=str, help='path to xml file')
args = parser.parse_args()

tree = ET.parse(args.input)
root = tree.getroot()
ns = "{http://www.forensicswiki.org/wiki/Category:Digital_Forensics_XML}"
fakedirlist = ['/Volumes/USB DISK/this_is_a_title_1---reel_1_of_6---scan','/Volumes/USB DISK/this_is_a_title_2---reel_1_of_6---scan','/Volumes/USB DISK/this_is_a_title_3---reel_1_of_6---scan','/Volumes/USB DISK/this_is_a_title_4---reel_1_of_6---scan']
bagmanifest = open('manifest-md5.txt', 'w')


### this is for making the bag from the DFXML
for fileobject in root.iter(ns+'fileobject'):
	## only do this for files, not dirs
	filegen = (f for f in fileobject.iter(ns+'name_type') if f.text != 'd')
	for f in filegen:
		# for every allocated file that is an 'actual' file (not a directory, . or ..)
		for allocationStatus in fileobject.iter(ns+'alloc'):
			filename = fileobject[1].text
			generator = (checksum for checksum in fileobject.iter(ns+'hashdigest') if checksum.attrib['type'] == 'md5')
			for checksum in generator:
				### right now I'm using a hard coded list of dirs and iterating over that,
				### but in actuality I will pass this function one at a time and iterate outside of the function
				for fakedir in fakedirlist:
					lengthOfBaseOfPath = len(os.path.dirname(fakedir))+1
					# print 'dir from list: '+fakedir
					trimmedFilename = fakedir[lengthOfBaseOfPath:]
					if trimmedFilename in filename:
						manifestLine = checksum.text+'  '+'data/'+filename+'\n'
						print manifestLine
						bagmanifest.write(manifestLine)


bagmanifest.close()



	# if the first part of the file path starts with something in the list of directories, get the checksum and filename, get ready to make bag



