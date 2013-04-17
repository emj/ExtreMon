#!/bin/bash

rm -f extremon.pdf && \
cd figures && ./generate.sh && cd - && \
xelatex extremon.tex && \
xelatex extremon.tex 

RESULT=$?

if [[ $USER == x3bb* ]]; then
    echo "continuous build.. no displaying of the result"
else
    if [ -f "extremon.pdf" ]; then
        evince extremon.pdf
    fi
fi

exit $RESULT
