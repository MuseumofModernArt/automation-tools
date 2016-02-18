#!/usr/bin/env python

import argparse
import xml.etree.ElementTree as ET


parser = argparse.ArgumentParser(description="this is a rough draft of parsing dfxml")
parser.add_argument('-i', '--input', type=str, help='path to xml file')
args = parser.parse_args()

tree = ET.parse(args.input)
root = tree.getroot()

ns = "{http://www.forensicswiki.org/wiki/Category:Digital_Forensics_XML}"

for fileobject in root.iter(ns+'fileobject'):
	
	if fileobject[6].tag == ns+'alloc':
		print 'allocated file: '+fileobject[1].text

