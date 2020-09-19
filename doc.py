# Copyright 2020 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

import argparse
from functools import wraps
import glob
import os
import os.path
from os.path import join
import os.path
import requests
import shutil
import stat
import subprocess

sphinx_opts    = '-n -N -j auto'
sphinx_build   = 'sphinx-build'
source_dir     = 'source'
build_dir      = 'build'
doxygen_xml    = join(build_dir, 'doxygen', 'xml', 'index.xml')
doxyfile       = join('source', 'Doxyfile')

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
    
def shell(c):
    log(c)
    if args.dry_run:
        return
    subprocess.check_call(c, shell=True)

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
            's3_url': 's3://pre.oneapi.com/docs',
            'cpcode': '1081245'
        },
        'prod': {
            's3_url': 's3://oneapi.com/docs',
            'cpcode': '1081797'
        }
    },
    'spec': {
        'pre': {
            's3_url': 's3://pre.oneapi.com/spec',
            'cpcode': '1081244'
        },
        'prod': {
            's3_url': 's3://oneapi.com/docs',
            'cpcode': '1081242'
        }
    }
}

docs = {
    'dpcpp': {'sites': sites['docs'],
              'dir': 'dpcpp'},
    'spec': {'sites': sites['spec'],
              'dir': '.'},
}

def site_info():
    return doc_info()['sites']['prod' if args.prod else 'pre']

def doc_info():
    if not args.doc:
        exit('--doc is required')
    return docs[args.doc]

@action
def publish(action):
    d = doc_info()
    s = site_info()
    shell('aws s3 sync %s --delete doc/build/html %s/versions/latest/%s'
          % (('--dryrun' if args.aws_dry_run else ''), s['s3_url'], d['dir']))
    shell('./akamai purge delete --cpcode %s' % s['cpcode'])

@action
def encrypt_credentials(action):
    home = os.getenv('HOME')
    shell('gpg --output credentials/aws-credentials.gpg --symmetric --cipher-algo AES256 %s/.aws/credentials' % home)
    shell('gpg --output credentials/edgerc.gpg --symmetric --cipher-algo AES256 %s/.edgerc' % home)

@action
def install_credentials(action):
    home = os.getenv('HOME')
    makedirs(join(home, '.aws'))
    shell('gpg --quiet --batch --yes --decrypt --passphrase=%s'
          ' --output %s/.aws/credentials %s/credentials/aws-credentials.gpg'
          % (os.getenv('ONEAPI_PASSPHRASE'), home, args.root))
    shell('gpg --quiet --batch --yes --decrypt --passphrase=%s'
          ' --output %s/.edgerc %s/credentials/edgerc.gpg'
          % (os.getenv('ONEAPI_PASSPHRASE'), home, args.root))

@action
def install(action):
    install_credentials(action)
    url = 'https://github.com/akamai/cli/releases/download/1.1.5/akamai-1.1.5-linuxamd64'
    response = requests.get(url, allow_redirects=True)
    with open('akamai', 'wb') as fout:
        fout.write(response.content)
    st = os.stat('akamai')
    os.chmod('akamai', st.st_mode | stat.S_IEXEC)
    p = subprocess.run('./akamai', stdout=subprocess.PIPE, input='n\nn\nn\n', encoding='ascii')
    print(p.stdout)
    shell('./akamai install purge --force')


commands = {'install-credentials': install_credentials,
            'encrypt-credentials': encrypt_credentials,
            'install': install,
            'publish': publish,
}

def main():
    global args
    parser = argparse.ArgumentParser(description='Publish docs.')
    parser.add_argument('action',choices=commands.keys())
    parser.add_argument('--doc', choices=docs.keys())
    parser.add_argument('--root', default='.')
    parser.add_argument('--prod', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--aws-dry-run', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    commands[args.action](args.action)

main()
