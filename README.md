# README #

### What is this repository for? ###
This repoitory contains the local logging script needed to use the LGR-AMR mobile observatory. It processes and logs the output of 
an LGR Ultraportable GHG Analyser and an Airmar Wx220 weather station and integrates with the GTA-Emissions
repository to create a live web map from the data output by the LGR and AMR.

### How do I get set up? ###
To set up the repository, clone the entire repository to your local machine and copy the lgr_amr.infile.template to
a new file called lgr_amr.infile.
The LGR-AMR.py script was written using Python 3.5 and other versions haven't been tested.
The script requires the following modules datetime, numpy, socket, theading, getpass, serial, pytz, paramiko and time.
These can all be downloaded with the anaconda conda package manager or should be included with your python installation.
Further instructions on running the software and using the mobile observatory can be found in the Mobile Lab Manual document.