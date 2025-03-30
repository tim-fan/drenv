#!/bin/bash

containers=$(docker ps --all --format='{{json .}}' | jq -r -c '. | select( .Image | startswith("drenv")) | .Names ')

if [ -z "$containers" ]
then
    echo "No drenv containers found."
    exit 0
fi

echo "Found drenv containers:"
for container in $containers
do
    echo " * ${container}"
done

echo "Deleting all drenv containers!"
echo "You could lose some work!"
read -p "Continue (y/N)?" choice
case "$choice" in 
  y|Y ) ;;
  * ) echo "abort"; exit 1;;
esac

for container in $containers
do 
    docker container rm -f $container
done