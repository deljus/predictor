#!/usr/bin/env bash
# make work dir
workdir=worktmp.`basename $1`
mkdir ${workdir}
# copy svm files to individual workdirs
# make SVMreg files
for i in $1.*.svm; do
    curworkdir=${workdir}/${i%.svm}
    mkdir ${curworkdir} &&
    cp ${i} ${curworkdir}/file.svm &&
    awk '{print $1}' ${i} > ${curworkdir}/file.SVMreg
done

# start dragosscript

# parse results
for i in ${workdir}/*; do
    head -n 1 ${i}/bestprop | need grep > `basename ${i}`.result
done

rm -rf ${workdir}
