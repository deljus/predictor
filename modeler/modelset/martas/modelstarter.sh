#! /bin/tcsh

if (!(-e $2) || (-z $2)) then
    exit
endif

rm $3

foreach f ($1/*.model)
    ./libsvm/svm-predict $2 $f $2.tmp_pred
    cat $2.tmp_pred >> $3
end
