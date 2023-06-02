#!/usr/bin/env python3

import argparse
import json
import sys

def sqlog2qlog(input, output):
    with open(input) as file:
        sqlog_data = [json.loads(line) for line in file.readlines()]

    qlog = sqlog_data.pop(0)
    qlog["qlog_format"] = "JSON"
    qlog["trace"]["events"] = sqlog_data
    with open(output, "w") as outfile:
        json.dump(qlog, outfile, indent=4)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert sqlog (NDJSON) files to qlog (JSON) format")
    parser.add_argument("input", help="Input sqlog file path")
    parser.add_argument("output", help="Output qlog file path")
    args = parser.parse_args()

    sqlog2qlog(args.input, args.output)
    