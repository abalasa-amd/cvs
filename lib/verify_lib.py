
from lib.utils_lib import *



err_patterns_dict = {

    'gpu_reset': 'GPU reset begin|GPU hang|cp might be in an unrecoverable state|fence wait loop timeout expired',
    'crash': 'crashed|Traceback|cut here|Bug:|Call Trace|end trace',
    'test_fail': 'Test failure',
    'access': 'no-retry page fault|Illegal register access|PROTECTION_FAULT_STATUS',
    'driver': 'Queue preemption failed for queue|Failed to evict process queues',
    'hardware': 'hardware error|hardware fail|ras error|uncorrectable|correctable err',
    'down': 'NIC Link is Down'

}


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





def verify_pcie_errors():
    print()

