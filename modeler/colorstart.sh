#!/usr/bin/env bash

export SETUP_DIR=/home/stsouko/Utils
export FORCEFIELD=${SETUP_DIR}/cvffTemplates.xml
export CHMXN_DIR=/home/stsouko/ChemAxon
export CLASSPATH=${CHMXN_DIR}/JChem/lib/jchem.jar:/home/stsouko:

java Utils/CA_Prop_Map2011 -f $1 -o $2 -stdoptions $3
