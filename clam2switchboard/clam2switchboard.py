#!/usr/bin/env python3

"""This tool obtains and converts CLAM webservice metadata to CLARIN switchboard registry metadata, writing the necessary JSON files"""

import sys
import argparse
import json
import os
import urllib.request
from copy import deepcopy

from clam.common.client import CLAMClient
from clam.common.parameters import StringParameter, StaticParameter, ChoiceParameter, BooleanParameter
import codemeta

def first(*args):
    """Returns the first non-zero argument"""
    for arg in args:
        if arg:
            if isinstance(arg, (list,tuple)):
                #squash multiple into one for now
                return ", ".join(arg)
            else:
                return arg
    return ""

def convert(**kwargs):
    """Convert CLAM webservice metadata to switchboard registry metadata"""

    #Connect to CLAM service and retrieve data
    client = CLAMClient(kwargs['url'])
    data = client.porch()


    if kwargs['codemeta']: #has codemeta metadata been passed? then use it
        if kwargs['codemeta'].startswith(("http://","https://")):
            #download if remote
            try:
                codemetadata = urllib.request.urlopen(kwargs['codemeta']).read()
            except:
                pass
        else:
            #assume it is a local file
            with open(kwargs['codemeta'],'r',encoding='utf-8') as f:
                codemetadata = json.loads(f)
    else:
        codemetadata = {}


    #Set the base entry
    if data.authentication == "none":
        auth_msg = "no"
    else:
        auth_msg = "yes"
        if data.system_register_url:
            auth_msg += ". Before tool use, Please register at " + data.system_register_url

    #set logo (automaticallty finds matching logos in ../logos dir, assuming tool is run in tools/ dir!)
    if 'logo' in kwargs and kwargs['logo']:
        logo = kwargs['logo']
    elif os.path.exists("../logos/" + data.system_id.lower() + ".jpg"):
        logo = data.system_id.lower() + ".jpg"
    elif os.path.exists("../logos/" + data.system_id.lower() + ".png"):
        logo = data.system_id.lower() + ".png"
    else:
        logo = None

    baseentry = {
        "name": first(data.system_name, codemetadata.get("name")),
        "task": first(kwargs['task'], codemetadata.get("tooltask"), "unknown"),
        "deployment": "production" if not kwargs['dev'] else 'development',
        "softwareType": "qualitative",
        "description": first(data.description, codemetadata.get("description")),
        "homepage": first(data.system_url, codemetadata.get("url"), codemetadata.get("codeRepository"), data.baseurl),
        "licence": first(data.system_license, codemetadata.get("license")),
        "location": first(data.system_affiliation, "unknown"), #not really the same, but will have to do for now
        "creators": data.system_author,
        "contact": {
            "person": data.system_email, #we just use the e-mail as we can't strictly identify it with a person
            "email": data.system_email,
        },
        "version": first(data.system_version if data.system_version else None, codemetadata.get("version")),
        "authentication":  auth_msg,
        "url": data.baseurl,
        "logo": logo,
        "mapping": {},
        "parameters": {},
        "mimetypes": [],
        "languages": []
    }
    if data.system_affiliation:
        #add affiliation to creators as well:
        if baseentry['creators']:
            baseentry['creators'] += " (" + data.system_affiliation + ")"
        else:
            baseentry['creators'] = data.system_affiliation

    #Set the derived entries (based on the clam profiles/inputtemplates) and write a registry file for each
    for profile in data.profiles:
        required = sum( 1 for inputtemplate in profile.input if not inputtemplate.optional)
        if required > 1:
            print("Notice: Skipping a profile in this webservice because it has multiple mandatory input parameters. The switchboard does not support this.",file=sys.stderr)
            continue

        inputtemplate = next(it for it in profile.input if not it.optional)

        entry_name = baseentry['name'] + " (" + inputtemplate.label+")"
        entry_filename = entry_name + '.json'

        #instantiate entry derived from base entry
        entry = deepcopy(baseentry)
        entry['name'] = entry_name


        if os.path.exists(entry_filename):
            with open(entry_filename,'r',encoding='utf-8') as f:
                existing_entry = json.loads(f.read())
        else:
            existing_entry = {}

        #override any empty/missing values with values from the existing_entry (if any):
        for key, value in existing_entry.items():
            if key not in entry or entry[key] in ("",None,"unknown","unspecified"):
                entry[key] = existing_entry[key]


        entry['parameters'] = {"project":"new","input":"self.linkToResource"}
        #                                 ^-- new is an actionable value for CLAM which
        #                                     makes it assign a random ID
        #                                               ^-- self.linkToResource is an actionable value for the switchboard


        setparams = [] #list of (prefix, Parameter) tuples

        langparameter = None
        langparameter_prefix = None

        #Collecting mandatory parameters (global)
        for _, parameters in data.parameters:
            for parameter in parameters:
                if 'langparam' not in kwargs or parameter.id != kwargs['langparam']:
                    if parameter.value is not False or parameter.required:
                        setparams.append( ("", parameter) )
                else:
                    langparameter = parameter
                    langparameter_prefix = ""

        #Collecting mandatory parameters (local)
        for parameter in inputtemplate.parameters:
            if 'langparam' not in kwargs or parameter.id != kwargs['langparam']:
                if parameter.value is not False or parameter.required:
                    setparams.append( (inputtemplate.id + '_', parameter) )
            elif not langparameter:
                langparameter = parameter
                langparameter_prefix = inputtemplate.id

        #Set collected parameters
        for prefix, parameter in setparams:
            if 'parameters' in existing_entry and prefix + parameter.id in 'existing_entry':
                #take the parameter from the existing entry (this allows manual override of any parameters)
                entry['parameters'][prefix + parameter.id] = existing_entry['parameters'][prefix + parameter.id]
            elif isinstance(parameter, StaticParameter):
                #no need to set static parameters, CLAM will do that
                continue
            elif parameter.value is not False:
                entry['parameters'][prefix + parameter.id] = parameter.value
            elif isinstance(parameter, ChoiceParameter):
                #just take the first choice
                firstchoice = parameter.choices[0]
                if isinstance(firstchoice, (list,tuple)): firstchoice = firstchoice[0]
            elif isinstance(parameter, BooleanParameter):
                #unset boolean, okay
                entry['parameters'][prefix + parameter.id] = False
            else:
                print("WARNING: Unable to automatically determine a value for mandatory parameter " + parameter.id + ", edit the resulting JSON entry manually to set this!",file=sys.stderr)
                entry['parameters'][prefix + parameter.id] = "---- SET THIS VALUE MANUALLY! ----"


        if kwargs['langs']:
            #explicitly provided, hard override
            entry['languages'] = kwargs['langs'].split(',')
        elif langparameter is None:
            if 'languages' in existing_entry:
                #no language parameter
                entry['languages'] = existing_entry['languages']
        else:
            #we have a language parameter, collect language options
            langs = []
            if langparameter is not None:
                if isinstance(langparameter, (StaticParameter, StringParameter)):
                        if len(langparameter.value) == 3: #assume iso-639-3
                            kwargs['langencoding'] = 3
                        elif len(langparameter.value) == 2: #assume iso-639-1
                            kwargs['langencoding'] = 1
                elif isinstance(langparameter, ChoiceParameter):
                    for choice in langparameter.choices:
                        if isinstance(choice, tuple) and len(choice) == 2: #key,value pair, grab the key
                            choice = choice[0]
                        if len(choice) == 3: #assume iso-639-3
                            kwargs['langencoding'] = 3
                        elif len(choice) == 2: #assume iso-639-1
                            kwargs['langencoding'] = 1
                        else:
                            print("WARNING: Skipping uninterpretable language code: ", choice ,file=sys.stderr)
                            continue

                        if choice not in langs:
                            langs.append(choice)

            entry['languages'] = langs
            entry['parameters']['lang'] = "self.linkToResourceLanguage"
            entry['mapping']['lang'] = langparameter_prefix + '_' + langparameter.id

        entry['mapping']['input'] =  inputtemplate.id + '_url'
        entry['mimetypes'] = [ inputtemplate.formatclass.mimetype ]
        entry['output'] = list(set( output.formatclass.mimetype for output in profile.outputtemplates() ))
        entry['langEncoding'] = "639-" + str(kwargs['langencoding'])

        print("Writing " + entry_filename,file=sys.stderr)
        with open(entry_filename,'w',encoding='utf-8') as f:
            print(json.dumps(entry,ensure_ascii=False,indent=4),file=f)
    return entry

def main():
    parser = argparse.ArgumentParser(description="Converts metadata for a CLAM webservice to Switchboard format", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-u','--url', type=str,help="URL to a CLAM webservice", action='store',required=True)
    parser.add_argument('-m','--codemeta', type=str,help="Codemeta metadata", action='store',default="",required=False)
    parser.add_argument('--dev', help="Target development instead of production", action='store_true',default="",required=False)
    parser.add_argument('--task', help="A short description of the tool's task (will put in in this category in the switchboard)", action='store',required=True)
    parser.add_argument('--logo', help="Filename (not full path) of a logo image, needs to be put in registry manually", action='store',required=False)
    parser.add_argument('-l','--langs', type=str,help="Comma separated list of languages (iso-639-3 codes). If explicitly provided, they will not be derived from the service (which may not always work)", action='store',default="",required=False)
    parser.add_argument('--langparam', type=str,help="The name of the CLAM parameter that stores the language (if available at all)", action='store',default="language",required=False)
    parser.add_argument('-e','--langencoding', type=int,help="Language encoding, set to 1 for iso-639-1 and 3 for iso-639-3", action='store',default=3,required=False)
    args = parser.parse_args()
    #args.storeconst, args.dataset, args.num, args.bar
    args = parser.parse_args()
    convert(**args.__dict__)

if __name__ == '__main__':
    main()




