import re
import sys
import os
import json







def get_lshw_network_dict( phdl ):
    lshw_dict = {}
    out_dict = phdl.exec('sudo lshw -class network -businfo')
    for node in out_dict.keys():
        lshw_dict[node] = {}
        for line in out_dict[node].split("\n"):
            print(line)
            if re.search( 'pci\@([0-9a-f\:\.]+)\s+([a-z0-9\-\.]+)\s+network\s+([a-z0-9\s\[\]\/\-\_]+)', line, re.I ):
                match = re.search( 'pci\@([0-9a-f\:\.]+)\s+([a-z0-9\-\.]+)\s+network\s+([a-z0-9\s\[\]\/\-\_]+)', line, re.I )
                pci_bus = match.group(1)
                dev_name = match.group(2)
                dev_descr = match.group(3)
                lshw_dict[node][dev_name] = {}
                lshw_dict[node][dev_name]['pci_bus'] = pci_bus
                lshw_dict[node][dev_name]['description'] = dev_descr
            elif re.search( 'pci\@([0-9a-f\:\.]+)\s+network\s+([a-z0-9\s\[\]\/\-\_]+)', line, re.I ):
                match = re.search( 'pci\@([0-9a-f\:\.]+)\s+network\s+([a-z0-9\s\[\]\/\-\_]+)', line, re.I )
                pci_bus = match.group(1)
                dev_name = 'virtio'
                dev_descr = match.group(2)
                lshw_dict[node][dev_name] = {}
                lshw_dict[node][dev_name]['pci_bus'] = pci_bus
                lshw_dict[node][dev_name]['description'] = dev_descr
                
    return lshw_dict
              
     

def get_ip_addr_dict( phdl ):
    ip_dict = {}
    out_dict = phdl.exec('sudo ip addr show | grep -A 5 mtu --color=never')
    int_nam = None
    for node in out_dict.keys():
        ip_dict[node] = {}
        for line in out_dict[node].split("\n"):
            if re.search( '[0-9]+\:\s+([0-9a-z\.\_\-\/]+):\s+([\<\>\,A-Z0-9]+)', line ):
                match = re.search( '[0-9]+\:\s+([0-9a-z\.\_\-\/]+):\s+([\<\>\,A-Z0-9]+)', line )
                int_nam = match.group(1)
                ip_dict[node][int_nam] = {}
                ip_dict[node][int_nam]['ipv4_addr_list'] = []
                ip_dict[node][int_nam]['ipv6_addr_list'] = []
                 
                ip_dict[node][int_nam]['flags'] = match.group(2)
            if re.search( 'mtu ([0-9]+)', line ):
                match = re.search( 'mtu ([0-9]+)', line )
                ip_dict[node][int_nam]['mtu'] = match.group(1)
            if re.search( 'state ([A-Z]+)', line ):
                match = re.search( 'state ([A-Z]+)', line )
                ip_dict[node][int_nam]['state'] = match.group(1)
            if re.search( 'link\/ether\s+([a-f0-9\:]+)', line ):
                match = re.search( 'link\/ether\s+([a-f0-9\:]+)', line )
                ip_dict[node][int_nam]['mac_addr'] = match.group(1)
            if re.search( 'inet\s+([0-9\.\/]+)', line ):
                match = re.search( 'inet\s+([0-9\.\/]+)', line )
                ip_dict[node][int_nam]['ipv4_addr_list'].append(match.group(1))
            if re.search( 'inet6\s+([a-f0-9\:\/]+)', line ):
                match = re.search( 'inet6\s+([a-f0-9\:\/]+)', line )
                ip_dict[node][int_nam]['ipv6_addr_list'].append(match.group(1))

    return ip_dict



def get_rdma_nic_dict( phdl ):
    rdma_dict = {}
    out_dict = phdl.exec('sudo rdma link')
    gid_dict_t = phdl.exec('sudo show_gids | grep -i v2 --color=never')
    for node in out_dict.keys():
        rdma_dict[node] = {}
        for line in out_dict[node].split("\n"):
            if re.search( '^link', line ):
                match = re.search( 'link\s+([a-zA-Z0-9\_\-\.]+)\/([0-9]+)\s+state\s+([A-Za-z]+)\s+physical_state\s+([A-Za-z\_]+)\s+netdev\s+([a-z0-9A-Z\.]+)', line)
                dev = match.group(1)
                rdma_dict[node][dev] = {}
                rdma_dict[node][dev]['port'] = match.group(2)
                rdma_dict[node][dev]['device_status'] = match.group(3)
                rdma_dict[node][dev]['link_status'] = match.group(4)
                rdma_dict[node][dev]['eth_device'] = match.group(5)
    gid_dict = {}
    for node in gid_dict_t.keys():
        gid_dict[node] = {}        
        for line in gid_dict_t[node].split("\n"):
            if re.search( '([a-z0-9\_\-]+)\s+([0-9]+)\s+([0-9]+)\s+([a-f0-9\:]+)\s+([0-9\.]+)\s+v2\s+([a-z0-9\_\-]+)', line, re.I ):
                match = re.search( '([a-z0-9\_\-]+)\s+([0-9]+)\s+([0-9]+)\s+([a-f0-9\:]+)\s+([0-9\.]+)\s+v2\s+([a-z0-9\_\-]+)', line, re.I )
                dev = match.group(1)
                rdma_dict[node][dev]['index'] = match.group(3)
                rdma_dict[node][dev]['gid'] = match.group(4)
                rdma_dict[node][dev]['ipv4_addr'] = match.group(5)
            elif re.search( '([a-z0-9\_\-]+)\s+([0-9]+)\s+([0-9]+)\s+([a-f0-9\:]+)\s+v2\s+([a-z0-9\_\-]+)', line, re.I ):
                match = re.search( '([a-z0-9\_\-]+)\s+([0-9]+)\s+([0-9]+)\s+([a-f0-9\:]+)\s+v2\s+([a-z0-9\_\-]+)', line, re.I )
                dev = match.group(1)
                rdma_dict[node][dev]['index'] = match.group(3)
                rdma_dict[node][dev]['gid'] = match.group(4)
                rdma_dict[node][dev]['ipv4_addr'] = None
                
    return rdma_dict

            
   


 

def get_linux_perf_tuning_dict( phdl ):
    out_dict = {}
    out_dict['bios_version'] = phdl.exec('sudo dmidecode -s bios-version')
    out_dict['numa_balancing'] = phdl.exec('sudo sysctl kernel.numa_balancing')
    out_dict['nmi_watchdog'] = phdl.exec('sudo cat /proc/sys/kernel/nmi_watchdog')
    out_dict['huge_pages'] = phdl.exec('sudo cat /sys/kernel/mm/transparent_hugepage/enabled')
    out_dict['cpu_power_profile'] = phdl.exec('sudo cpupower info')


