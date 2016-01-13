#!/usr/bin/env bash
# make work dir
# $1 path/to/file{.[0-9]+}
# $workdir /path/to/worktmp.file{/}
workdir=`dirname $1`/worktmp.`basename $1`
mkdir -p ${workdir}
# copy svm files to individual workdirs
# make SVMreg files
for i in `find $(dirname $1) -type f -name "$(basename $1).*.svm"`; do
    curworkdir=${workdir}/`basename ${i%.svm}`
    mkdir ${curworkdir} &&
    cp ${i} ${curworkdir}/file.svm &&
    awk '{print $1}' ${i} > ${curworkdir}/file.SVMreg
done

# start dragosscript
for i in ${workdir}/* ; do
    ${GACONF}/pilot_local.csh data_dir=${i} workdir=${i}/work >& ${i}/msg.log
done

# parse results
for i in ${workdir}/*; do
    head -n1 ${i}/work/`head -n1 ${i}/work/best_pop | grep -oP "attempt.[0-9]+"`/svm.pars > `dirname $1`/`basename ${i}`.result
done

# remove tmp
rm -rf ${workdir}
