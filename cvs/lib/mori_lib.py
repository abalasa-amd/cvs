'''
Copyright 2026 Advanced Micro Devices, Inc.
All rights reserved. This notice is intended as a precaution against inadvertent publication and does not imply publication or any waiver of confidentiality.
The year included in the foregoing notice is the year of creation of the work.
All code contained here is Property of Advanced Micro Devices, Inc.
'''

import re
import time
from typing import List, Dict


from cvs.lib import globals
from cvs.lib.utils_lib import *
from cvs.lib.verify_lib import *

log = globals.log


def textwrap_for_cmd(msg_string):
    return '\n'.join([m.lstrip() for m in msg_string.split('\n')])


HEADER_MAP = {
    "MsgSize (B)": "MsgSize_B",
    "BatchSize": "BatchSize",
    "TotalSize (MB)": "TotalSize_MB",
    "Max BW (GB/s)": "Max_BW_GBps",
    "Avg Bw (GB/s)": "Avg_BW_GBps",
    "Min Lat (us)": "Min_Lat_us",
    "Avg Lat (us)": "Avg_Lat_us",
}


def _convert_value(val: str):
    """Convert string to int or float."""
    val = val.strip()
    if "." in val:
        return float(val)
    return int(val)


def parse_pretty_tables_multi_rank(text: str) -> dict:
    """
    Parse multiple pretty-printed tables (one per Initiator Rank)
    into a single JSON file.

    Args:
        text (str): Raw benchmark output (multiple ranks concatenated).
    """

    lines = [line.rstrip() for line in text.splitlines() if line.strip()]

    results: Dict[int, Dict[str, List[Dict]]] = {}
    i = 0

    while i < len(lines):
        line = lines[i]
        # -----------------------------
        # Detect rank header
        # -----------------------------
        if "Initiator Rank" in line:
            match = re.search(r"Initiator Rank\s+(\d+)", line)
            if not match:
                i += 1
                continue

            rank = int(match.group(1))
            results[rank] = {"rows": []}

            # -----------------------------
            # Find header row
            # -----------------------------
            while i < len(lines) and not lines[i].startswith("| MsgSize"):
                i += 1
            headers = [h.strip() for h in lines[i].strip("|").split("|")]
            json_headers = [HEADER_MAP[h] for h in headers]

            # Skip separator line
            i += 2

            # -----------------------------
            # Parse data rows
            # -----------------------------
            while i < len(lines):
                row_line = lines[i]

                if row_line.startswith("+"):
                    break

                if not row_line.startswith("|"):
                    i += 1
                    continue

                values = [v.strip() for v in row_line.strip("|").split("|")]

                if len(values) == len(json_headers):
                    row = {key: _convert_value(val) for key, val in zip(json_headers, values)}
                    results[rank]["rows"].append(row)

                i += 1

        i += 1

    # -----------------------------
    # Write to dict
    # -----------------------------
    output_dict = {"ranks": results}
    print(output_dict)
    return output_dict


class MoriBenchmark:
    def __init__(self, phdl, mori_dict, gpu_type):
        self.phdl = phdl
        self.host_list = phdl.host_list
        self.nnodes = len(self.host_list)
        self.mori_dict = mori_dict
        self.master_addr = self.mori_dict['master_addr']
        self.master_port = self.mori_dict['master_port']
        self.container_image = self.mori_dict['container_image']
        self.container_name = self.mori_dict['container_name']
        self.oob_port = self.mori_dict['oob_port']
        self.more_device_list = self.mori_dict['mori_device_list']
        self.gpu_type = gpu_type
        self.torchlib_dir = self.mori_dict['torchlib_dir']
        self.mori_dir = self.mori_dict['mori_dir']
        self.mori_device_list = self.mori_dict['mori_device_list']
        self.nic_type = self.mori_dict['nic_type']
        self.log_dir = self.mori_dict['log_dir']
        self.expected_results_dict = self.mori_dict['expected_results']

    def create_env_script(
        self,
    ):
        cmd = f'''docker exec {self.container_name} /bin/bash -c "echo '
              export PYTHONPATH={self.mori_dir}:$PYTHONPATH
              export LD_LIBRARY_PATH={self.torchlib_dir}:$LD_LIBRARY_PATH
              export NCCL_SOCKET_IFNAME={self.oob_port}
              export GLOO_SOCKET_IFNAME={self.oob_port}
              export GLOO_TCP_IFNAME={self.oob_port}
              export GAI_PREFER_IPV4=1
              export MORI_RDMA_DEVICES={self.mori_device_list}
              ' > /tmp/mori_env_script.sh"
              '''
        formatted_cmd = textwrap_for_cmd(cmd)
        print(f'%%%%%%% formatted_cmd = {formatted_cmd}')
        self.phdl.exec(formatted_cmd)
        cmd = f'''docker exec {self.container_name} /bin/bash -c "
              mkdir -p {self.log_dir}"'''
        self.phdl.exec(formatted_cmd)

    def exec_nic_setup_scripts(
        self,
    ):
        # This is a temporary hack needed for broadcom nics to work within containers ..
        if re.search('broadcom|thor', self.nic_type, re.I):
            # override the gid_index to 3 for broadcom
            self.nccl_ib_gid_index = 3
            cmd = f'docker exec {self.container_name} /bin/bash -c "sudo \
                    cp /usr/lib/x86_64-linux-gnu/libibverbs/libbnxt_re-rdmav34.so.host \
                    /usr/lib/x86_64-linux-gnu/libibverbs/libbnxt_re-rdmav34.so;" '
            pout_dict = self.phdl.exec(cmd)
            for node in pout_dict.keys():
                if not re.search('hca_id:\s+bnxt_', out_dict[node], re.I):
                    print(pout_dict[node])

    def install_packages(
        self,
    ):
        cmd = f'''docker exec {self.container_name} /bin/bash -c "
              pip3 install prettytable
              " '''
        formatted_cmd = textwrap_for_cmd(cmd)
        self.phdl.exec(formatted_cmd)

    def check_ibv_devices(
        self,
    ):
        cmd = f'''docker exec {self.container_name} /bin/bash -c "ibv_devinfo" '''
        out_dict = self.phdl.exec(cmd)
        for node in out_dict.keys():
            dev_list = self.mori_device_list.split(',')
            for dev_nam in dev_list:
                if not re.search(f'{dev_nam}', out_dict[node], re.I):
                    fail_test(
                        f'ERROR - MORI device {dev_nam} not showing up under container \
                            {self.container_name} on node {node}'
                    )

    def run_mori_torch_io_test(
        self,
        op_type='read',
        enable_sess=True,
        buffer_size=32768,
        transfer_batch_size=128,
        no_of_qp_per_transfer=1,
        no_of_initiators=8,
        no_of_targets=8,
    ):
        """
        Run MORI Torch-based IO benchmark across multiple nodes using torchrun,
        collect performance results, parse them, and validate against expected
        bandwidth and latency thresholds.

        This test:
        - Launches one torchrun process per node (inside a container)
        - Runs a distributed IO benchmark
        - Parses per-rank performance tables
        - Verifies bandwidth and latency against expected baselines

        Args:
        op_type (str): IO operation type ('read' or 'write'), used to select
                       expected results.
        enable_sess (bool): Enable MORI session mode if True.
        buffer_size (int): Size of the IO buffer in bytes.
        transfer_batch_size (int): Number of transfers batched together.
        no_of_qp_per_transfer (int): Number of Queue Pairs per transfer.
        no_of_initiators (int): Number of initiator devices.
        no_of_targets (int): Number of target devices.
        """
        cmd_list = []

        # ------------------------------------------------------------------
        # Construct and launch one torchrun command per node
        # ------------------------------------------------------------------
        for i in range(0, int(self.nnodes)):
            # Build command-line options for the MORI benchmark
            # These options control IO batching, buffer sizing, and device topology
            cmd_opts = f'--enable-batch-transfer --buffer-size {buffer_size} '
            cmd_opts = cmd_opts + f' --transfer-batch-size {transfer_batch_size}'
            cmd_opts = cmd_opts + f' --num-qp-per-transfer {no_of_qp_per_transfer}'
            cmd_opts = cmd_opts + f' --num-initiator-dev {no_of_initiators}'
            cmd_opts = cmd_opts + f' --num-target-dev {no_of_targets}'
            if enable_sess:
                cmd_opts = cmd_opts + ' --enable-sess'

            # ------------------------------------------------------------------
            # Compose docker + torchrun command
            #
            # Key details:
            # - One torchrun process per node
            # - torchrun coordinates across NNODES
            # - NODE_RANK determines the rank of the node
            # - Output is redirected to /tmp/torch_cmd.log
            # - Command runs in background (nohup + &)
            # ------------------------------------------------------------------
            cmd = f'''docker exec {self.container_name} /bin/bash -c  " \
                    source /tmp/mori_env_script.sh && \
                    cd {self.mori_dir} && \
                    export NNODES={self.nnodes}
                    export NODE_RANK={i}
                    nohup torchrun --nnodes={self.nnodes} --node_rank={i} --nproc_per_node=1 \
                    --master_addr={self.master_addr} \
                    --master_port={self.master_port} \
                    {self.mori_dir}/tests/python/io/benchmark.py --host={self.host_list[i]} \
                    --all {cmd_opts} > /tmp/torch_cmd.log 2>&1 &"'''
            formatted_cmd = textwrap_for_cmd(cmd)
            cmd_list.append(formatted_cmd)
        # ------------------------------------------------------------------
        # Execute all launch commands in parallel (one per node)
        # ------------------------------------------------------------------
        out_dict = self.phdl.exec_cmd_list(cmd_list)
        time.sleep(20)
        # ------------------------------------------------------------------
        # Collect benchmark output from master node log
        # ------------------------------------------------------------------
        cmd = f'''docker exec {self.container_name} /bin/bash -c  "cat /tmp/torch_cmd.log"'''
        out_dict = self.phdl.exec(cmd)
        script_out = out_dict[self.master_addr]
        if not re.search('Max BW', script_out, re.I):
            fail_test('MORI benchmark test did not succeed, no Bandwidth numbers seen')
        # ------------------------------------------------------------------
        # Parse benchmark output into structured per-rank results
        #
        # Expected format:
        # {
        #   "ranks": {
        #     rank_id: {
        #       "rows": [ { MsgSize_B, Avg_BW_GBps, Avg_Lat_us, ... }, ... ]
        #     }
        #   }
        # }
        # ------------------------------------------------------------------
        # act_res_dict = parse_pretty_table_to_dict( script_out )
        act_res_dict = parse_pretty_tables_multi_rank(script_out)
        exp_res_dict = self.expected_results_dict[op_type]
        m_key = str(buffer_size) + ',' + str(transfer_batch_size) + ',' + str(no_of_qp_per_transfer)
        # ------------------------------------------------------------------
        # Validate actual results against expected thresholds
        # ------------------------------------------------------------------
        for rank_no in act_res_dict['ranks'].keys():
            for row_dict in act_res_dict['ranks'][rank_no]['rows']:
                # Only validate if expected results exist for this configuration
                if m_key in exp_res_dict:
                    # Match by message size
                    for msg_size in exp_res_dict[m_key].keys():
                        exp_max_bw = exp_res_dict[m_key][msg_size]['max_bw']
                        exp_avg_lat = exp_res_dict[m_key][msg_size]['avg_lat']
                        if int(row_dict['MsgSize_B']) == int(msg_size):
                            # Validate bandwidth: actual must be >= expected
                            if float(row_dict['Avg_BW_GBps']) < float(exp_max_bw):
                                fail_test(f'''BW is lower than expected for \
                                      rank {rank_no}, Msg size {msg_size}, \
                                      actual BW {row_dict['Avg_BW_GBps']}, \
                                      expected BW {exp_max_bw}, \
                                      buffer_size,transfer_batch_size,no_of_qp_per_transfer = \
                                      {m_key}''')
                            # Validate latency: actual must be <= expected
                            if float(row_dict['Avg_Lat_us']) > float(exp_avg_lat):
                                fail_test(f'''Latency is higher than expected for \
                                      rank {rank_no}, Msg size {msg_size}, \
                                      actual Avg Lat {row_dict['Avg_Lat_us']}, \
                                      expected Avg Lat {exp_avg_lat}, \
                                      buffer_size,transfer_batch_size,no_of_qp_per_transfer = \
                                      {m_key}''')
