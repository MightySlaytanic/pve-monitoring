#!/root/scripts/venv/bin/python3

# Note about python shabang string above: if you're running on a Debian 11
# system use the standard "#!/usr/bin/python3" string while if you are on
# a Debian 12 system you need to create a virtual-env with influxdb_client
# and use the shabang string pointing to the python3 interpreter within
# the virtual-env, such as "#!/root/scripts/venv/bin/python3"
#
# For example, to create the virtual-env in /root/scripts/venv and install
# the required package do the following:
#
# python3 -m venv /root/scripts/venv
# . /root/scripts/venv/bin/activate
# pip3 install influxdb-client
# deactivate

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
CPU_CORES = int(getenv("CPU_CORES"))

CORE_OFFSET=2

CORETEMP_NAME = getenv("CORETEMP_NAME")
PCH_INFO = getenv("PCH_INFO").split(':')
ACPITZ_INFO = getenv("ACPITZ_INFO").split(':')

NVME_INFO = []
for nvme_item in getenv("NVME_INFO").split(','):
    NVME_INFO.append(nvme_item.split(':'))


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

    stats["cpu-package"] = int(data[CORETEMP_NAME]["Package id 0"]["temp1_input"])  

    for index in range(0,CPU_CORES):
        stats[f"core{index}"] = int(data[CORETEMP_NAME][f"Core {index}"][f"temp{index+CORE_OFFSET}_input"])

    if PCH_INFO[0]: 
        stats[PCH_INFO[0]] = int(data[PCH_INFO[1]][PCH_INFO[2]][PCH_INFO[3]])

    if ACPITZ_INFO[0]: 
        stats[ACPITZ_INFO[0]] = int(data[ACPITZ_INFO[1]][ACPITZ_INFO[2]][ACPITZ_INFO[3]])

    if NVME_INFO[0]:
        for nvme_item in NVME_INFO:
            if nvme_item[0]:
                stats[nvme_item[0]] = int(data[nvme_item[1]][nvme_item[2]][nvme_item[3]])

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
