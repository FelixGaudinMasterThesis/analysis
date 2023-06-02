import json
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import folium
import ipinfo
import numpy as np
from tqdm import tqdm
from quic_info2 import Quic_info, is_packet_lost


def get_delta_df(folders):
    output = []
    for folder in folders:
        for subfolder in tqdm([f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f)) and f.startswith("rpm_")]):
            logfile = os.path.join(folder, subfolder, "test.json")
            if os.path.exists(logfile):
                try:
                    with open(logfile) as file:
                        data = json.load(file)
                        ip, isp_dist = data["clientIp"].split(" - ")
                        isp, dist = isp_dist.split("(")
                        dist = int(dist.rstrip("km)"))
                        output.append({
                            "ip": ip,
                            "isp": isp,
                            "dist": dist,
                            "dl_bw": float(data["dlStatus"]),
                            "ul_bw": float(data["ulStatus"]),
                            "dl_rpm": int(data["rpmDlStatus"]),
                            "ul_rpm": int(data["rpmUlStatus"]),
                            "ping": float(data["pingStatus"]),
                            "ping_as_rpm": int(60_000 / float(data["pingStatus"])),
                            "jitter": float(data["jitterStatus"])
                        })
                except:
                    # print(subfolder)
                    pass
    return pd.DataFrame(output)

import re

def get_browser(user_agent):
    if isinstance(user_agent, list): user_agent = user_agent[0]
    if "Firefox" in user_agent:
        # Extract Firefox version number using regex
        match = re.search(r"Firefox/(\d+\.\d+)", user_agent)
        if match:
            return "Firefox " + match.group(1)
    elif "Chrome" in user_agent:
        # Extract Chrome version number using regex
        match = re.search(r"Chrome/(\d+\.\d+)", user_agent)
        if match:
            # Check if it's a mobile version of Chrome
            if "Mobile" in user_agent:
                return "Chrome Mobile " + match.group(1)
            else:
                return "Chrome " + match.group(1)
    elif "Safari" in user_agent:
        # Extract Safari version number using regex
        match = re.search(r"Version/(\d+\.\d+)", user_agent)
        if match:
            # Check if it's a mobile version of Safari
            if "Mobile" in user_agent:
                return "Safari Mobile " + match.group(1)
            else:
                return "Safari " + match.group(1)
    elif "Edge" in user_agent:
        # Extract Edge version number using regex
        match = re.search(r"Edge/(\d+\.\d+)", user_agent)
        if match:
            # Check if it's a mobile version of Edge
            if "Mobile" in user_agent:
                return "Edge Mobile " + match.group(1)
            else:
                return "Edge " + match.group(1)
    elif "MSIE" in user_agent:
        # Extract IE version number using regex
        match = re.search(r"MSIE (\d+\.\d+)", user_agent)
        if match:
            return "Internet Explorer " + match.group(1)
    print(user_agent)
    return "Unknown browser"

def parse(filename):
    output = []
    with open(filename, "r") as file:
        for line in file.readlines():
            try:
                output.append(json.loads(line))
            except:
                pass
    return output

def get_browsers(folders):
    output = []
    for folder in folders:
        for subfolder in tqdm([f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f)) and f.startswith("rpm_")]):
            logfile = os.path.join(folder, subfolder, "proxy.log")
            if os.path.exists(logfile):
                try:
                    proxy_logs = parse(logfile)
                    if len(proxy_logs) > 0:
                        n_req = h3 = 0
                        for access in proxy_logs:
                            if access["request"]["method"] == "GET" or access["request"]["method"] == "POST":
                                if access["request"]["proto"] == "HTTP/3.0":
                                    h3 += 1
                                n_req += 1
                        quic_usage = 100*h3/n_req
                        user_agent = proxy_logs[0]["request"]["headers"]["User-Agent"]
                        browser = get_browser(user_agent)
                        output.append({
                            "browser" : browser, 
                            "quic_usage": quic_usage
                        })

                except Exception as e:
                    # print(e)
                    pass
    return pd.DataFrame(output)


def get_bursts(file):
    qi = Quic_info(file)
    timestamps = []
    for event in qi._get_events():
        if is_packet_lost(event):
            timestamps.append(event["time"])

    srtt = qi.get_srtt()
    var = qi.get_varrtt()
    threshold = srtt + var
    burst_loss = []

    current_burst = 0
    for i in range(len(timestamps) - 1):
        delta_time = timestamps[i+1] - timestamps[i]
        if 1000*delta_time <= threshold:  # in the same burst
            current_burst += 1
        else:
            if current_burst != 0:
                burst_loss.append(current_burst)
            current_burst = 1
    burst_loss.append(current_burst)
    return burst_loss

def get_bursts_df(folders):
    bursts = []
    for folder in folders:
        for subfolder in tqdm([f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]):
            if os.path.exists(os.path.join(folder, subfolder, "proxy.log")):
                subfolder = os.path.join(folder, subfolder)

                logfile = os.path.join(subfolder, "test.json")
                if os.path.exists(logfile):
                    try:
                        with open(logfile) as file:
                            data = json.load(file)
                            ip, isp_dist = data["clientIp"].split(" - ")
                            isp, dist = isp_dist.split("(")
                            dist = int(dist.rstrip("km)"))
                            current_bursts = []
                            # legacy
                            for subsubfolder in ["IP", "Ping", "RpmDownload", "RpmUpload"]:
                                subsubfolder = os.path.join(subfolder, subsubfolder)
                                for sqlog_file in os.listdir(subsubfolder):
                                    b = get_bursts(os.path.join(subsubfolder, sqlog_file))
                                    if len(b) > 1:
                                        current_bursts.extend(b)
                            bursts.append({
                                "ip" : ip,
                                "isp" : isp,
                                "dist" : dist,
                                "burst" : current_bursts
                            })
                    except:
                        pass

    return pd.DataFrame(bursts)


def get_spurious_informations(file):
    qi = Quic_info(file)
    return {
        "spurious" : qi.get_spurious(), 
        "loss" : qi.get_lost(),
        "packet_sent" : qi.get_packet_sent()
        }

def get_spurious_df(folders):
    spurious = []
    for folder in folders:
        for subfolder in tqdm([f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]):
            if os.path.exists(os.path.join(folder, subfolder, "proxy.log")):
                subfolder = os.path.join(folder, subfolder)

                logfile = os.path.join(subfolder, "test.json")
                if os.path.exists(logfile):
                    try:
                        with open(logfile) as file:
                            data = json.load(file)
                            ip, isp_dist = data["clientIp"].split(" - ")
                            isp, dist = isp_dist.split("(")
                            dist = int(dist.rstrip("km)"))
                            ping_as_rpm = int(60_000 / float(data["pingStatus"]))

                            current_spurious = 0
                            current_losses = 0
                            current_pkt_sent = 0
                            # legacy
                            for subsubfolder in ["IP", "Ping", "RpmDownload", "RpmUpload"]:
                                subsubfolder = os.path.join(subfolder, subsubfolder)
                                for sqlog_file in os.listdir(subsubfolder):
                                    info = get_spurious_informations(
                                        os.path.join(subsubfolder, sqlog_file))
                                    current_spurious += info["spurious"]
                                    current_losses += info["loss"]
                                    current_pkt_sent += info["packet_sent"]
                            spurious.append({
                                "ip": ip,
                                "isp": isp,
                                "dist": dist,
                                "spurious": current_spurious,
                                "loss" : current_losses,
                                "loss_rate" : 100*current_losses/current_pkt_sent,
                                "ping_as_rpm": ping_as_rpm,
                                "ratio_dl_rpm": ping_as_rpm / int(data["rpmDlStatus"]),
                                "ratio_ul_rpm": ping_as_rpm / int(data["rpmUlStatus"])
                            })
                    except:
                        pass
    return pd.DataFrame(spurious)


def get_quic_infos(folders):
    quic_infos = []
    for folder in folders:
        for subfolder in tqdm([f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]):
            if os.path.exists(os.path.join(folder, subfolder, "proxy.log")):
                subfolder = os.path.join(folder, subfolder)

                logfile = os.path.join(subfolder, "test.json")
                if os.path.exists(logfile):
                    try:
                        with open(logfile) as file:
                            data = json.load(file)
                            ip, isp_dist = data["clientIp"].split(" - ")
                            isp, dist = isp_dist.split("(")
                            dist = int(dist.rstrip("km)"))
                            ping_as_rpm = int(60_000 / float(data["pingStatus"]))

                            current_spurious = 0
                            current_losses = 0
                            current_pkt_sent = 0
                            # legacy
                            for subsubfolder in ["IP", "Ping", "RpmDownload", "RpmUpload"]:
                                subsubfolder = os.path.join(subfolder, subsubfolder)
                                for sqlog_file in os.listdir(subsubfolder):
                                    qi = Quic_info(os.path.join(
                                        subsubfolder, sqlog_file))
                                    info = {
                                        "ip": ip,
                                        "isp": isp,
                                        "dist": dist,
                                        "ping_as_rpm": ping_as_rpm,
                                        "ratio_dl_rpm": ping_as_rpm / int(data["rpmDlStatus"]),
                                        "ratio_ul_rpm": ping_as_rpm / int(data["rpmUlStatus"])
                                    }
                                    info.update(qi.to_json())
                                    quic_infos.append(info)
                    except:
                        pass
    return pd.DataFrame(quic_infos)

# print("delta df:")
# delta_df = get_delta_df(["memoire-vps-output", "memoire-vps-output2"])
# delta_df.to_csv(os.path.join("data", "delta.csv"), index=False)

print("browsers:")
browsers_df = get_browsers(["memoire-vps-output", "memoire-vps-output2"])
browsers_df.to_csv(os.path.join("data", "browsers.csv"), index=False)

# print("bursts:")
# bursts_df = get_bursts_df(["memoire-vps-output2"])
# bursts_df.to_csv(os.path.join("data", "bursts.csv"), index=False)

# print("spurious")
# spurious_df = get_spurious_df(["memoire-vps-output2"])
# spurious_df.to_csv(os.path.join("data", "spurious.csv"), index=False)

# print("quic_info")
# quic_info_df = get_quic_infos(["memoire-vps-output2"])
# quic_info_df.to_csv(os.path.join("data", "quic_info.csv"), index=False)
