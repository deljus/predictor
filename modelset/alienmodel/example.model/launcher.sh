#!/usr/bin/env bash
#example model
~/ChemAxon/JChem/bin/molconvert smiles structures -o structures.smi
echo 'TEXT:id,TEXT:pH=3.00,TEXT:pH=3.50,TEXT:pH=4.00,TEXT:pH=4.50,TEXT:pH=5.00,TEXT:pH=5.50,TEXT:pH=6.00,TEXT:pH=6.50,TEXT:pH=7.00,TEXT:increments,TEXT:logP' > results.csv
~/ChemAxon/JChem/bin/cxcalc -i my -t my logd -l 3 -u 7 -s 0.5 logp -t increments,logP -p 3 structures.smi | tail -n +2 | sed 's/,/./g' | sed 's/\t/,/g' >> results.csv