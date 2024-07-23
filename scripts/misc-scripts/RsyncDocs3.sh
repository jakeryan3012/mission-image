#!/bin/bash

if [ -z "$1" ]; then

echo "you must use the source file path as the second argument"
exit
fi

if [ -z "$2" ]; then

echo "you must use the destination file path as the third argument"
exit

fi


while true; do
	echo you are rsyncing from  "$1"/SHOOTDAYS/0[NUM]_DOCUMENTATION to "$2"
    read -p "Do you wish to continue? y or n" yn
   
    case $yn in
        [Yy]* )
		        cd "$1"
		        for d in *; do
				echo $d
				rsync -rvh $d/0[0-9]_DOCUMENTATION "$2"/$d/
				done
				break;;
				
				
				
        [Nn]* ) 
        		exit;;
        
        
        * ) 
        		echo "Please answer yes or no.";;
    esac
done

	
