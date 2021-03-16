use strict;
use warnings;
use YAML::Tiny;
use Data::Dumper;

##my $yaml = YAML::Tiny->read('CV.yml');
my $yaml = YAML::Tiny->read($ARGV[0]);
my @classes = @{$yaml->[0]{classes}};

my %instructor_hash;
my %lecturer_hash;
my %lab_hash;

#put all the years in class of the appropriate catagory
for  my $class (@classes) {
    if ($class->{role} eq "Instructor" or $class->{role} eq "Co-Instructor") {
	push @{$instructor_hash{$class->{class}}}, $class->{year};
    } 

    if  (index($class->{role}, "Lecturer") != -1) {
	push @{$lecturer_hash{$class->{class}}}, $class->{year};
    } 

    if  (index($class->{role}, "Lab Instructor") != -1) {
	push @{$lab_hash{$class->{class}}}, $class->{year};
    }

    
}

# #print out as a new yaml file
open(my $fh, ">", "temp/ShortClass.tex") or die "could not open";

print $fh "\\textbf{Instructor:} ";
foreach my $class (keys %instructor_hash) {
    print $fh $class," (";
    my $nyears = keys @{$instructor_hash{$class}};
    
    for my $year (@{$instructor_hash{$class}}) {
	print $fh $year;

	if ( 0 < --$nyears ) {
	    print $fh ", ";
	}
    }
    print $fh ");\n";
}

print $fh "\\textbf{Lecturer:} ";
foreach my $class (keys %lecturer_hash) {
    print $fh $class," (";
    my $nyears = keys @{$lecturer_hash{$class}};
    
    for my $year (@{$lecturer_hash{$class}}) {
	print $fh $year;

	if ( 0 < --$nyears ) {
	    print $fh ", ";
	}
    }
    print $fh ");\n";
}


print $fh "\\textbf{Lab Instructor:} ";
my $nclass = (keys %lab_hash);
foreach my $class (keys %lab_hash) {
    print $fh $class," (";
    my $nyears = keys @{$lab_hash{$class}};
    
    for my $year (@{$lab_hash{$class}}) {
	print $fh $year;

	if ( 0 < --$nyears ) {
	    print $fh ", ";
	}
    }

    if (0 < --$nclass) {
	print $fh ");\n";
    } else {
	print $fh ")\n";
    }
}



close $fh;

# That did not work, try latex
# open(my $fh, ">", "ShortClass.yml") or die "could not open";

# print $fh "instructorclass:\n";
# foreach my $class (keys %instructor_hash) {
#     print $fh "  - title: ",$class,"\n";
#     print $fh "    years:\n";

#     for my $year (@{$instructor_hash{$class}}) {
# 	print $fh "      - ", $year,"\n";
#     }
# }

# print $fh "lecturerclass:\n";
# foreach my $class (keys %lecturer_hash) {
#     print $fh "  - title: ",$class,"\n";
#     print $fh "    years:\n";

#     for my $year (@{$lecturer_hash{$class}}) {
# 	print $fh "      - ", $year,"\n";
#     }
# }


# print $fh "labclass:\n";
# foreach my $class (keys %lab_hash) {
#     print $fh "  - title: ",$class,"\n";
#     print $fh "    years:\n";

#     for my $year (@{$lab_hash{$class}}) {
# 	print $fh "      - ", $year,"\n";
#     }
# }


# close $fh;
