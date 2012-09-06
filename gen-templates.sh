#!/bin/bash
ARCHIVE_NAME=__tmpl.zip
OUTPUT_FILE=templates.b64

declare -a TEMPLATE_FILES=(
    'templates/main.html' 
    'templates/main.css'
    'templates/file.html'
    'templates/dir.html'
    'templates/images/tile.png'
    );


# add the files to the archive
echo "Archiving template files"
zip  $ARCHIVE_NAME ${TEMPLATE_FILES[@]}
echo "Done"
echo "------------------"

base64 $ARCHIVE_NAME > $OUTPUT_FILE 
rm $ARCHIVE_NAME 
echo "Templates archived with ZIP in $OUTPUT_FILE and encoded in base 64."