import pytest

import re
import sys
import os
import sys
import time
import json
import logging
import time

sys.path.insert( 0, './lib' )

from parallel_ssh_lib import *
from utils_lib import *
import docker_lib
import jax_training_lib

import globals
log = globals.log


# Importing additional cmd line args to script ..
@pytest.fixture(scope="module")
def cluster_file(pytestconfig):
    return pytestconfig.getoption("cluster_file")


@pytest.fixture(scope="module")
def training_config_file(pytestconfig):
    return pytestconfig.getoption("config_file")


# Importing the cluster and cofig files to script to access node, switch, test config params
@pytest.fixture(scope="module")
def  cluster_dict(cluster_file):
     with open(cluster_file) as json_file:
        cluster_dict = json.load(json_file)
     log.info(cluster_dict)
     return cluster_dict


@pytest.fixture(scope="module")
def  training_dict(training_config_file):
     with open(training_config_file) as json_file:
        training_dict_t = json.load(json_file)
     training_dict = training_dict_t['config']
     return training_dict


@pytest.fixture(scope="module")
def  model_params_dict(training_config_file):
     with open(training_config_file) as json_file:
        training_dict_t = json.load(json_file)
     model_params_dict = training_dict_t['model_params']
     log.info(model_params_dict)
     return model_params_dict


@pytest.fixture(scope="module")
def  hf_token(training_config_file):
     with open(training_config_file) as json_file:
        training_dict_t = json.load(json_file)
     hf_token_file = training_dict_t['config']['hf_token_file']
     try:
         with open(hf_token_file, 'r') as fp:
             hf_token = fp.read().rstrip("\n")
     except FileNotFoundError:
         print(f"Error: The file '{hf_token_file}' was not found.")
     except Exception as e:
         print(f"An error occurred: {e}")
     return hf_token




# Batch size and Micro Batch size are going to vary based on number of GPUs used for training and the size of the model


# Create connection to DUT, MTPs, Switches and export for later use ..
@pytest.fixture(scope="module")
def  phdl(cluster_dict):
     nhdl_dict = {}
     print(cluster_dict)
     node_list = list(cluster_dict['node_dict'].keys())
     phdl = Pssh( log, node_list, user=cluster_dict['username'], pkey=cluster_dict['priv_key_file'] )
     return phdl


@pytest.fixture(scope="module")
def  gpu_type(cluster_dict):
     gpu_type=cluster_dict['gpu_type']
     return gpu_type




def test_cleanup_stale_containers( phdl, training_dict ):
    container_name = training_dict['container_name']
    docker_lib.kill_docker_container( phdl, container_name )
    docker_lib.delete_all_containers_and_volumes( phdl )




def test_launch_jax_containers(phdl, training_dict ):
    log.info('Testcase launch JAX containers')
    globals.error_list = []
    container_name = training_dict['container_name']
    # Launch the containers ..
    docker_lib.launch_docker_container( phdl, container_name,
          training_dict['container_image'], 
          training_dict['container_config']['device_list'],
          training_dict['container_config']['volume_dict'],
          training_dict['container_config']['env_dict'],
          shm_size='256G', timeout=60*20 )
    # ADD verifications ..
    update_test_result()



    

def test_llama_3_1_fp8_single_node(phdl, gpu_type, training_dict, model_params_dict, hf_token ):
    globals.error_list = []
    jx_obj = jax_training_lib.JaxTrainingJob( phdl,
           'llama3.1-405b', training_dict, model_params_dict,
           hf_token, gpu_type, tune_model_params=False )
    jx_obj.exec_nic_setup_scripts()
    jx_obj.build_training_job_cmd()
    jx_obj.start_training_job()
    jx_obj.poll_for_training_completion()
    jx_obj.verify_training_results()
    update_test_result()

 
