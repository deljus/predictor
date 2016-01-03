#!/usr/bin/env bash
mkdir worktmp.$1
for i in $1.*.svm; do
    mkdir worktmp.$1/${i%.svm} &&
    cp ${i} worktmp.$1/${i%.svm}/file.svm &&
    awk '{print $1}' ${i%.svm} > worktmp.$1/${i%.svm}/file.SVMreg
done

# start dragos

for i in worktmp.$1/*; do
    echo ${i} `tail -n 1 ${i}/bestprop`
done > $1.results

rm -rf worktmp.$1
