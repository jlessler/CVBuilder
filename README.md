# CVBuilder
Build a CV from YAML data files.

## Terminal Instructions (Linux or Windows Subsystem for Linux)
1. Verify that the shell scripts in `scripts` are executable. 
1. Verify that the shell scripts do not have Windows line endings. Use `dos2unix` to convert these files if needed.
1. Install perl, pandoc, and tth as necessary.
1. Store your personal data (yml files) in a `mydata` folder.
1. If you need to make minor modifications to existing templates to suit your needs, consider storing and editing copies in a `mytemplates` directory. You can then reference your custom template in the command that creates the CV file. 
1. If you need to make a completely new and generalizable template, consider saving and committing this .tex file in the `templates` folder.
1. Run the appropriate shell script and template

`./scripts/<your_shell_script.sh> <template_dir>/<your_template.tex> <your_cv_name>`

See optional arguments for output and data directory at the top of the .sh scripts.



## ALPHA Functionality

Very preliminary and untested functionality has been
added to import and export refs.yml files to an 
SQLite database and for a front end to view and add
references (including from a DOI). 

To create an SQLite database from your yaml run:
`./sql_db/src/refs_yaml_to_sql.py`

To export these to `refs_exported.yml` run:
`./sql_db/src/refs_sql_to_yaml.py`

And for a simple web interface to edit the SQLite version run:
`./sql_db/src/app.py`