# Copyright 2020 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

import argparse
from functools import wraps
import glob
import json
import os
from os import getenv
import os.path
from os.path import join
import os.path
import requests
import shutil
import stat
from string import Template
import subprocess

sphinx_opts    = '-n -N -j auto'
sphinx_build   = 'sphinx-build'
source_dir     = 'source'
build_dir      = 'build'
doxygen_xml    = join(build_dir, 'doxygen', 'xml', 'index.xml')
doxyfile       = join('source', 'Doxyfile')

script_dir = os.path.dirname(os.path.realpath(__file__))

args = None

indent = 0

def action(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        global indent
        log('%s:' % (wrapped.__name__))
        indent += 2
        x = func(*args, **kwargs)
        indent -= 2
        return x
    return wrapped

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        log('cd ' + self.newPath)
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

def log(*args, **kwargs):
    print(indent * ' ' + ' '.join(map(str,args)), flush = True, **kwargs)
    
def shell(c, **kwargs):
    log(c)
    if args.dry_run:
        return
    subprocess.run(c, shell=True, check=True, **kwargs)

def rm(dir):
    log('rm -rf', dir)
    if args.dry_run:
        return
    shutil.rmtree(dir, ignore_errors=True)
    
def copytree(src, dst):
    log('cp -r', src, dst)
    if args.dry_run:
        return
    shutil.copytree(src, dst)
    
def copy(src, dst):
    log('cp', src, dst)
    if args.dry_run:
        return
    shutil.copy(src, dst)
    
def makedirs(path):
    if os.path.exists(path):
        return
    log('mkdir -p', path)
    if args.dry_run:
        return
    os.makedirs(path)


sites = {
    'docs': {
        'pre': {
            'url': 'https://docs.pre.oneapi.com',
            's3_url': 's3://pre.oneapi.com/docs',
            'cpcode': '1081245',
            'aws-profile': 'oneapi-docs',
        },
        'prod': {
            'url': 'https://docs.oneapi.com',
            's3_url': 's3://oneapi.com/docs',
            'cpcode': '1081797',
            'aws-profile': 'oneapi-docs',
        }
    },
    'spec': {
        'pre': {
            'url': 'https://spec.pre.oneapi.com',
            's3_url': 's3://pre.oneapi.com/spec',
            'cpcode': '1081244',
            'aws-profile': 'oneapi-spec',
        },
        'prod': {
            'url': 'https://spec.oneapi.com',
            's3_url': 's3://oneapi.com/spec',
            'cpcode': '1081242',
            'aws-profile': 'oneapi-spec',
        }
    }
}

docs = {
    'dpcpp': {'site': sites['docs'],
              's3_paths': ['versions/latest/dpcpp']
    },
    'oneapi-spec': {'site': sites['spec'],
              's3_paths': ['versions/latest', 'versions/$version']
    },
}

def csite(prod=None):
    p = prod if prod else 'prod' if args.prod else 'pre'
    return cdoc()['site'][p]

def cdoc(doc=None):
    d = doc if doc else args.doc
    return docs[d]

def aws_prefix():
    return ('AWS_SHARED_CREDENTIALS_FILE=%s/credentials/aws-credentials.txt aws --profile %s s3'
            % (script_dir, csite()['aws-profile']))

def sync(src, dst):
    shell('%s sync %s --delete %s %s'
          % (aws_prefix(), ('--dryrun' if args.aws_dry_run else ''), src, dst))

def purge(site=None):
    s = site if site else csite()
    shell('./akamai purge --edgerc %s/credentials/akamai-credentials.txt delete --cpcode %s'
          % (script_dir, s['cpcode']))
    
def substitute(dc, string):
    return Template(string).substitute(dc)

def view(dc, site=None):
    s = site if site else csite()
    for path in cdoc()['s3_paths']:
        print(substitute(dc, 'Published at %s/%s/index.html' % (s['url'], path)))

def doc_cfg():
    if args.doc_cfg:
        with open(args.doc_cfg) as fin:
            return json.load(fin)
    else:
        return {}
    
@action
def sync_to_prod(action):
    if not args.doc:
        exit('%s requries --doc' % action)
    dc = doc_cfg()
    for path in cdoc()['s3_paths']:
        src = substitute(dc, '%s/%s' % (csite('pre')['s3_url'], path))
        dst = substitute(dc, '%s/%s' % (csite('prod')['s3_url'], path))
        sync(src, dst)
    purge(csite('prod'))
    view(dc, csite('prod'))

@action
def publish(action):
    if not args.doc or not args.html:
        exit('%s requries --doc and --html' % action)
    dc = doc_cfg()
    # first copy comes from local file system
    src = args.html
    for path in cdoc()['s3_paths']:
        dst = substitute(dc, '%s/%s' % (csite()['s3_url'], path))
        sync(src, dst)
        # subsequent copies are bucket to bucket
        src = dst
    purge()
    view(dc)

credential_files = ['aws-credentials.txt', 'akamai-credentials.txt']

def encrypt_credentials(action):
    print('enter passphrase:', end = ' ')
    passphrase = input()
    print()
    for file in credential_files:
        shell('rm -f %s/credentials/%s.gpg' % (script_dir, file))
        shell('gpg --batch --passphrase-fd 0 --symmetric --cipher-algo AES256 %s/credentials/%s'
              % (script_dir, file),
              input=passphrase, encoding='ascii')

def decrypt_credentials(action):
    passphrase = getenv('ONEAPI_PASSPHRASE')
    for file in credential_files:
        shell('gpg --yes --batch --passphrase-fd 0 --decrypt --output %s/credentials/%s %s/credentials/%s.gpg'
              % (script_dir, file, script_dir, file),
              input=passphrase, encoding='ascii')

@action
def setup(action):
    decrypt_credentials(action)
    url = 'https://github.com/akamai/cli/releases/download/1.1.5/akamai-1.1.5-linuxamd64'
    rm('%s/.akamai-cli' % getenv('HOME'))
    response = requests.get(url, allow_redirects=True)
    with open('akamai', 'wb') as fout:
        fout.write(response.content)
    st = os.stat('akamai')
    os.chmod('akamai', st.st_mode | stat.S_IEXEC)
    shell('./akamai', input='n\nn\nn\n', encoding='ascii')
    shell('./akamai install purge --force')


commands = {'decrypt-credentials': decrypt_credentials,
            'encrypt-credentials': encrypt_credentials,
            'setup': setup,
            'publish': publish,
            'sync-to-prod': sync_to_prod,
}

def main():
    global args
    parser = argparse.ArgumentParser(description='Publish docs.')
    parser.add_argument('action',choices=commands.keys())
    parser.add_argument('--doc', choices=docs.keys())
    parser.add_argument('--doc-cfg')
    parser.add_argument('--html')
    parser.add_argument('--prod', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--aws-dry-run', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    commands[args.action](args.action)

main()
