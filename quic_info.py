import json
from numpy import mean, var

# print("WARNING: this version works only for draft-00 version of qlog")

class Quic_info:
    def __init__(self, qlog_file=None, host_type="local"):        

        self.qlogs = None
        if qlog_file != None: 
            with open(qlog_file) as f:
                self.qlogs = json.load(f)

            # Time units (us / ms / else)
            self.time_units = self.qlogs["traces"][0]["configuration"]["time_units"]

            # Since the timestamp are relative we need the reference
            self.reference_timestamp = int(self.qlogs["traces"][0]["common_fields"]["reference_time"])

        self.host_type = host_type
    def set_qlog_content(self, content):
        self.qlogs = content
        # Time units (us / ms / else)
        self.time_units = self.qlogs["traces"][0]["configuration"]["time_units"]

        # Since the timestamp are relative we need the reference
        self.reference_timestamp = int(
            self.qlogs["traces"][0]["common_fields"]["reference_time"])
    def _get_events(self):
        return self.qlogs["traces"][0]["events"]

    def get_RTO(self):
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "parameters_set":
                if data["owner"] == self.host_type:
                    if "idle_timeout" in data:
                        return data["idle_timeout"]

    def get_ATO(self):
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "parameters_set":
                if data["owner"] == self.host_type:
                    if "max_ack_delay" in data:
                        # TODO: CHECK min/max_ack_delay
                        return data["max_ack_delay"]

    def get_snd_MSS(self):
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "parameters_set":
                if data["owner"] == "local":
                    if "initial_max_data" in data:
                        return data["initial_max_data"]

    def get_rcv_MSS(self):
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "parameters_set":
                if data["owner"] == "remote":
                    if "initial_max_data" in data:
                        return data["initial_max_data"]

    def get_lost(self):
        lost = 0
        for timestamp, category, event, data in self._get_events():
            if category == "recovery" and event == "packet_lost":
                lost += 1
        return lost

    # def get_spurious(self):
    #     for timestamp, category, event, data in reversed(self._get_events()):
    #         if category == "info" and event == "message":
    #             if "spurious" in data["message"]:
    #                 return data["message"]

    def get_retrans(self):
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "info" and event == "message":
                if "retrans" in data["message"]:
                    return data["message"]

    def get_last_data_sent(self):
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "transport" and event == "packet_sent":
                for frame in data["frames"]:
                    if frame["frame_type"] == "stream":
                        last_data_sent = self.reference_timestamp + timestamp
                        return last_data_sent

    def get_last_ack_sent(self):
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "transport" and event == "packet_sent":
                for frame in data["frames"]:
                    if frame["frame_type"] == "ack":
                        last_data_sent = self.reference_timestamp + timestamp
                        return last_data_sent

    def get_last_data_recv(self):
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "transport" and event == "packet_received":
                for frame in data["frames"]:
                    if frame["frame_type"] == "stream":
                        last_data_recv = self.reference_timestamp + timestamp
                        return last_data_recv

    def get_last_ack_recv(self):
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "transport" and event == "packet_received":
                for frame in data["frames"]:
                    if frame["frame_type"] == "ack":
                        last_ack_recv = self.reference_timestamp + timestamp
                        return last_ack_recv

    def _get_rtts(self):
        rtts = []
        for timestamp, category, event, data in self._get_events():
            if category == "recovery" and event == "metrics_updated":
                if "latest_rtt" in data:
                    rtts.append(data["latest_rtt"])
        return rtts

    def get_minrtt(self):
        min(self._get_rtts())

    def get_meanrtt(self):
        return mean(self._get_rtts())

    def get_varrtt(self):
        return var(self._get_rtts())

    def get_maxrtt(self):
        return max(self._get_rtts())

    def get_pacing_rate(self):
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "recovery" and event == "metrics_updated":
                if "pacing_rate" in data:
                    return data["pacing_rate"]

    def get_max_pacing_rate(self):
        max_pacing_rate = 0
        for timestamp, category, event, data in self._get_events():
            if category == "recovery" and event == "metrics_updated":
                if "pacing_rate" in data:
                    if data["pacing_rate"] > max_pacing_rate:
                        max_pacing_rate = data["pacing_rate"]
        return max_pacing_rate

    def get_delivery_rate(self):
        return self.get_bytes_sent()/self.get_connexion_duration()

    def get_bytes_sent(self):
        bytes_sent = 0
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "datagram_sent":
                bytes_sent += data["byte_length"]
        return bytes_sent

    def get_bytes_received(self):
        bytes_reveived = 0
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "datagram_received":
                bytes_reveived += data["byte_length"]
        return bytes_reveived

    def get_frames_sent(self):
        frames_sent = 0
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "transport" and event == "packet_sent":
                for frame in data["frames"]:
                    if frame["frame_type"] == "stream":
                        frames_sent += 1
        return frames_sent

    def get_frames_received(self):
        frames_received = 0
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "transport" and event == "packet_reveived":
                for frame in data["frames"]:
                    if frame["frame_type"] == "stream":
                        frames_received += 1
        return frames_received

    def get_cwnd(self):
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "recovery" and event == "metrics_updated":
                if "cwnd" in data:
                    return data["cwnd"]

    def get_maxcwnd(self):
        max_cwnd = 0
        for timestamp, category, event, data in self._get_events():
            if category == "recovery" and event == "metrics_updated":
                if "cwnd" in data:
                    if data["cwnd"] > max_cwnd:
                        max_cwnd = data["cwnd"]
        return max_cwnd

    def get_datagram_sent(self):
        datagram_sent = 0
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "datagram_sent":
                datagram_sent += 1
        return datagram_sent

    def get_data_datagram_sent(self):
        data_datagram_sent = 0
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "datagram_sent" and data["byte_length"] > 0:
                data_datagram_sent += 1
        return data_datagram_sent

    def get_data_sent(self):
        # TODO : not good for server side ?
        sent = {} # pkt_numbet -> data_carried
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "packet_sent":
                data_carried = 0
                for frame in data["frames"]:
                    if frame["frame_type"] == "stream":
                        data_carried += frame["length"]
                sent[data["header"]["packet_number"]] = data_carried
            if category == "recovery" and event == "packet_lost":
                del sent[data["header"]["packet_number"]]
        data_sent = sum(sent.values())
        return data_sent

    def get_datagram_received(self):
        datagram_received = 0
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "datagram_received":
                datagram_received += 1
        return datagram_received

    def get_data_datagram_received(self):
        data_datagram_received = 0
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "datagram_received" and data["byte_length"] > 0:
                data_datagram_received += 1
        return data_datagram_received
    
    def get_data_received(self):
        data_received = 0
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "packet_received":
                for frame in data["frames"]:
                    if frame["frame_type"] == "stream":
                        data_received += frame["length"]
        return data_received

    def get_next_send_packet_number(self):
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "transport" and event == "packet_sent":
                return data["header"]["packet_number"] + 1

    def get_next_receive_packet_number(self):
        for timestamp, category, event, data in reversed(self._get_events()):
            if category == "transport" and event == "packet_received":
                return data["header"]["packet_number"] + 1

    def get_connexion_duration(self):
        return self._get_events()[-1][0]

    def get_upload_estimated_overhead(self):
        # udp header = 8 bytes
        udp_headers = self.get_datagram_sent() * 8
        # total bytes sent
        total_bytes_sent = udp_headers + self.get_bytes_sent()

        return 1 - (self.get_data_sent() / total_bytes_sent)

    def get_spurious(self):
        acked = set()
        losts = set()
        for timestamp, category, event, data in self._get_events():
            if category == "transport" and event == "packet_received":
                for frame in data["frames"]:
                    if frame["frame_type"] == "ack":
                        for start, end in frame["acked_ranges"]:
                            acked |= set(range(start, end+1))
            if category == "recovery" and event == "packet_lost":
                losts.add(data["packet_number"])
        return len(acked.intersection(losts))
                        

    def to_json(self):
        methodes = [methode for methode in dir(self) if methode.startswith('get_')]
        return {meth[4:]:getattr(self, meth)() for meth in methodes}
