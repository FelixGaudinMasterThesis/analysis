import os
from sqlog2qlog import sqlog2qlog
from tqdm import tqdm

folder = "memoire-vps-output2"

for subfolder in tqdm([f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]):
    if os.path.exists(os.path.join(folder, subfolder, "proxy.log")):
        subfolder = os.path.join(folder, subfolder)
        losses_for_test = []
        for subsubfolder in ["IP", "Ping", "RpmDownload", "RpmUpload"]:
            subsubfolder = os.path.join(subfolder, subsubfolder)
            for sqlog_file in os.listdir(subsubfolder):
                if sqlog_file.endswith(".sqlog"):
                    sqlog2qlog(
                        os.path.join(subsubfolder, sqlog_file), 
                        os.path.join(subsubfolder, sqlog_file.replace("sqlog", "qlog"))
                        )
                    os.remove(os.path.join(subsubfolder, sqlog_file))
