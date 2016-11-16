#!/usr/bin/env bash
# make work dir
# $1 path/to/file{.[0-9]+}
# $2 svr or svc.
# $workdir /path/to/worktmp.file{/}
GACONF=/path/to/ga

datadir=$1
workdir=${datadir}/work

# make SVMreg file
for i in `find ${datadir} -type f -name "*.svm"`; do
    awk '{print $1}' ${i} > ${datadir}/file.SVMreg
done

${GACONF}/pilot_local.csh data_dir=${datadir} workdir=${workdir} >& ${datadir}/GA.log
rc=$?

killall pilot_local.csh local_SVMreg.csh svm-train svm-predict

if [[ ${rc} != 0 ]]; then exit ${rc}; fi  # return exitcode
