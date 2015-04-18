#! /bin/tcsh
setenv utils $0:h
setenv models $0:h/models

$utils/fragmentor -i $1 -o $1.frag -h $models/$3.hdr $4

$utils/svmPreProc.pl $1.frag.svm scale=yes numfld=yes selfile=$models/$3.pri explicit=yes output=$1.frag.pp.svm

#box

if (!(-e $1.frag.pp.svm) || (-z $1.frag.pp.svm)) then
    #rm $1.frag.svm $1.frag.hdr $1.frag.frgControl >& /dev/null
    exit
endif

foreach f ($models/$3/*.model)
    $utils/libsvm/svm-predict $1.frag.pp.svm $f $1.tmp_pred
end


echo "{\"predicted_value\":$RANDOM,\"applicability_domain\":\"true\"}" > $2