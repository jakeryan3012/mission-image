#!/bin/bash
echo 'enter dir & search'
read dir search
IFS=$'\n'
fiender=( $(find $dir ) )

a=0
b=0
while [ $a -le ${#fiender[@]} ]
		do 
 cat ${fiender[$a]} | grep -C 5 $search
echo ${fiender[$a]}
a=$[a+1]
#if [ -a $(pdfgrep $pingu ${fiender[$a]}) ]; then
#	$b = $b+1

#fi

#pdfgrep $pingu ${fiender[$a]}
					done
					echo "there was $b results"
					
					