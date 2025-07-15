import re
import os
import sys
import parallel_ssh_lib

from utils_lib import *


def get_rocm_smi_dict( phdl ):
    rocm_smi_dict = convert_phdl_json_to_dict( phdl.exec('sudo rocm-smi -a --json') )
    return rocm_smi_dict


def get_gpu_partition_dict( phdl ):
    amd_part_dict = convert_phdl_json_to_dict( phdl.exec('sudo amd-smi partition --json') )
    return amd_part_dict


def get_gpu_process_dict( phdl ):
    amd_proc_dict = convert_phdl_json_to_dict( phdl.exec('sudo amd-smi process --json') )
    return amd_proc_dict


def get_amd_smi_metric_dict( phdl ):
    amd_metric_dict = convert_phdl_json_to_dict( phdl.exec('sudo amd-smi metric --json') )
    return amd_metric_dict


def get_amd_smi_fw_dict( phdl ):
    firmware_dict = convert_phdl_json_to_dict( phdl.exec('sudo amd-smi firmware --json') )
    return firmware_dict


def get_gpu_mem_use_dict( phdl ):
    d_dict = convert_phdl_json_to_dict( phdl.exec('sudo rocm-smi --showmemuse --json'))
    return d_dict

def get_gpu_use_dict( phdl ):
    d_dict = convert_phdl_json_to_dict( phdl.exec('sudo rocm-smi --showuse --json'))
    return d_dict

def get_gpu_metrics_dict( phdl ):
    d_dict = convert_phdl_json_to_dict( phdl.exec('sudo rocm-smi --showmetric --json'))
    return d_dict


def get_gpu_fw_dict( phdl ):
    d_dict = convert_phdl_json_to_dict( phdl.exec('sudo rocm-smi --showfwinfo --json'))
    return d_dict

def get_gpu_pcie_bus_dict( phdl ):
    d_dict = convert_phdl_json_to_dict( phdl.exec('sudo rocm-smi --showbus --json'))
    return d_dict

def get_gpu_model_dict( phdl ):
    d_dict = convert_phdl_json_to_dict( phdl.exec('sudo rocm-smi --showproductname --json'))
    return d_dict

def get_gpu_temp_dict( phdl ):
    d_dict = convert_phdl_json_to_dict( phdl.exec('sudo rocm-smi --showtemp --json'))
    return d_dict




