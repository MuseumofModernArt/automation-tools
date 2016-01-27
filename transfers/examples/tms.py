#!/usr/bin/env python

from __future__ import print_function

import json
import os
import sys
import urllib2
import ast

def main(transfer_path):
    basename = os.path.basename(transfer_path)
    try:
        comp_num, comp_id, obj_id = basename.split('---')
    except ValueError:
        return 1
    print('Component Number: ', comp_num, end='')
    print('Component ID: ', comp_id, end='')
    print('Object ID: ', obj_id, end='')

    # get the object metadata
    object_url = "http://vmsqlsvcs.museum.moma.org/TMSAPI/TmsObjectSvc/TmsObjects.svc/GetTombstoneDataRest/ObjectID/"+obj_id
    object_request = json.load(urllib2.urlopen(object_url))

    # get the component metadata
    component_url = "http://vmsqlsvcs.museum.moma.org/TMSAPI/TmsObjectSvc/TmsObjects.svc/GetComponentDetails/Component/"+comp_id
    component_request = json.load(urllib2.urlopen(component_url))

    # put object metdata in its place
    dc_ident1 = object_request["GetTombstoneDataRestIdResult"]["ObjectID"]
    dc_ident2 = object_request["GetTombstoneDataRestIdResult"]["ObjectNumber"]
    dc_title = object_request["GetTombstoneDataRestIdResult"]["Title"]
    dc_creator = object_request["GetTombstoneDataRestIdResult"]["DisplayName"]
    dc_date = object_request["GetTombstoneDataRestIdResult"]["Dated"]
    dc_format1 = object_request["GetTombstoneDataRestIdResult"]["Classification"]
    dc_format2 = object_request["GetTombstoneDataRestIdResult"]["Medium"]

    # put component metadata in its place
    componentName = component_request["GetComponentDetailsResult"]["ComponentName"]
    componentNumber = component_request["GetComponentDetailsResult"]["ComponentNumber"]
    componentID = component_request["GetComponentDetailsResult"]["ComponentID"]
    Attributes = component_request["GetComponentDetailsResult"]["Attributes"]

    #initialize component variables
    componentStatus = ""
    componentFormat = ""

    try:
        Attributes = ast.literal_eval(Attributes)
    except SyntaxError:
        print ("Caught a SyntaxError")
    except ValueError:
        print ("Caught a ValueError")

    componentDate = ''
    componentChannels = ''
    componentCopyinSet = ''

    for item in Attributes:
        try:
            if item['Media Label'] == 'Created Date':
                componentDate = item['Remarks']
            if item['Media Label'] == 'Channels':
                componentChannels = item['Remarks']
            if item['Media Label'] == 'Copy in set':
                componentCopyinSet = item['Remarks']
            componentStatus = item['Status']
            componentFormat = item['Media Format']  
        except KeyError:
            print ("nada")

    metadata = [
        {
            'parts': 'objects',
            'dc.identifier': comp_num,
            'dc.title': dc_title,
            'dc.creator': dc_creator,
            'dc.date': dc_date,
            'dc.format': dc_format2,
            'MoMA.objectID': dc_ident1,
            'MoMA.objectNumber': dc_ident2,
            'MoMA.classification': dc_format1,
            'MoMA.componentName': componentName,
            'MoMA.componentNumber': componentNumber,
            'MoMA.componentID': componentID,
            'MoMA.componentCreatedDate': componentDate,
            'MoMA.channels': componentChannels,
            'MoMA.copyInSet': componentCopyinSet,
            'MoMA.status': componentStatus,
        }
    ]
    metadata_path = os.path.join(transfer_path, 'metadata')
    if not os.path.exists(metadata_path):
        os.makedirs(metadata_path)
    metadata_path = os.path.join(metadata_path, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    return 0

if __name__ == '__main__':
    transfer_path = sys.argv[1]
    sys.exit(main(transfer_path))
 