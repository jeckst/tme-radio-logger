import csv
import datetime as dt
import logging
import os
import re
import xml.dom.minidom

import requests
import yaml

logger = logging.getLogger(__name__)
log_level = os.getenv("LOG_LEVEL", logging.INFO)
logger.setLevel(log_level)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(log_level)
logger.addHandler(stream_handler)

BASE_COLUMNS = ["timestamp"]

config = {
    "OUTPUT_FILE_DIR": "/home/jeckst/code/templog/",
    "OUTPUT_FILE_PREFIX": "out_",
    "ENDPOINT": "http://192.168.2.254/fresh.xml",
    "CSV_PARAMS": {
        "delimiter": ";",
        "quotechar": '"',
        "quoting": csv.QUOTE_MINIMAL,
    },
}


class SensorData:
    OK_CONST = "0"

    def __init__(self, endpoint):
        try:
            ans = requests.get(endpoint)
            ans.raise_for_status()
        except Exception as e:
            logger.exception("Could not connect to TME; %s", e)
            raise
        try:
            document = xml.dom.minidom.parseString(ans.text)
            self.data = [
                {
                    "name": elem.getAttribute("name"),
                    "state": elem.getAttribute("s1"),
                    "value": float(elem.getAttribute("v1")) / 10.0,
                    "timestamp": int(elem.getAttribute("ack_cas")),
                }
                for elem in document.getElementsByTagName("sns")
            ]
            self.names = [s["name"] for s in self.data]
        except Exception as e:
            logger.exception("Could not parse response; %s", e)
            raise

    def get_data_dict(self):
        return {
            s["name"]: s["value"]
            for s in self.data
            if s["state"] == self.OK_CONST
        }


def output_file_pattern():
    return rf"{config['OUTPUT_FILE_PREFIX']}{dt.date.today():%Y-%m}_(\d+).csv"


def output_file_path(index):
    return os.path.join(
        config["OUTPUT_FILE_DIR"],
        f"{config['OUTPUT_FILE_PREFIX']}{dt.date.today():%Y-%m}_{index}.csv",
    )


def get_output_file_index(file_name):
    return int(re.match(output_file_pattern(), file_name).group(1))


def find_current_output_file():
    output_files = sorted(
        (
            f
            for f in os.listdir(config["OUTPUT_FILE_DIR"])
            if re.match(output_file_pattern(), f)
        ),
        key=lambda item: get_output_file_index(item),
    )
    if output_files:
        return output_files[-1]


def get_current_ouput_columns(file_path):
    with open(file_path, "r") as f:
        reader = csv.DictReader(f, **config["CSV_PARAMS"])
        return reader.fieldnames


def write_data_row(writer, sensor_data):
    row = dict(
        timestamp=dt.datetime.now().isoformat(timespec="seconds"),
        **sensor_data.get_data_dict(),
    )
    writer.writerow(row)


def new_file_write_values(file_index, sensor_data):
    columns = BASE_COLUMNS + sensor_data.names
    file_path = output_file_path(file_index)
    logger.info("Setting up new file at %s", file_path)
    with open(file_path, "w") as f:
        writer = csv.DictWriter(f, fieldnames=columns, **config["CSV_PARAMS"])
        writer.writeheader()
        write_data_row(writer, sensor_data)


def existing_file_write_values(file_path, columns, sensor_data):
    logger.info("Writing to existing file at %s", file_path)
    with open(file_path, "a") as f:
        writer = csv.DictWriter(f, fieldnames=columns, **config["CSV_PARAMS"])
        write_data_row(writer, sensor_data)


if __name__ == "__main__":
    with open(os.getenv("CONFIG_FILE", "config.yaml"), "r") as f:
        config = yaml.safe_load(f)

    sensor_data = SensorData(config["ENDPOINT"])
    all_sensor_columns = BASE_COLUMNS + sensor_data.names
    current_file = find_current_output_file()
    if current_file:
        current_file_index = get_output_file_index(current_file)
        current_file_columns = get_current_ouput_columns(current_file)
        if set(current_file_columns) == set(all_sensor_columns):
            existing_file_write_values(
                current_file, current_file_columns, sensor_data
            )
        else:
            new_file_write_values(
                file_index=current_file_index + 1, sensor_data=sensor_data
            )
    else:
        new_file_write_values(file_index=1, sensor_data=sensor_data)
