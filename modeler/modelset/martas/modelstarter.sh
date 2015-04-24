#! /bin/tcsh

if (!(-e $2) || (-z $2)) then
    exit
endif

if ((-e $3) && !(-z $3)) then
    rm $3
endif

foreach f ($1/*.model)
    ./libsvm/svm-predict -q $2 $f $2.tmp_pred
    cat $2.tmp_pred >> $3
end
