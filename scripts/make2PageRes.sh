#!/bin/bash

##Usage: makeCV.sh <template> <output_filename> [-o <output directory> -d <data directory> ]
outdir=output
datadir=mydata


## Set the flags
while getopts o:d: flag
do
    case "${flag}" in
        o) outdir=${OPTARG};;
        d) data=${OPTARG};;
    esac
done


mkdir temp
mkdir $outdir

perl ./perl/YAMLtoRefList.pl $datadir/refs.yml "reverse" "select"
perl ./perl/MakeShortClassList.pl $datadir/CV.yml

cd temp

pandoc ../$datadir/CV.yml --template=../$1 -o ../$outdir/$2.pdf --pdf-engine=pdflatex


cd ..


