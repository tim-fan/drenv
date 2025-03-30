#!/bin/bash

REPO=drenv

image_tags=$(docker image ls -a --format='{{json .}}' | jq -r --arg REPO "${REPO}" -c '. | select( .Repository | startswith($REPO)) | .Tag ')

if [ -z "$image_tags" ]
then
    echo "No drenv images found."
    exit 0
fi

echo "Found drenv images:"
for tag in $image_tags
do
    echo " * ${tag}"
done

echo "Deleting all drenv images!"
read -p "Continue (y/N)?" choice
case "$choice" in 
  y|Y ) ;;
  * ) echo "abort"; exit 1;;
esac

for tag in $image_tags
do 
    docker rmi $REPO:$tag
done

echo ""
echo "done."
echo "You may now want to 'docker image prune'"