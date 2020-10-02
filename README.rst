====================
 Level Zero Publish
====================


Procedure for changes.

Create a dev branch based on an up-to-date level-zero branch::

  git checkout level-zero
  git pull
  git checkout -b dev/level-zero

Make some changes, commit, and push::

  git add .
  git commit -m 'update level zero'
  git push -u origin dev/level-zero

Commit triggers a build in gitlab CI. Publishes on
https://spec.pre.oneapi.com/level-zero/latest/index.html

If it looks OK, submit a PR to merge dev/level-zero into level-zero.
