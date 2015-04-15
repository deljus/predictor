#!/usr/bin/env bash
#this script start model (fragmentor|condenser|svm) and then write JSON string to result_file

echo "{\"predicted_value\":$RANDOM,\"applicability_domain\":\"true\"}" > $2