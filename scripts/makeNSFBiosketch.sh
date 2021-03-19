#!/bin/bash

#get filtered references - other
perl FilterPubs.pl NSFBiosketchInfoEEID.yml other otherrefs.yml
perl ./YAMLtoRefList.pl otherrefs.yml "reverse" 

#hacky, but let's just rename the .tex file
mv refs.tex otherrefs.tex


#get filtered references
perl FilterPubs.pl NSFBiosketchInfoEEID.yml current currentrefs.yml
perl ./YAMLtoRefList.pl currentrefs.yml "reverse" 

#hacky, but let's just rename the .tex file
mv refs.tex currentrefs.tex

# merge the yaml files to make PDF ....a little clunky
head -n -1 CV.yml > tmp.yml

cat tmp.yml $1 | pandoc --template=NSFTemplate.tex -o NSFBiosketch.pdf

#clean up temp files
#rm tmp.yml
