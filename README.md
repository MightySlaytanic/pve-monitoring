# pve-monitoring

Proxmox VE temperature and disk-health stats upload to influxdb2

**DISCLAIMER**: this tool has been developed to monitor my own Intel NUC with a SATA and an NVME disk. You can freely use and modify it to your needs, but I hold no responsibility if not used properly.

## Requirements

The script requires the module influxdb-client to be installed on your PVE hosts, with pip:

```bash
apt install pip lmsensors smartctl nvme-cli -y

# If the following fails, read the next section about Python Virtual environment
pip install influxdb-client
```

And a functioning InfluxDB v2 instance hosted on your local LAN.  

### Installing python modules in a Python Virtual Environment
#### UPDATE 2023-06-28
If you're running on a Debian 12 system (such as proxmox v8), you are required to create a python virtual environment with influxdb-client installed and then point at the python3 executable within that environment.  
For example, to create the virtual-env in /root/scripts/venv and install the required package do the following:
##### Install python env
`apt install python3-venv -y`

##### Configure python virtual environment
```bash
python3 -m venv /root/scripts/venv
. /root/scripts/venv/bin/activate
pip3 install influxdb-client
deactivate
```
##### Adjust 'python' in sh
Then, invoke the python script by passing it as an argument to /root/scripts/venv/bin/python3 executable or change the shabang string on the first line of the script.
You can do this by adjusting each *.sh file, to replace `python3` with the path you made, in this example `/root/scripts/venv/bin/python3`.  

## Script Overview

### pve_disks_stats_to_influxdb2.py

This script retrieves data from sata disks using smartctl and from nvme disks via nvmcli tools.
You can modify the DEVICES dictionary by changing the path of the sata or nvme disk or by removing one of the two entries. Multiple disks per device type are supported by adding the device path to the array.

### pve_temp_stats_to_influxdb2.py

This script uses the lm_sensors command to retrieve temperature info from the device. It has been tailored for the output of the command executed on an Intel NUC i7 10th Gen device, so it may not work for your device without proper changes to the code

### Usage

#### Run location

You will need to create these scripts on each host in your PVE cluster (or on your singular host).
This location will be used throughout this guide for variable replacements.
For the purpose of this guide, we will assume `/home/scripts`, make sure you are replacing this particular path with your path of choice.

#### Variables

Both tools requires you to set some environment variables
You can either set these directly in Bash (below #1), or directly editing each script (further below #2)

| Variable | What to input |
| ----- | ----- |
| INFLUX_HOST | The host URL or IP for your InfluxDb instance|
| INFLUX_PORT | The port for your InfluxDB instance |
| INFLUX_TOKEN | The admin token for your InfluxDB instance |
| INFLUX_ORGANIZATION | Your InfluxDB Org Name |
| INFLUX_BUCKET | Your InfluxDB Bucket Name |
| HOST_TAG | The name of your PVE Host |
| DATA_UNITS_READ_BASE | Set it to the read bytes if you want to count read bytes from a non zero value. Otherwise set it to 0. Ex: 300_000_000_000 is 300GB |
| DATA_UNITS_WRITTEN_BASE | Set it to the written bytes if you want to count written bytes from a non zero value. Otherwise set it to 0 |
| CPU_CORES | Set it to the number of CPU cores on your machine |
| SATA_DISKS | Comma-separated list of sata disk paths |
| NVME_DISKS | Comma-separated list of nvme disk paths |
| PCH_INFO | PCH-related column-separated info in sensors output (see example in pve_temp_stats_to_influxdb2.sh script below)
| ACPITZ_INFO | PCH-related column-separated info in sensors output (see example in pve_temp_stats_to_influxdb2.sh script below)
| NVME_INFO | NVME disks comma-separated list of column-separated info in sensors output (see example in pve_temp_stats_to_influxdb2.sh script below)
| CORETEMP_NAME | CORETEMP value name in sensors output (see example in pve_temp_stats_to_influxdb2.sh script below)

#### Step 1: Create the environment file/s

`nano /home/scripts/pve_disks_stats_to_influxdb2.sh`

```bash
#!/bin/bash

export INFLUX_HOST="influx_IP_or_DNS"
export INFLUX_PORT="influx_PORT"
export INFLUX_ORGANIZATION="influx_organization"
export INFLUX_BUCKET="influx_bucket"
export INFLUX_TOKEN="influx_token"
export HOST_TAG="measurements_host_tag"
export SATA_DISKS="/dev/sda,/dev/sdb"
export NVME_DISKS="/dev/nvme0,/dev/nvme1"

# I've introduced the following variables since my NVME disk was bought from another person 
# and had a lot of read/written TBs.
# This variables hold the amount of read/written bytes the day I've received it, so I can know 
# the amount of data read/written by myself. 
# If your drive is new, set it to 0.
export DATA_UNITS_READ_BASE="0"
export DATA_UNITS_WRITTEN_BASE="0"

# Debian 11 without Python Virtual Environment
# python3 /home/scripts/pve_disks_stats_to_influxdb2.py $*

# Debian 12 with Python Virtual Environment in /path/to/venv
/path/to/venv/bin/python3 /home/scripts/pve_disks_stats_to_influxdb2.py $*
```

Edit the 'export' lines to you the variables that are applicable to your environment.  

`nano /home/scripts/pve_temp_stats_to_influxdb2.sh`

````bash
#!/bin/bash

export INFLUX_HOST="influx_IP_or_DNS"
export INFLUX_PORT="influx_PORT"
export INFLUX_ORGANIZATION="influx_organization"
export INFLUX_BUCKET="influx_bucket"
export INFLUX_TOKEN="influx_token"
export HOST_TAG="measurements_host_tag"
export CPU_CORES="6"

# Execute "sensors -j" and then use the information to set the following environment variables.
# In case some of them, like ACPITZ stuff, are not available, set them to ""
# For example if you want the PCH temperature to be stored in a pch field and you see the following
# within "sensors -j" output
#   "pch_cannonlake-virtual-0":{
#      "Adapter": "Virtual device",
#      "temp1":{
#         "temp1_input": 61.000
#      }
#   }
# Set PCH_INFO as the following, by looking at the chain of values that lead to the temperature of PCH
export PCH_INFO="pch:pch_cannonlake-virtual-0:temp1:temp1_input"

# The same as above
export ACPITZ_INFO="acpitz:acpitz-acpi-0:temp2:temp2_input"

# The same as above, but if you have multiple nvme entries you can define them as below, using "," to 
# separate the column-separated info of the different nvme disks
export NVME_INFO="nvme:nvme-pci-3a00:Composite:temp1_input,nvme2:nvme-pci-xxxx:Composite:temp1_input"

# This is simply the name of the coretemp-* value in "sensors -j" output
export CORETEMP_NAME="coretemp-isa-0000"

# Debian 11 without Python Virtual Environment
# python3 /home/scripts/pve_temp_stats_to_influxdb2.py $*

# Debian 12 with Python Virtual Environment in /path/to/venv
/path/to/venv/bin/python3 /home/scripts/pve_temp_stats_to_influxdb2.py $*
````

Edit the 'export' lines to you the variables that are applicable to your environment.  

#### Step 2: Create the script files

Taking from this repository, create the two python files, `pve_disks_stats_to_influxdb2.py` & `pve_temp_stats_to_influxdb2.py` on your system, on the paths used in your environment files/scripts.  

#### Step 3: Make the files executable

(from your scripts directory) -  
`chmod +x ./*.sh`  

#### Step 4: Dry Run

This is an important step, to allow you to DRY-RUN: see the what the scripts will upload to influxdb2.  

Both scripts (and also both wrappers) can be launched with *-t* flag, in order to print the collected data (*measurements*)
that will be uploaded to influxdb2.

##### Example Output - Disk Stats

- pve_disks_stats_to_influxdb2.sh

```bash
# /home/scripts/pve_disks_stats_to_influxdb2.sh -t

Measurements for host pve
[
    {
        "measurement": "disks",
        "tags": {
            "host": "pve",
            "devtype": "nvme",
            "devpath": "/dev/nvme0"
        },
        "fields": {
            "critical_warning": 0,
            "temperature": 35,
            "available_spare": 100,
            "available_spare_threshold": 5,
            "percentage_used": 100,
            "data_units_read_from_day1": 649318117888000,
            "data_units_read": 1022190592000,
            "data_units_written_from_day1": 600541940736000,
            "data_units_written": 401684992000,
            "host_read_commands": 2156546787,
            "host_write_commands": 1595165397,
            "controller_busy_time": 43706,
            "power_cycles": 141,
            "power_on_hours": 8347,
            "unsafe_shutdowns": 94,
            "media_errors": 0,
            "num_err_log_entries": 214
        }
    },
    {
        "measurement": "disks",
        "tags": {
            "host": "pve",
            "devtype": "sata",
            "devpath": "/dev/sda"
        },
        "fields": {
            "raw_read_error_rate": 0,
            "reallocate_nand_blk_cnt": 0,
            "power_on_hours": 249,
            "power_cycle_count": 18,
            "program_fail_count": 0,
            "erase_fail_count": 0,
            "ave_block-erase_count": 0,
            "unexpect_power_loss_ct": 1,
            "unused_reserve_nand_blk": 121,
            "sata_interfac_downshift": 0,
            "error_correction_count": 0,
            "reported_uncorrect": 0,
            "temperature_celsius": 26,
            "reallocated_event_count": 0,
            "current_pending_ecc_cnt": 0,
            "offline_uncorrectable": 0,
            "udma_crc_error_count": 0,
            "percent_lifetime_remain": 0,
            "write_error_rate": 0,
            "success_rain_recov_cnt": 0,
            "total_lbas_written": 461738011,
            "host_program_page_count": 3699503,
            "ftl_program_page_count": 461048
        }
    }
]
```

##### Example Output - System Temperatures

- pve_temp_stats_to_influxdb2.sh

```bash
# /home/scripts/pve_temp_stats_to_influxdb2.sh -t

Measurements for host pve
[
    {
        "measurement": "temp",
        "tags": {
            "host": "pve",
            "service": "lm_sensors"
        },
        "fields": {
            "cpu-package": 67,
            "core0": 50,
            "core1": 49,
            "core2": 51,
            "core3": 67,
            "core4": 48,
            "core5": 49,
            "pch": 42,
            "acpitz": 49,
            "nvme-pci": 34
        }
    }
]
```

#### Step 5: Scheduling data upload

I've put the two scripts in the following */etc/cron.d/influx_stats* crontab file in order to upload stats every minute:

```bash
# Upload stats to InfluxDB2

* * * * * root /home/scripts/pve_disks_stats_to_influxdb2.sh >/dev/null 2>&1

* * * * * root /home/scripts/pve_temp_stats_to_influxdb2.sh >/dev/null 2>&1
```

#### Step 6: Grafana Dashboard

Once you have your data on influxdb2, you can build your Grafana Dashboard and keep an eye on the health of your PVE box.  
You can also add alarms to warn you about high temperatures, low disk space available etc. Remember to configure your PVE to upload data to influxdb2 too, in order to have a complete set of data like cpu, memory and disk usage. It can be setup from GUI under Server View -> Datacenter -> Metric Server.  

![image](./grafana/Proxmox%20VE%20Grafana%20Dashboard%20Example.png)
(I've uploaded the [json source](./grafana/pve_grafana_dashboard.json) for the above dashboard in grafana folder)
