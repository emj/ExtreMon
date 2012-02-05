#!/bin/bash


screen -ls | while read line
do
  case "$line" in 
      *commonrail_* ) PID=`echo $line | awk -F"." '{print $1}'` ; echo "Killing $line" ; kill $PID ;;
  esac
done
