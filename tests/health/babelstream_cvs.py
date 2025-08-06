import pytest

import re
import sys
import os
import sys
import time
import json
import logging
import time

import netmiko
from netmiko import ConnectHandler
from netmiko import redispatch

sys.path.insert( 0, './lib' )
from parallel_ssh_lib import *
from utils_lib import *

import globals

log = globals.log


# Importing additional cmd line args to script ..
@pytest.fixture(scope="module")
def cluster_file(pytestconfig):
    return pytestconfig.getoption("cluster_file")


@pytest.fixture(scope="module")
def config_file(pytestconfig):
    return pytestconfig.getoption("config_file")


# Importing the cluster and cofig files to script to access node, switch, test config params
@pytest.fixture(scope="module")
def  cluster_dict(cluster_file):
     with open(cluster_file) as json_file:
        cluster_dict = json.load(json_file)
     log.info(cluster_dict)
     return cluster_dict

@pytest.fixture(scope="module")
def  config_dict(config_file):
     with open(config_file) as json_file:
        config_dict_t = json.load(json_file)
     config_dict = config_dict_t['babelstream']
     log.info(config_dict)
     return config_dict



def parse_babelstream_results( out_dict, exp_dict ):
    for node in out_dict.keys():
        copy_list = re.findall( 'Copy\s+([0-9\.]+)\s+[0-9\.]+\s+[0-9\.]+\s+', out_dict[node] )
        for copy_val in copy_list:
            if float(copy_val) < float(exp_dict['copy']):
                fail_test(f"Copy value {copy_val} less than expected {exp_dict['copy']} on node {node}")
        add_list = re.findall( 'Add\s+([0-9\.]+)\s+[0-9\.]+\s+[0-9\.]+\s+', out_dict[node] )
        for add_val in add_list:
            if float(add_val) < float(exp_dict['add']):
                fail_test(f"Add value {add_val} less than expected {exp_dict['add']} on node {node}")
        mul_list = re.findall( 'Mul\s+([0-9\.]+)\s+[0-9\.]+\s+[0-9\.]+\s+', out_dict[node] )
        for mul_val in mul_list:
            if float(mul_val) < float(exp_dict['mul']):
                fail_test(f"Mul value {mul_val} less than expected {exp_dict['mul']} on node {node}")
        triad_list = re.findall( 'Triad\s+([0-9\.]+)\s+[0-9\.]+\s+[0-9\.]+\s+', out_dict[node] )
        for triad_val in triad_list:
            if float(triad_val) < float(exp_dict['triad']):
                fail_test(f"Triad value {triad_val} less than expected {exp_dict['triad']} on node {node}")
        dot_list = re.findall( 'Dot\s+([0-9\.]+)\s+[0-9\.]+\s+[0-9\.]+\s+', out_dict[node] )
        for dot_val in dot_list:
            if float(dot_val) < float(exp_dict['dot']):
                fail_test(f"Triad value {dot_val} less than expected {exp_dict['dot']} on node {node}")



        

# Create connection to DUT, Switches and export for later use ..
@pytest.fixture(scope="module")
def phdl(cluster_dict):
    print(cluster_dict)
    node_list = list(cluster_dict['node_dict'].keys())
    phdl = Pssh( log, node_list, user=cluster_dict['username'], pkey=cluster_dict['priv_key_file'] )
    return phdl


# Connect to first node to install packages in NFS mounted common directories
@pytest.fixture(scope="module")
def hdl(cluster_dict):
    node_list = list(cluster_dict['node_dict'].keys())
    hdl = ConnectHandler( ip=node_list[0], device_type='linux', username=cluster_dict['username'], \
        use_keys=True, key_file=cluster_dict['priv_key_file'] )
    return hdl


@pytest.mark.dependency(name="init")
def test_install_babelstream(hdl, phdl, config_dict ):
    globals.error_list = []
    log.info('Testcase install babelstream')
    path = config_dict['path']
    package_path = config_dict['package_path']
    git_url = config_dict['git_url']
    print(package_path)
    out = hdl.send_command(f'ls -l {path}')
    print(out)
    if re.search( 'No such file', out, re.I ):
        #out = hdl.send_command(f'cd {package_path};git clone {git_url};cd', delay_factor=10, expect_string='$|#')
        out_dict = phdl.exec(f'cd {package_path};git clone {git_url};cd')
        #out = hdl.send_command(f'cd {package_path}/BabelStream;cmake -Bbuild -H. -DMODEL=hip -DCMAKE_CXX_COMPILER=hipcc;cd', delay_factor=10, expect_string='$|#')
        out_dict = phdl.exec(f'cd {package_path}/BabelStream;cmake -Bbuild -H. -DMODEL=hip -DCMAKE_CXX_COMPILER=hipcc;cd')
        #out = hdl.send_command(f'cd {package_path}/BabelStream;cmake --build build;cd', delay_factor=10, expect_string='$|#')
        out_dict = phdl.exec(f'cd {package_path}/BabelStream;cmake --build build;cd')
        #out = hdl.send_command(f'ls -l {package_path}/BabelStream', expect_string='$|#')
        out_dict = phdl.exec(f'ls -l {package_path}/BabelStream')
        for node in out_dict.keys():
            if not re.search('hip-stream', out_dict[node], re.I ):
                fail_test('Installation of BabelStream failed, hip-stream file not found' )
        phdl.exec(f'export PATH={package_path}/BabelStream/build:$PATH')
    update_test_result()

 
 
@pytest.mark.dependency(depends=["init"])
def test_create_wrapper_script(hdl, config_dict ):
    globals.error_list = []
    log.info('Testcase create hip-stream wrapper-script')
    path = config_dict['path']
    out = hdl.send_command(f'cd {path};ls -l', expect_string='$|#')
    print(out)
    print(f"echo -e '#!/bin/bash\n{path}/hip-stream --device $OMPI_COMM_WORLD_RANK -n 50 -s 268435456' > {path}/wrapper.sh")
    out = hdl.send_command(f"echo -e '#!/bin/bash\\n{path}/hip-stream --device $OMPI_COMM_WORLD_RANK -n 50 -s 268435456' > {path}/wrapper.sh", expect_string='$|#')
    print(out)
    time.sleep(2)
    print(f'cat {path}/wrapper.sh')
    out = hdl.send_command(f'ls -l {path}/wrapper.sh', expect_string='$|#')
    print(out)
    if re.search('No such file', out, re.I ):
        fail_test('Creation of wrapper script failed, file not found or content missing' )
    out = hdl.send_command(f'chmod 755 {path}/wrapper.sh', expect_string='$|#')
    print(out)
    update_test_result()



@pytest.mark.dependency(depends=["init"])
def test_install_open_mpi(phdl, config_dict, ):
    globals.error_list = []
    log.info('Testcase install openmpi')
    path = config_dict['path']
    out_dict = phdl.exec(f'sudo apt update -y', timeout=200)
    out_dict = phdl.exec(f'sudo apt-get install -y openmpi-bin openmpi-common libopenmpi-dev', timeout=200)
    out_dict = phdl.exec('which mpiexec')
    for node in out_dict.keys():
        if not re.search( 'mpiexec', out_dict[node] ):
            fail_test(f'Open MPI installation failed on node {node}')
    update_test_result()



@pytest.mark.dependency(depends=["init"])
def test_run_babelstream(phdl, config_dict, ):
    globals.error_list = []
    log.info('Testcase Run babelstream on all 8 GPUs')
    path = config_dict['path']
    exp_dict = config_dict['results']
    out_dict = phdl.exec(f'cd {path};mpiexec -n 8 ./wrapper.sh', timeout=(60*2))
    for node in out_dict.keys():
        if re.search( 'fail|error|fatal|core|crash', out_dict[node], re.I ):
            fail_test(f'Failure error patterns seen in babelstream test on node {node}')
        if not re.search( 'Triad', out_dict[node], re.I ):
            fail_test(f'Expected performance number outputs not printed in babelstream out on node {node} - Test Failed')
    parse_babelstream_results( out_dict, exp_dict )
    update_test_result()
