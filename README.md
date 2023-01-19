# TME Radio Logger
Simple utility to retrieve measured values from Papouch TME Radio unit.

## Setup
Install all the required Python libraries:
```
pip3 install -r requirements.txt
```
Create config file by editing the provided `config.yaml.example` and place it
in the script's working directory or specify its location in `CONFIG_FILE`
enviroment variable.

Running the script reads all available values and writes them out to 
a .csv file according to the config. Use cron to schedule regular execution
with `crontab -e`, adding e.g.:
```
 */3 *  * * * python /path/to/script/templog.py 2>&1 | ts "\%F \%T" >> /path/to/log/out.log
```
 
