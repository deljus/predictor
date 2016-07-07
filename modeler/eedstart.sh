#!/usr/bin/env bash

[ $# -ge 1 -a -f "$1" ] && input="$1" || input="-"

export CHMXN_DIR=/home/stsouko/ChemAxon
export CLASSPATH=$CHMXN_DIR/JChem/lib/jchem.jar:/home/stsouko:

cat ${input} | java Utils.react_desc -svm
