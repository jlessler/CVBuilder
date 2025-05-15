#!/bin/bash

##Usage: makeCV.sh <template> <output_filename> [-o <output directory> -d <data directory> ]

outdir=output
datadir=mydata


## Set the flags
# while getopts o:d: flag
# do
#     case "${flag}" in
#         o) outdir=${OPTARG};;
#         d) datadir=${OPTARG};;
#     esac
# done

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o)
            outdir="$2"
            shift 2
            ;;
        -d)
            datadir="$2"
            shift 2
            ;;
        *)
            # Capture positional arguments
            if [[ -z "$template" ]]; then
                template="$1"
            elif [[ -z "$output_filename" ]]; then
                output_filename="$1"
            else
                echo "Unknown argument: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

mkdir temp
echo $1
echo $2
echo $template
echo $output_filename

mkdir $outdir

echo $datadir

perl ./perl/YAMLtoRefList.pl $datadir/refs.yml "reverse" 

cd temp


pandoc ../$datadir/CV.yml --template ../$template -o ../$outdir/$output_filename.pdf
pandoc ../$datadir/CV.yml --template ../$template -o temp.tex 
tth temp.tex 
cp temp.html ../$outdir/$2.html

##Don't think this is worth doing since adobe pdf export is so much better
#pandoc -s  ../$outdir/$2.html -o  ../$outdir/$2.docx

cd ..   


