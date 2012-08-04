#! /bin/sh

NAME=BookmarksMenu
VERSION=`cat "VERSION"`

zip -9 -o $NAME-$VERSION.oxt \
  META-INF/* \
  description.xml \
  descriptions/* \
  icons/* dialogs/* \
  registration.components \
  pythonpath/**/*.py pythonpath/**/**/*.py \
  *.xcu *.xcs registration.py \
  resources/* \
  bookmarks/**/*.xml \
  help/**/* help/**/**/* \
  LICENSE CHANGES NOTICE Translators

