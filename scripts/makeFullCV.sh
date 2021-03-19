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

perl ./perl/YAMLtoRefList.pl $datadir/refs.yml "reverse" 

cd temp


pandoc ../$datadir/CV.yml --template ../$1 -o ../$outdir/$2.pdf
pandoc ../$datadir/CV.yml --template ../$1 -o temp.tex 
tth temp.tex 
cp temp.html ../$outdir/$2.html

##Don't think this is worth doing since adobe pdf export is so much better
#pandoc -s  ../$outdir/$2.html -o  ../$outdir/$2.docx

cd ..   


