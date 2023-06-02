# %%
import json
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import folium
import ipinfo
import numpy as np
from datetime import datetime
from zipfile import ZipFile
import cbor2
from tqdm import tqdm
import shutil
from quic_info import Quic_info

folder = os.path.join("labo_tests", "nesquic_wsp_2", "logs")


def get_events(qlogs):
    return qlogs['traces'][0]['events']


def get_rtts(qlogs):
    timestamps = []
    rtts = []
    for event in get_events(qlogs):
        if "latest_rtt" in event[3]:
            timestamps.append(event[0]/1000)
            rtts.append(event[3]["latest_rtt"]/1000)
    return timestamps, rtts

out = []

for test in tqdm(os.listdir(folder)):
    test_folder = os.path.join(folder, test)
    results = os.listdir(test_folder)
    latest_zip = max([(datetime.strptime(e.rstrip(".zip"),
                     "%a_%b_%d_%H:%M:%S_%Y"), e) for e in results])[1]
    data = None
    with ZipFile(os.path.join(test_folder, latest_zip)) as zo:
        tmp_dir = "nesquic_tmp"
        zo.extractall("nesquic_tmp")
        with open(os.path.join(tmp_dir, "output.json")) as output:
            data = json.load(output)
            for method in data:
                for way in method['ways']:
                    if way["way"] == "upload":
                        for param in way["params"]:
                            c_dir = os.path.join(tmp_dir, method['method'], "upload", str(param['param']))
                            test_name = f"{method['method']}_{way['way']}_{param['param'].split(' ')[0]}"
                            to_take = "server" if way["way"] == "download" else "client"
                            compressed_qlog = [f for f in os.listdir(c_dir) if f.endswith("cbor") and to_take in f][0]
                            qi = None
                            with open(os.path.join(c_dir, compressed_qlog), 'rb') as cq_f:
                                qlog = json.loads(cbor2.loads(cq_f.read()))
                                qi = Quic_info(host_type="local")
                                qi.set_qlog_content(qlog)
                            curr = {
                                "test_name" : test_name,
                                "fixed_bw": int(test.split("_")[1].rstrip("mbit")),
                                "fixed_latency": int(test.split("_")[2].rstrip("ms"))
                            }
                            curr.update(qi.to_json())
                            out.append(curr)
            shutil.rmtree(tmp_dir)
            
lat_df = pd.DataFrame(out)
lat_df.to_csv("data/nesquic_quic_info.csv")


