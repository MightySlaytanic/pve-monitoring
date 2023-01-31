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

CORE_OFFSET=2

if __name__ == '__main__':
    parser = argparse.ArgumentParser(usage="PVE Sensors Stats to influxdb2 uploader")

    parser.add_argument(
        "-t",
        "--test",
        help="Just print the results without uploading to influxdb2",
        action="store_true"
    )

    args = parser.parse_args()

    measurements = []
    stats = {}

    data = json.loads(run(["/usr/bin/sensors -j"], stdout=PIPE, stderr=None, text=True, shell=True).stdout)

    stats["cpu-package"] = int(data["coretemp-isa-0000"]["Package id 0"]["temp1_input"])  

    for index in range(0,6):
        stats[f"core{index}"] = int(data["coretemp-isa-0000"][f"Core {index}"][f"temp{index+CORE_OFFSET}_input"])

    stats["pch"] = int(data["pch_cannonlake-virtual-0"]["temp1"]["temp1_input"])
    stats["acpitz"] = int(data["acpitz-acpi-0"]["temp2"]["temp2_input"])
    stats["nvme-pci"] = int(data["nvme-pci-3a00"]["Composite"]["temp1_input"])

    measurements.append({
        "measurement": "temp",
        "tags": {"host": HOST, "service": "lm_sensors"},
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
