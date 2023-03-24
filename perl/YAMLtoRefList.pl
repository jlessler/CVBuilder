use strict;
use warnings;
use YAML::Tiny;

my $filename = "temp/refs.tex";
open(my $fh, ">", $filename) or die "could not open";

my $yaml = YAML::Tiny->read($ARGV[0]);

my $myname = $yaml->[0]{myname};

    
my @papers = @{$yaml->[0]{papers}};
my @papersNoPeer;
if ($yaml->[0]{papersNoPeer}) { 
    @papersNoPeer = @{$yaml->[0]{papersNoPeer}};
}

my @preprints;
if ($yaml->[0]{preprints}) { 
    @preprints = @{$yaml->[0]{preprints}};
}

my @chapters;
if ($yaml->[0]{chapters}) {
    @chapters = @{$yaml->[0]{chapters}};
}

my @letters;
if ($yaml->[0]{letters}) {
    @letters = @{$yaml->[0]{letters}};
}

my @scipres;
if ($yaml->[0]{scimeetings}) {
    @scipres = @{$yaml->[0]{scimeetings}};
}

my $num_args = $#ARGV + 1;

my $select_only = 0;
my $select_chol_only = 0;

# some tracking variables to be written out at the end.
my $n_peer = 0;
my $n_no_peer = 0;
my $n_chapters = 0;
my $n_preprint = 0;
my $n_letters = 0;
my $n_pres = 0;


if ((($num_args > 1) && ($ARGV[1] eq "reverse")) || (($num_args > 2) && ($ARGV[2] eq "reverse"))) {
    @papers = reverse @papers;
    if ($yaml->[0]{papersNoPeer}) {
	@papersNoPeer = reverse @papersNoPeer;
    }
    if ($yaml->[0]{preprints}) {
	@preprints = reverse @preprints;
    }
    if ($yaml->[0]{chapters}) {
	@chapters = reverse @chapters;
    }
    if ($yaml->[0]{letters}) {
	@letters = reverse @letters;
    }
    if ($yaml->[0]{scimeetings}) {
	@scipres = reverse @scipres;
    }
} 

if ((($num_args > 1) && ($ARGV[1] eq "select")) || (($num_args > 2) && ($ARGV[2] eq "select"))) {
    print "Select Only\n";
    $select_only = 1;
}

if ((($num_args > 1) && ($ARGV[1] eq "select_chol")) || (($num_args > 2) && ($ARGV[2] eq "select_chol"))) {
    print "Select Cholera Only\n";
    $select_chol_only = 1;
}



#Makes the tex for an individual paper
sub print_paper {
    my($paper, $fh) = @_;
    
    print $fh "\\item ";
    my $nauth = keys @{$paper->{authors}};
    my $authnum = 0;
    for my $author (@{$paper->{authors}}) {
	#if ($author eq "Lessler J") {
	if ($author eq $myname) {
	    print $fh "\\textbf{",$author,"}";

	    if ($paper->{corr}) {
		print $fh "\$^\\dagger\$";
	    }
	} else {
	    print $fh $author;
	}

	if ($paper->{cofirsts} && $authnum < $paper->{cofirsts}) {
	    print $fh "\$^\\ddagger\$";
	}
	$authnum++;

	if ($paper->{coseniors} && $nauth <= $paper->{coseniors}) {
	    print $fh "\$^\\ddagger\$";
	}
	
	if ( 0 < --$nauth ) {
	    print $fh ", ";
	} 
    }
    print $fh " (", $paper->{year},") ";
    print $fh $paper->{title}, ". ";

    print $fh "\\journal{", $paper->{journal},"}.";

    if ($paper->{volume}) {
	print $fh " ", $paper->{volume};
    }

    if ($paper->{issue}) {
	print $fh "(", $paper->{issue},")";
    }

    if ($paper->{pages}) {
	if ($paper->{volume}) {
	    print $fh ":";
	} else {
	    print $fh " ";
	}
	
	print $fh $paper->{pages};
    }

    if ($paper->{doi}) {
	print $fh "\\\\ \\doi{",$paper->{doi},"}";
    }

    if ($paper->{inpress}) {
	print $fh " \\emph{In Press}";
    }
    
    print $fh "\n\n";
}


for my $paper (@papers) {
    $n_peer++;
    if ($select_only && !$paper->{select}){ next;}
    if ($select_chol_only && !$paper->{select_chol}){ next;}
    print_paper($paper, $fh);
}

close $fh;

if ($yaml->[0]{papersNoPeer}) { 
$filename = "temp/refs_norev.tex";
open($fh, ">", $filename) or die "could not open";


    for my $paper (@papersNoPeer) {
	$n_no_peer++;
	if ($select_only && !$paper->{select}){ next;}
	print_paper($paper, $fh);
    }
}

close $fh;


if ($yaml->[0]{preprints}) { 
$filename = "temp/preprints.tex";
open($fh, ">", $filename) or die "could not open";


    for my $paper (@preprints) {
	$n_preprint++;
	if ($select_only && !$paper->{select}){ next;}
	print_paper($paper, $fh);
    }
}

close $fh;


if ($yaml->[0]{chapters}) { 
$filename = "temp/chapters.tex";
open($fh, ">", $filename) or die "could not open";

for my $chapter (@chapters) {
    $n_chapters++;
    print $fh "\\item ";

    my $nauth = keys @{$chapter->{authors}};
    
    for my $author (@{$chapter->{authors}}) {
	if ($author eq "Lessler J") {	    
	    print $fh "\\textbf{",$author,"}";	  
	} else {
	    print $fh $author;
	}

	if ( 0 < --$nauth ) {
	    print $fh ", ";
	} 

    }

    print $fh " (",$chapter->{year},") ";
    print $fh $chapter->{title}, ". ";
    print $fh "\\textit{", $chapter->{book},"}";
    
    if ($chapter->{publisher}) {
	print $fh ", ",$chapter->{publisher};
    }
    print $fh ".";

}

close $fh;
}

if ($yaml->[0]{letters}) { 
$filename = "temp/letters.tex";
open($fh, ">", $filename) or die "could not open";

for my $letter (@letters) {
    $n_letters++;
    if ($select_only && !$letter->{select}){ next;}
    print_paper($letter, $fh);
}

close $fh;
}

if ($yaml->[0]{scimeetings}) { 
$filename = "temp/scipres.tex";
open($fh, ">", $filename) or die "could not open";

for my $scipres (@scipres) {
    $n_pres++;
    if ($select_only && !$scipres->{select}){ next;}
    print $fh "\\item ";

    my $nauth = keys @{$scipres->{authors}};
    
    for my $author (@{$scipres->{authors}}) {
	if ($author eq "Lessler J") {	    
	    print $fh "\\textbf{",$author,"}";	  
	} else {
	    print $fh $author;
	}

	if ( 0 < --$nauth ) {
	    print $fh ", ";
	} 

    }

    print $fh " (",$scipres->{year},") ";
    print $fh $scipres->{title}, ". ";
    print $fh $scipres->{conference},". ";
    print $fh "(\\textit{",$scipres->{type},"})\n";
    
}

close $fh;
    }

$filename = "temp/refvars.tex";
open($fh, ">", $filename) or die "could not open";

print $fh "\\newcommand\\npeer{",$n_peer,"}\n";
print $fh "\\newcommand\\nnopeer{",$n_no_peer,"}\n";
print $fh "\\newcommand\\nchapters{",$n_chapters,"}\n";
print $fh "\\newcommand\\nletters{",$n_letters,"}\n";
print $fh "\\newcommand\\npres{",$n_pres,"}\n";
print $fh "\\newcommand\\npreprint{",$n_preprint,"}\n";

close $fh;
