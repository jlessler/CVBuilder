##' Function takes a DOI and returns a reference that looks like the 
##' template for the references package that could be edited.
##' 
##' @param doi the doi to look up
##' @param file the file to write yaml to
##' 
##' @return the object that can be written to yaml
doi_ref_template <- function(doi, file="tmp.yml") {
  require(rcrossref)
  require(tidyverse)
  require(yaml)
  
  ref <- cr_works(doi)
  
  rc <- list()
  
  rc$authors <- str_c(ref$data$author[[1]]$family," ",
                     map_chr(str_extract_all(ref$data$author[[1]]$given,'\\b(\\w)'),paste,collapse=""))
  rc$doi <- ref$data$doi
  rc$year <- as.character(max(c(as.numeric(str_sub(ref$data$published.print,end=4)), 
                 as.numeric(str_sub(ref$data$published.online,end=4))),
                 na.rm=T))
  rc$title <- ref$data$title
  rc$journal<- ref$data$container.title
  rc$volume <- ref$data$volume
  rc$issue <- ref$data$issue
  write_yaml(list(rc),file)
  return(rc)
}
