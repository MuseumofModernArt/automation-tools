#!/usr/bin/env python2

'''
- validate disk image, 
	- parse disk image log file and searching for line that starts with "Md5 checksum"
	- run md5 against disk image and make sure it's the same

- read DPX metadata file
- for each line
	- poll TMS object API endpoint, and get the correlating component include
	- make directory named with component number --- component id --- object id (get from file name)

- run fiwalk on disk image to get DFXML
- parse DPX CSV to find dir names of components
- search DFXML for files that include these folder names in their paths
– grab the MD5
- write "data/"+[ filename path from DFXML ], a tab space, and then the MD5 (one line per file)


- run 'mmls' (tsk tool) to see if there is a volume map
	- if there is, get the byte offset
- subprocess: tsk_recover -v -a [disk image] [destination]


two min per 1,000 files

- move DPX folders to their appropriate component dir
- continue ?

'''