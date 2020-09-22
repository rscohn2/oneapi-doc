====================
 oneapi-doc-publish
====================

Script for publishing documents to oneapi.com server. The script
contains all necessary information of the url's on s3, usr's on the
server, credentials, etc. User

Prerequistes
============

On ubuntu::

  apt-get update
  xargs -a ubuntu-packages.txt apt-get install

Setup
=====

Before publishing, you must setup to decrypt the credentials and
install akamai binary::

  ONEAPI_PASSPHRASE=<passphrase> python oneapi-publish.py setup


Publishing
==========

Build the document. The html directory should be the root with an
index.html. Publish dpcpp to pre-production::

  python oneapi-publish.py publish --doc dpcpp --html dpcpp-ref/build/html

Sync dpcpp from pre-production to production::

  python oneapi-publish.py sync-to-prod --doc dpcpp

oneAPI spec is published in a directory with a version number and
needs to provide a config files with the version::

  python oneapi-publish.py publish --doc oneapi-spec --html oneapi-spec/build/html -doc-cfg oneapi-spec/oneapi-doc.cfg

Credentials
===========

The credentials are stored encrypted in credentials directory. They
are unencrypted with::

  python oneapi-publish.py decrypt-credentials

You will be prompted for the passphrase. Files with .txt suffix are
unencrypted, and .gpg for encrypted. Only the encrypted files should
be commited to the repo.

If you want to update the credentials, then unencrypt, modify the
unecrypted files, encrypt, and commit to the repo::

  ONEAPI_PASSPHRASE=<passphrase> python oneapi-publish.py decrypt-credentials
  # edit credentials/aws-credentials.txt
  python oneapi-publish.py encrypt-credentials
  git add credentials
  git commit -m 'update credentials'

Integration into CI System
==========================

The script can be used manually to publish, but is intended to be used
as part of a CI system so there is a workflow for review and approval,
as well as reproducibility of the published document.

Create a branch in this repo with the name of your document. Add a CI
script (.gitlab-ci.yml), copying dpcpp as an example. Publishing
requires the html files. They can be:

* commmitted to the branch
* obtained by cloning a tagged version in another repo that contains
  html
* obtained by cloning a tagged version in another repo with contains
  sources and building the document

The recommended workflow is publishing through a merge request to the
branch for the doc. Using dpcpp as an example::

  # clone this repo and checkout your doc branch
  git clone ...
  git checkout dpcpp
  # make a working copy
  git checkout -b dev/dpcpp
  # make changes, dep
  # commit and push
  git commit -m update
  git push -u origin dev/dpcpp

The commit will trigger publishing to pre-production. When you are
happy with the results, submit a merge request to dpcpp. The reviewer
can verify that it looks ok on staging and then accept the merge
request.

Another option is to publish to pre-production on a merge request, and
to publish to production on a commit.
