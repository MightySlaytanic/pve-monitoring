# pve-monitoring
Proxmox VE temperature and disk-health stats upload to influxdb2

**DISCLAIMER**: this tool has been developed to monitor my own Intel NUC with a SATA and an NVME disk. You can freely use and modify it to your needs, but I hold no responsibility if not used properly. 

## pve_disks_stats_to_influxdb2.py

This script retrieves data from sata disks using smartctl and from nvme disks via nvmcli tools.
You can modify the DEVICES dictionary by changing the path of the sata or nvme disk or by removing one of the two entries.
At present time only one disk per type is supported (you can not add a second SATA or NVME disk without changing the code.

## pve_temp_stats_to_influxdb2.py

This script uses the lm_sensors command to retrieve temperature info from the device. It has ben tailored for the output of the command executed on an Intel NUC i7 10th Gen device, so it may not work for your device without proper changes to the code

## USAGE

Both tools requires you to set some environment variables 

```bash
INFLUX_HOST = getenv("INFLUX_HOST")
INFLUX_PORT = getenv("INFLUX_PORT")
INFLUX_TOKEN = getenv("INFLUX_TOKEN")
INFLUX_ORGANIZATION = getenv("INFLUX_ORGANIZATION")
INFLUX_BUCKET = getenv("INFLUX_BUCKET")
HOST = getenv("HOST_TAG")
```

You can directly edit the python script or you can build a bash wrapper like the following 
(replace path-to-the-script with the full path and set the environment variables to fit your influxdb2 settings):

- pve_disks_stats_to_influxdb2.sh

```bash
#!/bin/bash

export INFLUX_HOST="influx_IP_or_DNS"
export INFLUX_PORT="influx_PORT"
export INFLUX_ORGANIZATION="influx_organization"
export INFLUX_BUCKET="influx_bucket"
export INFLUX_TOKEN="influx_token"
export HOST_TAG="measurements_host_tag"

# I've introduced the following variables since my NVME disk was bought from another person 
# and had a lot of read/written TBs.
# This variables hold the amount of read/written bytes the day I've received it, so I can know 
# the amount of data read/written by myself. 
# If your drive is new, set it to 0.
export DATA_UNITS_READ_BASE="648_295_927_296_000"
export DATA_UNITS_WRITTEN_BASE="600_140_255_744_000"

python3 /path-to-the-script/pve_disks_stats_to_influxdb2.py $*
```

- pve_temp_stats_to_influxdb2.sh

```bash
#!/bin/bash

export INFLUX_HOST="influx_IP_or_DNS"
export INFLUX_PORT="influx_PORT"
export INFLUX_ORGANIZATION="influx_organization"
export INFLUX_BUCKET="influx_bucket"
export INFLUX_TOKEN="influx_token"
export HOST_TAG="measurements_host_tag"

python3 /path-to-the-script/pve_temp_stats_to_influxdb2.py $*
```

## DRY-RUN: see the what the scripts will upload to influxdb2

Both scripts (and also both wrappers) can be launched with *-t* flag, in order to print the collected data (*measurements*) 
that will be uploaded to influxdb2.

- pve_disks_stats_to_influxdb2.sh

```bash
# /root/scripts/pve_disks_stats_to_influxdb2.sh -t

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

- pve_temp_stats_to_influxdb2.sh

```bash
# /root/scripts/pve_temp_stats_to_influxdb2.sh -t

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

## Grafana Dashboard Example

Once you have your data on influxdb2, you can build your Grafana Dashboard and keep an eye on the health of your PVE box. 
You can also add alarms to warn you about high temperatures, low disk space available etc. Remember to configure your
PVE to upload data to influxdb2 too, in order to have a complete set of data like cpu, memory and disk usage. It can
be setup from GUI under Server View -> Datacenter -> Metric Server.

![image](./Proxmox%20VE%20Grafana%20Dashboard%20Example.png)
