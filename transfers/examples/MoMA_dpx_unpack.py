#!/usr/bin/env python2

'''
- validate disk image
- run fiwalk to get DFXML
- parse DPX CSV to find dir names of components
- search DFXML for these folders
– 

- parse DFXML and  
- subprocess: tsk_recover -v -a [disk image] [destination]
- read DPX metadata file
- poll TMS API and make component dirs
- move DPX folders to their appropriate component dir
- continue ?

'''