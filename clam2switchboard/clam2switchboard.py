#!/usr/bin/env python3

import sys
import argparse
import json
from copy import deepcopy

from clam.common.client import CLAMClient


def convert(**kwargs):
    client = CLAMClient(kwargs['url'])
    data = client.porch()
    if data.authentication == "none":
        auth_msg = "no"
    else:
        auth_msg = "yes"
        if data.system_register_url:
            auth_msg += ". Before tool use, Please register at " + data.system_register_url

    baseentry = {
        "name": data.system_name,
        "task": kwargs['task'],
        "deployment": "production" if not kwargs['dev'] else 'development',
        "softwareType": "qualitative",
        "description": data.description,
        "homepage": data.system_url,
        "licence": data.system_license,
        "creators": data.system_author,
        "contact": {
            "person": "Contact person",
            "email": data.system_email,
        },
        "version": data.system_version if data.system_version else None,
        "authentication":  auth_msg,
    }
    if data.system_affiliation:
        if baseentry['creators']:
            baseentry['creators'] += " (" + data.system_affiliation + ")"
        else:
            baseentry['creators'] = data.system_affiliation

    for profile in data.profiles:
        required = sum( 1 for inputtemplate in profile.input if not inputtemplate.optional)
        if required > 1:
            print("Notice: Skipping a profile in this webservice because it has multiple mandatory input parameters. The switchboard does not support this.",file=sys.stderr)
            continue

        inputtemplate = next(it for it in profile.input if not it.optional)

        entry = deepcopy(baseentry)
        entry['name'] += " (" + inputtemplate.label+")"

        entry['parameters'] = {"project":"new","input":"self.linkToResource"}
        langparameter = None
        for parameter in inputtemplate.parameters:
            if parameter.id.lower() == "language":
                langparameter = parameter.id

        entry['mapping'] = {"input": inputtemplate.id + '_url' }
        if langparameter:
            entry['parameters']['lang'] = "self.linkToResourceLanguage"
            entry['mapping']['lang'] = langparameter


        entry['mimetypes'] = [ inputtemplate.formatclass.mimetype ]
        entry['output'] = [ output.formatclass.mimetype for output in profile.output ]

        entry['languages'] = kwargs['langs'].split(',')
        entry['langEncoding'] = "639-" + str(kwargs['langencoding'])

        print("Writing " + entry['name'] + ".json" ,file=sys.stderr)
        with open(entry['name'] + ".json",'w',encoding='utf-8') as f:
            print(json.dumps(entry,ensure_ascii=False,indent=4),file=f)
    return entry

def main():
    parser = argparse.ArgumentParser(description="Converts metadata for a CLAM webservice to Switchboard format", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-u','--url', type=str,help="URL to a CLAM webservice", action='store',required=True)
    #parser.add_argument('-m','--codemeta', type=str,help="Codemeta metadata", action='store',default="",required=False)
    parser.add_argument('--dev', help="Target development instead of production", action='store_true',default="",required=False)
    parser.add_argument('--task', help="A short description of the tool's task (will put in in this category in the switchboard)", action='store',required=True)
    parser.add_argument('-l','--langs', type=str,help="Comma separated list of languages (iso-639-3 codes)", action='store',default="",required=False)
    parser.add_argument('-e','--langencoding', type=int,help="Language encoding, set to 1 for iso-639-1 and 3 for iso-639-3", action='store',default=3,required=False)
    args = parser.parse_args()
    convert(**args.__dict__)

if __name__ == '__main__':
    main()




