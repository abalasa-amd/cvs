import os
import sys
import re
import json

from rocm_plib import *

#<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">

def build_html_page_header(filename):
    print('Build HTML Page header')
    with open(filename, 'w') as fp:
         html_lines='''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>CVS Cluster View</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
<!-- DataTables CSS -->
<style>
   .highlight-red {
      color: red;
   }
   .label-danger {
      color: red;
   }
</style>
</head>
<body>
         '''
         fp.write(html_lines)
         fp.close()

 


def build_html_page_footer( filename, ):
    print('Build HTML Page header')
    with open(filename, 'a') as fp:
         html_lines='''
<!-- jQuery -->
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<!-- DataTables JS -->
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>

<script>
  // Initialize DataTable
  $(document).ready(function() {
    $('#prod').DataTable({
     "pageLength": 100,
     "autoWidth": true
    });
    $('#gpuuse').DataTable({
     "scrollX": true,
     "pageLength": 100,
     "autoWidth": true
    });
    $('#memuse').DataTable({
     "scrollX": true,
     "pageLength": 100,
     "autoWidth": true
    });
    $('#nic').DataTable({
     "scrollX": true,
     "pageLength": 100,
     "autoWidth": true
    });
    $('#training').DataTable({
     "scrollX": true,
     "pageLength": 100,
     "autoWidth": true
    });
    $('#ethtoolstats').DataTable({
     "scrollX": true,
     "pageLength": 100,
     "autoWidth": true
    });
    $('#rdmastats').DataTable({
     "scrollX": true,
     "pageLength": 100,
     "autoWidth": true
    });
    $('#pciexgmimetrics').DataTable({
     "scrollX": true,
     "pageLength": 100,
     "autoWidth": true
    });
    $('#error').DataTable({
     "scrollX": true,
     "pageLength": 100,
     "autoWidth": true
    });
  });
</script>

</body>
</html>
         '''
         fp.write(html_lines)
         fp.close()



def build_rdma_stats_table( filename, rdma_dict, ):
    node_0 = list(rdma_dict.keys())[0]
    err_pattern = 'err|retransmit|drop|discard|naks|invalid|oflow|out_of_buffer'
    rdma_device_list = rdma_dict[node_0].keys()
 
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">RDMA Statistics Table</h2>
<table id="rdmastats" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>'''
         fp.write(html_lines)
         for rdma_device in rdma_device_list:
             fp.write(f'<th>{rdma_device}</th>\n')
         fp.write('</tr></thead>\n')
         # End or header, let us start data rows ..

         for node in rdma_dict.keys():
             # begin each node row
             fp.write(f'<tr><td>{node}</td>\n')
             for rdma_device in rdma_device_list:
                 fp.write(f'<td><table border=1>\n')
                 stats_dict = rdma_dict[node][rdma_device]
                 for stats_key in stats_dict.keys():
                     if stats_key != "ifname":
                         if int(stats_dict[stats_key]) > 0:
                             if re.search( f'{err_pattern}', stats_key, re.I ):
                                 fp.write(f'<tr><td>{stats_key}</td><td><span class="label label-danger">{stats_dict[stats_key]}</td></tr>\n')
                             else: 
                                 fp.write(f'<tr><td>{stats_key}</td><td>{stats_dict[stats_key]}</td></tr>\n')
                 fp.write(f'</table></td>\n')
             #End of each node row
             fp.write(f'</tr>\n')
         html_lines='''
         </table>
         <br><br>
         '''
         fp.write(html_lines)
         fp.close()
             
        

def build_ethtool_stats_table( filename, d_dict, ):
    node_0 = list(d_dict.keys())[0]
    eth_device_list = d_dict[node_0].keys()
    err_pattern = 'err|retransmit|drop|discard|naks|invalid|oflow|out_of_buffer|collision|reset|uncorrect'
 
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">Ethtool Statistics Table</h2>
<table id="ethtoolstats" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>'''
         fp.write(html_lines)
         for eth_device in eth_device_list:
             fp.write(f'<th>{eth_device}</th>\n')
         fp.write('</tr></thead>\n')
         # End or header, let us start data rows ..

         for node in d_dict.keys():
             # begin each node row
             fp.write(f'<tr><td>{node}</td>\n')
             for eth_device in eth_device_list:
                 fp.write(f'<td><table border=1>\n')
                 stats_dict = d_dict[node][eth_device]
                 for stats_key in stats_dict.keys():
                     if int(stats_dict[stats_key]) > 0:
                         if re.search( f'{err_pattern}', stats_key, re.I ):
                             fp.write(f'<tr><td>{stats_key}</td><td><span class="label label-danger">{stats_dict[stats_key]}</td></tr>\n')
                         else: 
                             fp.write(f'<tr><td>{stats_key}</td><td>{stats_dict[stats_key]}</td></tr>\n')
                 fp.write(f'</table></td>\n')
             #End of each node row
             fp.write(f'</tr>\n')
         html_lines='''
         </table>
         <br><br>
         '''
         fp.write(html_lines)
         fp.close()
             
        







def build_training_results_table( filename, out_dict, title ):
    print('Build HTML training table')
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">''' + title + '''</h2>
<table id="training" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>
  <th>Throughput per GPU</th>
  <th>Tokens per GPU</th>
  <th>Elapsed time per iteration</th>
  <th>Nan iterations</th>
  <th>Mem usage</th>
  <tr>'''
         fp.write(html_lines)
         for node in out_dict.keys():
             d_dict = out_dict[node]
             html_lines='''
  <tr>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  </tr>'''.format( node, d_dict['throughput_per_gpu'],
             d_dict['tokens_per_gpu'], d_dict['elapsed_time_per_iteration'],
             d_dict['nan_iterations'], d_dict['mem_usages'] )
             fp.write(html_lines)
         html_lines='''
         </table>
         <br><br>
         '''
         fp.write(html_lines)
         fp.close()


             




def build_html_nic_table( filename, rdma_dict, lshw_dict, ip_dict ):
    print('Build HTML product table')
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">Network Info</h2>
<table id="nic" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>
  <th>Eth Device</th>
  <th>RDMA Device</th>
  <th>Link Status</th>
  <th>RDMA Status</th>
  <th>PCIe Bus</th>
  <th>MTU</th>
  <th>IP Addr List</th>
  </tr>
  </thead>'''
         fp.write(html_lines)
         for node in rdma_dict.keys():
             rdma_dev_list = list(rdma_dict[node].keys())
             eth_dev_list = []
             dev_status_list = []
             link_status_list = []
             pcie_bus_list = []
             mtu_list = []
             ip_list = []
             print(rdma_dev_list)
             print(rdma_dict)
             for rdma_dev in rdma_dev_list:
                 eth_dev = rdma_dict[node][rdma_dev]['eth_device']
                 eth_dev_list.append(eth_dev)
                 dev_status_list.append(rdma_dict[node][rdma_dev]['device_status'])
                 link_status_list.append(rdma_dict[node][rdma_dev]['link_status'])
                 pcie_bus_list.append(lshw_dict[node][eth_dev]['pci_bus'])
                 mtu_list.append(ip_dict[node][eth_dev]['mtu'])
                 ip_list.append(ip_dict[node][eth_dev]['ipv4_addr_list'])
             html_lines='''
  <tr>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  </tr>
  '''.format( node,
             eth_dev_list, rdma_dev_list, link_status_list,
             dev_status_list, pcie_bus_list, mtu_list, ip_list )
             fp.write(html_lines)
         html_lines='''
         </table>
         <br><br>
         '''
         fp.write(html_lines)
         fp.close()



def build_html_cluster_product_table( filename, model_dict, fw_dict ):
    print('Build HTML product table')
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">Product Info</h2>
<table id="prod" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>
  <th>Model</th>
  <th>GFX Ver</th>
  <th>SKU</th>
  <th>MEC Fw</th>
  <th>RLC Fw</th>
  <th>SDMA Fw</th>
  <th>SMC Fw</th>
  <th>SOS Fw</th>
  <th>TA RAS Fw</th>
  <th>TA XGMI Fw</th>
  <th>VCN Fw</th>
  </tr>
  </thead>'''
         fp.write(html_lines)
         for node in model_dict.keys():
             m_dict = model_dict[node]["card0"]
             f_dict = fw_dict[node]["card0"]
             print(m_dict)
             print(f_dict)
             if not 'SOS firmware version' in f_dict:
                 f_dict['SOS firmware version'] = "-"
             html_lines='''
  <tr>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  </tr>
  '''.format( node, m_dict['Card Series'], m_dict['GFX Version'], m_dict['Card SKU'],
             f_dict['MEC firmware version'], f_dict['RLC firmware version'],
             f_dict['RLC SRLC firmware version'], f_dict['RLC SRLG firmware version'],
             f_dict['RLC SRLS firmware version'], f_dict['SDMA firmware version'],
             f_dict['SMC firmware version'], f_dict['SOS firmware version'],
             f_dict['TA RAS firmware version'], f_dict['TA XGMI firmware version'],
             f_dict['VCN firmware version']
             )
             fp.write(html_lines)
         html_lines='''
         </table>
         <br><br>
         '''
         fp.write(html_lines)
         fp.close()

 

def build_html_gpu_utilization_table( filename, use_dict ):
    print('Build HTML utilization table')
    print('^^^^^')
    #print(use_dict)
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">GPU Utilization</h2>
<table id="gpuuse" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>
  <th>GPU0 use</th>
  <th>GPU0 GFX Activ</th>
  <th>GPU1 use</th>
  <th>GPU1 GFX Activ</th>
  <th>GPU2 use</th>
  <th>GPU2 GFX Activ</th>
  <th>GPU3 use</th>
  <th>GPU3 GFX Activ</th>
  <th>GPU4 use</th>
  <th>GPU4 GFX Activ</th>
  <th>GPU5 use</th>
  <th>GPU5 GFX Activ</th>
  <th>GPU6 use</th>
  <th>GPU6 GFX Activ</th>
  <th>GPU7 use</th>
  <th>GPU7 GFX Activ</th>
  </tr>
  </thead>'''
         fp.write(html_lines)
         for node in use_dict.keys():
             u_dict = use_dict[node]
             html_lines='''
  <tr>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  </tr>'''.format(
             node,
             u_dict['card0']['GPU use (%)'], u_dict['card0']['GFX Activity'],
             u_dict['card1']['GPU use (%)'], u_dict['card1']['GFX Activity'],
             u_dict['card2']['GPU use (%)'], u_dict['card2']['GFX Activity'],
             u_dict['card3']['GPU use (%)'], u_dict['card3']['GFX Activity'],
             u_dict['card4']['GPU use (%)'], u_dict['card4']['GFX Activity'],
             u_dict['card5']['GPU use (%)'], u_dict['card5']['GFX Activity'],
             u_dict['card6']['GPU use (%)'], u_dict['card6']['GFX Activity'],
             u_dict['card7']['GPU use (%)'], u_dict['card7']['GFX Activity'],
             )
             fp.write(html_lines)
         html_lines='''
         </table>
         <br><br>
         '''
         fp.write(html_lines)
         fp.close()




def build_html_mem_utilization_table( filename, use_dict, amd_dict ):
    print('Build HTML mem utilization table')
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">GPU Memory Utilization</h2>
<table id="memuse" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>
         '''
         fp.write(html_lines)
         for i in range(0,8):
             html_lines=f'''
  <th>G{i} Tot VRAM MB</th>
  <th>G{i} Used VRAM MB</th>
  <th>G{i} Free VRAM MB</th>
  <th>G{i} Mem Allocated</th>
  <th>G{i} Read/Write Acti</th>
  <th>G{i} Mem Acti</th>
  <th>G{i} Mem BW</th>
             '''
             fp.write(html_lines)
         html_lines='''
  </tr>
  </thead>'''
         fp.write(html_lines)
         for node in use_dict.keys():
             html_lines='''
  <tr>
  <td>{}</td>
             '''.format(node)
             fp.write(html_lines)
             u_dict = use_dict[node]
             #a_list = amd_dict[node]
             if isinstance( amd_dict[node], dict ):
                 # handling different between rocm6.x and 7.x
                 if 'gpu_data' in amd_dict[node].keys():
                     a_list = amd_dict[node]['gpu_data']
             else:
                 a_list = amd_dict[node]
             for j in range(0,8):
                 card = 'card' + str(j)
                 a_dict = a_list[j]
                 html_lines='''
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  '''.format(
                 a_dict['mem_usage']['total_vram']['value'],
                 a_dict['mem_usage']['used_vram']['value'],
                 a_dict['mem_usage']['free_vram']['value'],
                 u_dict[card]['GPU Memory Allocated (VRAM%)'],
                 u_dict[card]['GPU Memory Read/Write Activity (%)'],
                 u_dict[card]['Memory Activity'],
                 u_dict[card]['Avg. Memory Bandwidth']
                 )
                 fp.write(html_lines)
             html_lines='''
  </tr>
             '''
             fp.write(html_lines)
         html_lines='''
         </table>
         <br><br>
         '''
         fp.write(html_lines)
         fp.close()



def build_html_pcie_xgmi_metrics_table( filename, metrics_dict, amd_dict ):
    print('Build HTML PCIe metrics table')
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">GPU PCIe XGMI Metrics Table</h2>
<table id="pciexgmimetrics" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>
         '''
         fp.write(html_lines)
         for i in range(0,8):
             html_lines=f'''
  <th>G{i} pcie lanes</th>
  <th>G{i} pcie lane speed GT/s:</th>
  <th>G{i} PCIe BW inst Mb/s</th>
  <th>G{i} PCIe l0 to recov count acc</th>
  <th>G{i} PCIe replay count acc</th>
  <th>G{i} PCIe replay rover count acc</th>
  <th>G{i} PCIe nak sent count acc</th>
  <th>G{i} PCIe nak rcvd count acc</th>
  <th>G{i} XGMI link width</th>
  <th>G{i} XGMI link Speed Gbps</th>
  <th>G{i} XGMI link status toggle up/down</th>
  <th>G{i} VRAM max BW GB/s</th>
             '''
             fp.write(html_lines)
         html_lines='''
  </tr>
  </thead>'''
         fp.write(html_lines)
         for node in metrics_dict.keys():
             html_lines='''
  <tr>
  <td>{}</td>
             '''.format(node)
             fp.write(html_lines)
             d_dict = metrics_dict[node]
             if isinstance( amd_dict[node], dict ):
                 # handling different between rocm6.x and 7.x
                 if 'gpu_data' in amd_dict[node].keys():
                      a_list = amd_dict[node]['gpu_data']
             else:
                 a_list = amd_dict[node]
             for j in range(0,8):
                 card = 'card' + str(j)
                 a_dict = a_list[j]
                 html_lines='''
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  <td>{}</td>
  '''.format(
                 a_dict['pcie']['width'],
                 a_dict['pcie']['speed']['value'],
                 a_dict['pcie']['bandwidth']['value'],
                 d_dict[card]['pcie_l0_to_recov_count_acc (Count)'],
                 d_dict[card]['pcie_replay_count_acc (Count)'],
                 d_dict[card]['pcie_replay_rover_count_acc (Count)'],
                 d_dict[card]['pcie_nak_sent_count_acc (Count)'],
                 d_dict[card]['pcie_nak_rcvd_count_acc (Count)'],
                 d_dict[card]['xgmi_link_width'],
                 d_dict[card]['xgmi_link_speed (Gbps)'],
                 d_dict[card]['xgmi_link_status (Up/Down)'],
                 d_dict[card]['vram_max_bandwidth (GB/s)'],
                 )
                 fp.write(html_lines)
             html_lines='''
  </tr>
             '''
             fp.write(html_lines)
         html_lines='''
         </table>
         <br><br>
         '''
         fp.write(html_lines)
         fp.close()

 



def build_html_error_table( filename, metrics_dict, amd_dict ):
    print('Build HTML Error table')
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">GPU Error Metrics Table</h2>
<table id="error" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>
         '''
         fp.write(html_lines)
         for i in range(0,8):
             html_lines=f'''
  <th>G{i} ECC correct</th>
  <th>G{i} ECC uncorrect</th>
  <th>G{i} ECC deferred</th>
  <th>G{i} ECC cache correct</th>
  <th>G{i} ECC cache uncorrect</th>
  <th>G{i} PCIe l0 to recov count acc</th>
  <th>G{i} PCIe replay count acc</th>
  <th>G{i} PCIe replay rover count acc</th>
  <th>G{i} PCIe nak sent count acc</th>
  <th>G{i} PCIe nak rcvd count acc</th>
             '''
             fp.write(html_lines)
         html_lines='''
  </tr>
  </thead>'''
         fp.write(html_lines)
         for node in metrics_dict.keys():
             html_lines='''
  <tr>
  <td>{}</td>
             '''.format(node)
             fp.write(html_lines)
             d_dict = metrics_dict[node]
             if isinstance( amd_dict[node], dict ):
                 # handling different between rocm6.x and 7.x
                 if 'gpu_data' in amd_dict[node].keys():
                     a_list = amd_dict[node]['gpu_data']
             else:
                 a_list = amd_dict[node]
             for j in range(0,8):
                 card = 'card' + str(j)
                 a_dict = a_list[j]
                 if int(a_dict['ecc']['total_correctable_count']) > 0:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(a_dict['ecc']['total_correctable_count'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(a_dict['ecc']['total_correctable_count'])
                 fp.write(html_lines)
                 
                 if int(a_dict['ecc']['total_uncorrectable_count']) > 0:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(a_dict['ecc']['total_uncorrectable_count'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(a_dict['ecc']['total_uncorrectable_count'])
                 fp.write(html_lines)
                 
                 if int(a_dict['ecc']['total_deferred_count']) > 0:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(a_dict['ecc']['total_deferred_count'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(a_dict['ecc']['total_deferred_count'])
                 fp.write(html_lines)
                 
                 if int(a_dict['ecc']['cache_correctable_count']) > 0:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(a_dict['ecc']['cache_correctable_count'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(a_dict['ecc']['cache_correctable_count'])
                 fp.write(html_lines)
                 
                 if int(a_dict['ecc']['cache_uncorrectable_count']) > 0:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(a_dict['ecc']['cache_uncorrectable_count'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(a_dict['ecc']['cache_uncorrectable_count'])
                 fp.write(html_lines)
  
                 if int(d_dict[card]['pcie_l0_to_recov_count_acc (Count)']) > 4:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(d_dict[card]['pcie_l0_to_recov_count_acc (Count)'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(d_dict[card]['pcie_l0_to_recov_count_acc (Count)'])
                 fp.write(html_lines)

                 if int(d_dict[card]['pcie_replay_count_acc (Count)']) > 0:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(d_dict[card]['pcie_replay_count_acc (Count)'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(d_dict[card]['pcie_replay_count_acc (Count)'])
                 fp.write(html_lines)

                 if int(d_dict[card]['pcie_replay_rover_count_acc (Count)']) > 0:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(d_dict[card]['pcie_replay_rover_count_acc (Count)'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(d_dict[card]['pcie_replay_rover_count_acc (Count)'])
                 fp.write(html_lines)


                 if int(d_dict[card]['pcie_nak_sent_count_acc (Count)']) > 0:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(d_dict[card]['pcie_nak_sent_count_acc (Count)'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(d_dict[card]['pcie_nak_sent_count_acc (Count)'])
                 fp.write(html_lines)

                 if int(d_dict[card]['pcie_nak_rcvd_count_acc (Count)']) > 0:
                     html_lines='''
                     <td><span class="label label-danger">{}</td>
                     '''.format(d_dict[card]['pcie_nak_rcvd_count_acc (Count)'])
                 else:
                     html_lines='''
                     <td>{}</td>
                     '''.format(d_dict[card]['pcie_nak_rcvd_count_acc (Count)'])
                 fp.write(html_lines)

  
             html_lines='''
  </tr>
             '''
             fp.write(html_lines)
         html_lines='''
         </table>
         <br><br>
         '''
         fp.write(html_lines)
         fp.close()

 
    




def build_html_env_metrics_table():
    print('Build HTML env metrics table')
    with open(filename, 'a') as fp:
         html_lines='''
<h2 style="background-color: lightblue">GPU Environmental Metrics Table</h2>
<table id="envmetrics" class="display cell-border">
  <thead>
  <tr>
  <th>Node</th>
  <th>G0 Temp hotspot</th>
  <th>G0 Temp Mem</th>
  <th>G0 Temp vrsoc</th>
  <th>G0 gfxclk</th>
  <th>G0 uclk</th>
  <th>G0 pcie lanes</th>
  <th>G0 pcie speed GT/s:</th>
  <th>G0 gfx activi</th>
  <th>G0 mem activi</th>
  <th>G0 PCIe BW acc GB/s</th>
  <th>G0 PCIe BW inst GB/s</th>
  <th>G0 socket power</th>
  <th>G0 XGMI link width</th>
  <th>G0 XGMI link Speed Gbps</th>
  <th>G0 PCIe l0 to recov count acc</th>
  <th>G0 PCIe replay count acc</th>
  <th>G0 PCIe nak sent count acc</th>
  <th>G0 PCIe nak rcvd count acc</th>
  <th>G0 VRAM max BW GB/s</th>
         '''





def build_html_config_table():
    print('Build config table')



