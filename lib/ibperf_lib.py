'''
Copyright 2025 Advanced Micro Devices, Inc.
All rights reserved. This notice is intended as a precaution against inadvertent publication and does not imply publication or any waiver of confidentiality.
The year included in the foregoing notice is the year of creation of the work.
All code contained here is Property of Advanced Micro Devices, Inc.
'''


import os
import sys
import re
import time
import xlsxwriter

from utils_lib import *



def get_ib_bw_pps(phdl, msg_size, cmd ):
    res_dict = {}

    #Run some of the standard verifications
    out_dict = phdl.exec(cmd)
    err_pattern = "Couldn\'t initialize ROCm device|Failed to init|Unable to open file descriptor|ERROR|FAIL|Segmentation fault"
    for node in out_dict.keys():
        if not re.search( 'bytes of GPU buffer', out_dict[node], re.I ):
            fail_test('GPU Buffer allocation failed or Connection not setup for IB Test on node {node}')

        if re.search( err_pattern, out_dict[node], re.I ):
            fail_test('IB Test failed - Error patterns seen on node {node}')

    # Collect the BW, PPS numbers 
    for i in range(1,10):
        out_dict = phdl.exec(cmd)
        for node in out_dict.keys():
            res_dict[node] = {}
            pattern = r"{}\s+\d+\s+[0-9\.]+\s+([0-9\.]+)\s+([0-9\.]+)".format(msg_size)
            if re.search( pattern, out_dict[node] ):
                match = re.search( pattern, out_dict[node] )
                res_dict[node]['bw'] = match.group(1)
                res_dict[node]['pps'] = match.group(2)
                print(f'Node {node} BW - {res_dict[node]['bw']}, MPPS - {res_dict[node]['pps']}')
                continue
            else:
                print('Sleeping 10 secs for test to complete')
                time.sleep(10)
            fail_test(f'ERROR !!! on node {node} Client did not complete even after max iterations')
            fail_test(f'ERROR !!! pls check log file for errors on node {node}')
    return res_dict





def verify_expected_bw( bw_test, msg_size, qp_count, res_dict, expected_res ):
    print(f'Verifying expected BW for test {bw_test} msg_size {msg_size} QP count {qp_count}')
    print(expected_res.keys())
    print(res_dict)
    if bw_test in expected_res.keys():
        print(expected_res[bw_test].keys())
        if msg_size in expected_res[bw_test].keys():
            if qp_count in expected_res[bw_test][msg_size].keys():
                for node in res_dict.keys():
                    if float(res_dict[node]['bw']) <= float(expected_res[bw_test][msg_size]):
                        fail_test(f"Actual BW {res_dict[node]['bw']} less than the expected BW {expected_res[bw_test][msg_size]} for test {bw_test} on node {node}")




def run_ib_perf_test( phdl, bw_test, gpu_numa_dict, gpu_nic_dict, bck_nic_dict, app_path, \
        msg_size, gid_index, qp_count=8, port_no=1516, duration=60 ):
    app_port = port_no
    result_dict = {}
    i=0
    cmd_dict = {}
    phdl.exec('rm -rf /tmp/ib_cmds_file.txt')
    phdl.exec('touch /tmp/ib_cmds_file.txt')
    server_addr = None
    for node in bck_nic_dict.keys():
        result_dict[node] = {}
        cmd_dict[node] = []
        #even nodes make it server and odd as clients
        if i%2 == 0:
            # server
            server_addr = node
            cmd = 'echo "sleep 1" >> /tmp/ib_cmds_file.txt'
            cmd_dict[node].append(cmd)
            inst_count=0
            for gpu_no in range(0,8):
                card_no = 'card' + str(gpu_no)
                rdma_dev = gpu_nic_dict[node][card_no]['rdma_dev']
                cmd = f'numactl --physcpubind={gpu_numa_dict[node][card_no]["local_cpulist"]} --localalloc {app_path}/{bw_test} -d {rdma_dev} --use_rocm={gpu_no} -x {gid_index} --report_gbits -b -F -D {duration} -p {port_no} -R -s {msg_size} -q {qp_count} > /tmp/ib_perf_{inst_count}_logs &  2>&1'
                cmd_dict[node].append( f'echo "{cmd}" >> /tmp/ib_cmds_file.txt' )
                inst_count = inst_count + 1
                port_no = port_no + 1
        else:
            # client
            cmd = 'echo "sleep 5" >> /tmp/ib_cmds_file.txt'
            cmd_dict[node].append(cmd)
            inst_count=0
            port_no = app_port
            for gpu_no in range(0,8):
                card_no = 'card' + str(gpu_no)
                rdma_dev = gpu_nic_dict[node][card_no]['rdma_dev']
                cmd = f'numactl --physcpubind={gpu_numa_dict[node][card_no]["local_cpulist"]} --localalloc {app_path}/{bw_test} -d {rdma_dev} --use_rocm={gpu_no} -x {gid_index} --report_gbits -b -F -D {duration} -p {port_no} -R -s {msg_size} -q {qp_count} {server_addr} > /tmp/ib_perf_{inst_count}_logs &  2>&1'
                cmd_dict[node].append( f'echo "{cmd}" >> /tmp/ib_cmds_file.txt' )
                inst_count = inst_count + 1
                port_no = port_no + 1
        i = i+1


    # Get number of commands in cmd_dict - should be same for all nodes
    node_list = list(cmd_dict.keys())
    first_node_cmd_list = cmd_dict[node_list[0]]

    for j in range(0, len(first_node_cmd_list)):
        cmd_list = []
        for node in cmd_dict.keys():
            cmd_list.append(cmd_dict[node][j])
        #print(cmd_list)
        phdl.exec_cmd_list(cmd_list)


    # Clean up any stale instances of ib_write_bw from earlier runs ..
    phdl.exec('killall ib_write_bw')
    time.sleep(2)
    phdl.exec('source /tmp/ib_cmds_file.txt')

    # wait for the duration of test 
    time.sleep( int(duration) + 10 )

    for instance_no in range(0, inst_count ):
        print('instance_no - {}'.format(instance_no))
        try:
           bw_pps_dict = get_ib_bw_pps( phdl, msg_size, f'cat /tmp/ib_perf_{instance_no}_logs')
           for node in bw_pps_dict.keys():
               result_dict[node][instance_no] = {}
               result_dict[node][instance_no]['pps'] = bw_pps_dict[node]['pps']
               result_dict[node][instance_no]['bw'] = bw_pps_dict[node]['bw']
        except Exception as e:
           print('FAILED to get BW, PPS numbers for size - {} qp_count {}'.format(msg_size, qp_count))

    return result_dict






# Sample res_dict
# {'ib_write_bw': {2: {'8': {'x.x.x.x': {0: {'pps': '6.229094', 'bw': '0.099666'}, 1: {'pps': '6.391922', 'bw': '0.102271'}, .... 7: { 'pps': '6.79', 'bw': '0.10227' }}
# Top level - application like ib_write_bw, ib_read_bw
# 2 - msg_size
# 8 - Number of QPs
# x.x.x.x - Node IP
# 0 - NIC Instance (will have 0-7)
# pps - packets per sec
# BW - Bandwidth in Gbps

def generate_ibperf_bw_chart( res_dict, excel_file='ib_bw_pps_perf.xlsx' ):

    workbook = xlsxwriter.Workbook( excel_file )

    colors = ["#E41A1C", "#377EB8", "#4DAF4A", ]

    app_list = list(res_dict.keys())

    merge_format = workbook.add_format(
       {
           "bold": 1,
           "border": 1,
           "align": "center",
           "valign": "vcenter",
           "bg_color": "yellow",
       }
    )
    node_merge_format = workbook.add_format(
       {
           "bold": 1,
           "border": 1,
           "align": "center",
           "valign": "vcenter",
       }
    )

    node_list = []
    msg_size_list = []
    qp_count_list = []
    gpu_no_list = [ 0,1,2,3,4,5,6,7 ]

    for app_name in app_list:

        for msg_size in res_dict[app_name].keys():
            if msg_size not in msg_size_list:
                msg_size_list.append(msg_size)

            for qp_count in res_dict[app_name][msg_size].keys():
                if qp_count not in qp_count_list:
                    qp_count_list.append(qp_count)

                for node in res_dict[app_name][msg_size][qp_count].keys():
                    if node not in node_list:
                        node_list.append(node)


    #headings = [ "Msg Size" ]
    #for node in node_list:
    #    heading_str = node + ' Total BW'
    #    headings.append(heading_str)
    #    heading_str = node + ' Total PPS'
    #    headings.append(heading_str)


    for app_name in ['ib_write_bw']:
        data = []
        for qp_count in qp_count_list:                         
            sheet_name = app_name + "_qp_" + str(qp_count)
            worksheet = workbook.add_worksheet(sheet_name)
            bold = workbook.add_format({ "bold": 1})

            heading = "Test {} - BW, MPPS Numbers for {} QPs".format(app_name, qp_count)
            worksheet.merge_range("A1:O1", heading, merge_format)
            row_pos = 2
            col_pos = 1
    
            # Init data lists
            d_node_list = node_list
            d_msg_size_list = msg_size_list
            d_bw_gpu_0_list = [] 
            d_bw_gpu_1_list = [] 
            d_bw_gpu_2_list = [] 
            d_bw_gpu_3_list = [] 
            d_bw_gpu_4_list = [] 
            d_bw_gpu_5_list = [] 
            d_bw_gpu_6_list = [] 
            d_bw_gpu_7_list = []
            d_pps_gpu_0_list = [] 
            d_pps_gpu_1_list = [] 
            d_pps_gpu_2_list = [] 
            d_pps_gpu_3_list = [] 
            d_pps_gpu_4_list = [] 
            d_pps_gpu_5_list = [] 
            d_pps_gpu_6_list = [] 
            d_pps_gpu_7_list = []
            d_pps_total_list = []
            d_bw_total_list = []


            for node in node_list:
                for msg_size in msg_size_list:
                    tot_pps = 0.0
                    tot_bw = 0.0
                    for gpu_no in gpu_no_list:
                        if gpu_no == 0:
                            d_bw_gpu_0_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'] )
                            d_pps_gpu_0_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'] )
                            tot_pps = tot_pps + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'])
                            tot_bw = tot_bw + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'])
                        if gpu_no == 1:
                            d_bw_gpu_1_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'] )
                            d_pps_gpu_1_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'] )
                            tot_pps = tot_pps + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'])
                            tot_bw = tot_bw + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'])
                        if gpu_no == 2:
                            d_bw_gpu_2_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'] )
                            d_pps_gpu_2_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'] )
                            tot_pps = tot_pps + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'])
                            tot_bw = tot_bw + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'])
                        if gpu_no == 3:
                            d_bw_gpu_3_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'] )
                            d_pps_gpu_3_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'] )
                            tot_pps = tot_pps + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'])
                            tot_bw = tot_bw + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'])
                        if gpu_no == 4:
                            d_bw_gpu_4_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'] )
                            d_pps_gpu_4_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'] )
                            tot_pps = tot_pps + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'])
                            tot_bw = tot_bw + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'])
                        if gpu_no == 5:
                            d_bw_gpu_5_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'] )
                            d_pps_gpu_5_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'] )
                            tot_pps = tot_pps + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'])
                            tot_bw = tot_bw + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'])
                        if gpu_no == 6:
                            d_bw_gpu_6_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'] )
                            d_pps_gpu_6_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'] )
                            tot_pps = tot_pps + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'])
                            tot_bw = tot_bw + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'])
                        if gpu_no == 7:
                            d_bw_gpu_7_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'] )
                            d_pps_gpu_7_list.append( res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'] )
                            tot_pps = tot_pps + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['pps'])
                            tot_bw = tot_bw + float(res_dict[app_name][msg_size][qp_count][node][gpu_no]['bw'])
                    d_bw_total_list.append(tot_bw)
                    d_pps_total_list.append(tot_pps)

        
             
            data = [ node_list, msg_size_list, d_bw_gpu_0_list, d_bw_gpu_1_list, d_bw_gpu_2_list, d_bw_gpu_3_list, \
                     d_bw_gpu_4_list, d_bw_gpu_5_list, d_bw_gpu_6_list ]
            #Merge cols for Node IP 
            worksheet.merge_range( "A2:A3", "Node IP", bold ) 
            worksheet.merge_range( "B2:B3", "Msg Size", bold ) 
            # Merge 2 cols for every GPU and Total
            worksheet.merge_range( "C2:D2", "Total", bold )
            worksheet.merge_range( "E2:F2", "GPU0", bold )
            worksheet.merge_range( "G2:H2", "GPU1", bold )
            worksheet.merge_range( "I2:J2", "GPU2", bold )
            worksheet.merge_range( "K2:L2", "GPU3", bold )
            worksheet.merge_range( "M2:N2", "GPU4", bold )
            worksheet.merge_range( "O2:P2", "GPU5", bold )
            worksheet.merge_range( "Q2:R2", "GPU6", bold )
            worksheet.merge_range( "S2:T2", "GPU7", bold )
         
            headings = []
            for i in range(0,9):
                headings.append("BW")
                headings.append("PPS")  
            # Write headings for BW, PPS for total and every GPU     
            worksheet.write_row( "C3", headings, bold )

            cur_row = 4
            msg_list_len = len(msg_size_list)
            for node_ip in node_list:
                worksheet.merge_range( f"A{cur_row}:A{cur_row+msg_list_len-1}", node_ip )
                cur_row = cur_row + msg_list_len

            worksheet.write_column( "B4", msg_size_list )
            worksheet.write_column( "C4", d_bw_total_list )
            worksheet.write_column( "D4", d_pps_total_list )
            worksheet.write_column( "E4", d_bw_gpu_0_list )
            worksheet.write_column( "F4", d_pps_gpu_0_list )
            worksheet.write_column( "G4", d_bw_gpu_1_list )
            worksheet.write_column( "H4", d_pps_gpu_1_list )
            worksheet.write_column( "I4", d_bw_gpu_2_list )
            worksheet.write_column( "J4", d_pps_gpu_2_list )
            worksheet.write_column( "K4", d_bw_gpu_3_list )
            worksheet.write_column( "L4", d_pps_gpu_3_list )
            worksheet.write_column( "M4", d_bw_gpu_4_list )
            worksheet.write_column( "N4", d_pps_gpu_4_list )
            worksheet.write_column( "O4", d_bw_gpu_5_list )
            worksheet.write_column( "P4", d_pps_gpu_5_list )
            worksheet.write_column( "Q4", d_bw_gpu_6_list )
            worksheet.write_column( "R4", d_pps_gpu_6_list )
            worksheet.write_column( "S4", d_bw_gpu_7_list )
            worksheet.write_column( "T4", d_pps_gpu_7_list )

    workbook.close()

