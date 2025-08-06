
from utils_lib import *
from linux_utils import *
from rocm_plib import *


err_patterns_dict = {

    'gpu_reset': 'GPU reset begin|GPU hang|cp might be in an unrecoverable state|fence wait loop timeout expired',
    'crash': 'crashed|Traceback|cut here|Bug:|Call Trace|end trace|amdgpu: Fatal error',
    'test_fail': 'Test failure',
    'fault': 'no-retry page fault|Illegal register access|PROTECTION_FAULT_STATUS',
    'driver': 'Queue preemption failed for queue|Failed to evict process queues',
    'hardware': 'hardware error|hardware fail|ras error|uncorrectable|correctable err',
    'down': 'NIC Link is Down|link down|link is down'

}

err_stats_pattern = 'err|drop|discard|overflow|fcs|nak|uncorrect|loss'
warn_stats_pattern = 'retry|timeout|exceeded|ooo|retransmit'
threshold_stats_pattern = 'cnp|ecn'
threshold_counter_val=1000


def verify_dmesg_for_errors(phdl, start_time_dict, end_time_dict ):
    print('scan dmesg')
    node0 = list(start_time_dict.keys())[0]
    start_time = start_time_dict[node0]
    end_time = end_time_dict[node0]
    match = re.search( '([a-zA-Z]+\s+[a-zA-Z]+\s+[0-9]+\s+[0-9]+\:[0-9]+\:[0-9]+)\s', start_time)
    start_pattern = match.group(1)
    match = re.search( '([a-zA-Z]+\s+[a-zA-Z]+\s+[0-9]+\s+[0-9]+\:[0-9]+\:[0-9]+)\s', end_time)
    end_pattern = match.group(1)
    output_dict = phdl.exec(f"sudo dmesg -T | awk '/{start_pattern}.*/,/{end_pattern}.*/' | grep -v ALLOWED --color=never")
    #print(output_dict) 
    for node in output_dict.keys():
        for line in output_dict[node].split("\n"):
            for err_key in err_patterns_dict.keys():
                if re.search( f'{err_patterns_dict[err_key]}', line, re.I ):
                    fail_test(f'ERROR - Failue pattern {err_patterns_dict[err_key]} seen in Dmesg')
                    #phdl.exec('sudo dmesg -T > /tmp/dmesg_output')
                    #phdl.exec('sudo dmesg -c')





def create_cluster_metrics_snapshot( phdl, ):
    s_dict = {}
    s_dict['eth_stats'] = get_nic_ethtool_stats_dict( phdl )
    s_dict['rdma_stats'] = get_rdma_stats_dict( phdl )
    #s_dict['gpu_stats'] = get_gpu_metrics_dict( phdl )
    return s_dict


def get_metrics_snapshot_diff_dict( s_dict_before, s_dict_after ):
    diff_dict = {}
    # Initialize diff_dict
    for key_nam in s_dict_before.keys():
        diff_dict[key_nam] = {}
        for node in s_dict_before[key_nam].keys():
            diff_dict[key_nam][node] = {}
            for dev_nam in s_dict_before[key_nam][node].keys():
                diff_dict[key_nam][node][dev_nam] = {}

    for key_nam in s_dict_before.keys():
        for node in s_dict_before[key_nam].keys():
            for dev_nam in s_dict_before[key_nam][node].keys():
                for stat_nam in s_dict_before[key_nam][node][dev_nam].keys():
                    if not isinstance( s_dict_before[key_nam][node][dev_nam][stat_nam], list ):
                        if isinstance( s_dict_before[key_nam][node][dev_nam][stat_nam], str ):
                            if not re.search( '[a-z\.\_\-]+', s_dict_before[key_nam][node][dev_nam][stat_nam], re.I ):
                                diff_dict[key_nam][node][dev_nam][stat_nam] =  \
                                       int(s_dict_after[key_nam][node][dev_nam][stat_nam]) - \
                                       int(s_dict_before[key_nam][node][dev_nam][stat_nam])
                        elif isinstance( s_dict_before[key_nam][node][dev_nam][stat_nam], int ): 
                            diff_dict[key_nam][node][dev_nam][stat_nam] =  \
                                s_dict_after[key_nam][node][dev_nam][stat_nam] - \
                                s_dict_before[key_nam][node][dev_nam][stat_nam]
    return diff_dict
                      
            


def compare_cluster_metrics_snapshots( s_dict_before, s_dict_after ):
    print('Compare 2 cluster snapshots')
    diff_dict = get_metrics_snapshot_diff_dict( s_dict_before, s_dict_after )
    for key_nam in diff_dict.keys():
        for node in diff_dict[key_nam].keys():
            for dev_nam in diff_dict[key_nam][node].keys():
                for stat_nam in diff_dict[key_nam][node][dev_nam].keys():
                    if re.search( f'{warn_stats_pattern}', stat_nam, re.I ):
                        if int(diff_dict[key_nam][node][dev_nam][stat_nam]) > 0:
                            log.warn(f'WARNING !! cluster snapshot showing some warning counters going up - {key_nam} {node} {dev_nam} {stat_nam} has incremented by {diff_dict[key_nam][node][dev_nam][stat_nam]}')
                    elif re.search( f'{err_stats_pattern}', stat_nam, re.I ):
                        if int(diff_dict[key_nam][node][dev_nam][stat_nam]) > 0:
                            log.error(f'ERROR !! cluster snapshot showing some error counters going up - {key_nam} {node} {dev_nam} {stat_nam} has incremented by {diff_dict[key_nam][node][dev_nam][stat_nam]}')
                    elif re.search( f'{threshold_stats_pattern}', stat_nam, re.I ):
                        if int(diff_dict[key_nam][node][dev_nam][stat_nam]) > threshold_counter_val:
                            log.error(f'WARNING !! cluster snapshot showing some threshold warn counters going up - {key_nam} {node} {dev_nam} {stat_nam} has incremented by {diff_dict[key_nam][node][dev_nam][stat_nam]}')



