#!/usr/bin/python3

import re
import sys
import json
import argparse
from datetime import datetime
from os import getenv
from subprocess import run,PIPE

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

INFLUX_HOST = getenv("INFLUX_HOST")
INFLUX_PORT = getenv("INFLUX_PORT")
INFLUX_TOKEN = getenv("INFLUX_TOKEN")
INFLUX_ORGANIZATION = getenv("INFLUX_ORGANIZATION")
INFLUX_BUCKET = getenv("INFLUX_BUCKET")
HOST = getenv("HOST_TAG")
DATA_UNITS_READ_BASE = int(getenv("DATA_UNITS_READ_BASE"))
DATA_UNITS_WRITTEN_BASE = int(getenv("DATA_UNITS_WRITTEN_BASE"))

DEVICES = {
    "nvme" : "/dev/nvme0",
    "sata" : "/dev/sda",
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(usage="PVE Disks Stats to influxdb2 uploader")

    parser.add_argument(
        "-t",
        "--test",
        help="Just print the results without uploading to influxdb2",
        action="store_true"
    )

    args = parser.parse_args()

    measurements = []
    for devtype, devpath in DEVICES.items():

        if devtype == "nvme":
            stats = {}
            output = run([f"/usr/sbin/nvme smart-log {devpath}"], stdout=PIPE, stderr=None, text=True, shell=True).stdout.split("\n")

            for line in output:
                if len(line) > 0:
                    match_found = re.match(r".*Smart Log.*|^[^_]+$", line)
                    temperature_found = re.match(r".*temperature.*", line)

                    if not match_found or temperature_found:
                        key, value = line.strip().split(":")
                        key = key.strip()
                        value = value.strip().replace(",","")
                        value = value.strip().replace("%","")

                        if temperature_found:
                            value, _ = value.split(" ") 
                        
                        if value.isnumeric():
                            value = int(value)

                        match_found = re.match(r"data_units_read|data_units_written",key)

                        if match_found:
                            # data_units_read/written is in thousands of 512 bytes blocks
                            value = value * 512000

                            if key == "data_units_read":
                                stats["data_units_read_from_day1"] = value
                                value = value - DATA_UNITS_READ_BASE

                            if key == "data_units_written":
                                stats["data_units_written_from_day1"] = value
                                value = value - DATA_UNITS_WRITTEN_BASE
                        
                        stats[key.lower()] = value

            measurements.append({
                "measurement": "disks",
                "tags": {"host": HOST, "devtype": devtype, "devpath": devpath},
                "fields": stats
            })

        elif devtype == "sata":
            stats = {}
            output = run([f"/usr/sbin/smartctl -A {devpath}"], stdout=PIPE, stderr=None, text=True, shell=True).stdout.split("\n")

            for line in output:
                if len(line) > 0:
                    # Line sample:
                    #   1 Raw_Read_Error_Rate     0x002f   100   100   000    Pre-fail  Always       -       0
                    match_found = re.match(r"^\s*[0-9]+\s+([^\s]+).*\s-\s+([^\s]+).*", line)

                    if match_found:
                        stats[match_found.group(1).lower()] = int(match_found.group(2))

            measurements.append({
                "measurement": "disks",
                "tags": {"host": HOST, "devtype": devtype, "devpath": devpath},
                "fields": stats
            })

    if args.test:
        print(f"\nMeasurements for host {HOST}")
        print(json.dumps(measurements, indent=4))
    else:
        try:
            client = InfluxDBClient(url=f"http://{INFLUX_HOST}:{INFLUX_PORT}", token=INFLUX_TOKEN, org=INFLUX_ORGANIZATION, timeout=30000)
            write_api = client.write_api(write_options=SYNCHRONOUS)

            write_api.write(
                INFLUX_BUCKET,
                INFLUX_ORGANIZATION,
                measurements
            )

        except TimeoutError as e:
            failure = True
            print(e,file=sys.stderr)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] TimeoutError: Could not upload data to {INFLUX_HOST}:{INFLUX_PORT} for host {HOST}",file=sys.stderr)
            exit(-1)
        except InfluxDBError as e:
            failure = True
            print(e,file=sys.stderr)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] InfluxDBError: Could not upload data to {INFLUX_HOST}:{INFLUX_PORT} for host {HOST}",file=sys.stderr)
            exit(-1)
        except Exception as e:
            failure = True
            print(e, file=sys.stderr)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Connection Error: Could not upload data to {INFLUX_HOST}:{INFLUX_PORT} for host {HOST}",file=sys.stderr)
            exit(-1)

        client.close()
