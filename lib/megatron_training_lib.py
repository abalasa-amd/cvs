
import sys
import os
import re
import time

import globals
log = globals.log

from utils_lib import *
from verify_lib import *
import linux_utils

# Sample Training config dict. Actual values fed to PyTest script via input json file
#"config":
#{
#        "container_image": "rocm/megatron-lm:v25.5_py312",
#        "container_name": "megatron_llama3.1_8b",
#        "nnodes": "4",
#        "master_address": "10.2.96.21",
#        "training_iterations": "10",
#        "nic_type": "thor2",
#        "nccl_ib_hca_list": "bnxt_re0,bnxt_re1,bnxt_re2,bnxt_re3,bnxt_re4,bnxt_re5,bnxt_re6,bnxt_re7",
#        "nccl_socket_ifname": "ens51f1np1",
#        "gloo_socket_ifname": "ens51f1np1",
#        "nccl_ib_gid_index": "3",
#        "nccl_debug": "ERROR",
#        "shm_size": "128G",
#        "data_cache_dir": "/home/venksrin/cache",
#        "mock_data": "True",
#        "dataset_source":
#        {
#        },
#        "container_config":
#        {
#            "device_list": [ "/dev/dri", "/dev/kfd", "/dev/infiniband" ],
#            "volume_dict":
#            {
#                "/home/venksrin": "/home/venksrin",
#                "/lib/libibverbs.d": "/lib/libibverbs.d",
#                "/tmp/TRAINING_LOGS": "/workspace/Megatron-LM/output",
#            }
#}



# Sample model params dict. Actual values fed to PyTest script via input json file
#"model_params":
#    {
#        "single_node":
#        {
#             'llama3_1_8b':
#             {
#                 'mi300':
#                 {
#                     'tokenizer_model': 'meta-llama/Llama-3.1-8B',
#                     'model_size': '8',
#                     'batch_size': '128',
#                     'micro_batch_size': '2',
#                     'sequence_length': '8192',
#                     'tensor_parallelism': '1',
#                     'pipeline_parallelism': '1',
#                     'recompute': '0',
#                     'fsdp': '0'
#                 },
#                 'mi325':
#                 {
#                     'tokenizer_model': 'meta-llama/Llama-3.1-8B',
#                     'model_size': '8',
#                     'batch_size': '128',
#                     'micro_batch_size': '2',
#                     'sequence_length': '8192',
#                     'tensor_parallelism': '1',
#                     'pipeline_parallelism': '1',
#                     'recompute': '0',
#                     'fsdp': '0'
#                 },
#            }
#      }
#}

# The batch size should be divisible by MBS and NNODES


training_err_dict = {
    'cache_err': 'Unable to save MockGPTDataset indexes because path_to_cache is None',
    'NCCL ERROR': 'NCCL ERROR|NCCL timeout',
    'GPU HW ERROR': 'HW Exception by GPU|GPU Hang|Uncorrectable error|GPU Reset'
}

err_counters_pattern = 'err|retransmit|drop|discard|naks|invalid|oflow|out_of_buffer|reset|fail'

# Library for building Megatron training jobs ..

class MegatronLlamaTrainingJob():

    def __init__( self,  phdl, model_name,
        training_config_dict, model_params_dict,
        hf_token, gpu_type='mi300',
        tune_model_params=True, scripts_dir=os.path.expanduser("~") + '/SCRIPTS'  ):

        self.phdl                  = phdl
        self.host_list             = phdl.host_list
        self.model_name            = model_name
        self.hf_token              = hf_token
        self.gpu_type              = gpu_type

        # Sample training config and model params dict saved above
        self.training_config_dict  = training_config_dict
        self.model_params_dict     = model_params_dict
        self.iterations            = training_config_dict['training_iterations'] 
        self.tune_model_params        = tune_model_params

        self.scripts_dir           = scripts_dir

        self.job_cmd               = ''
        self.job_cmd_list          = []
        self.training_result_dict  = {}
        print(self.gpu_type)

        # Intialize cluster stats dicts ..
        self.rdma_stats_dict_before      = {}
        self.ethtool_stats_dict_before   = {}
        self.rdma_stats_dict_after       = {}
        self.ethtool_stats_dict_after    = {}
        self.training_start_time         = self.phdl.exec('date')
        self.training_end_time           = None


        # Training configs - let us set defaults if not defined in input json file
        self.home_dir                   = os.path.expanduser("~")
        tdict                      = training_config_dict
        tdict.setdefault( 'container_image', 'rocm/megatron-lm:v25.5_py312' )
        tdict.setdefault( 'container_name', 'megatron_llama3.1_8b' )
        tdict.setdefault( 'distributed_training', True )
        tdict.setdefault( 'training_iterations', 10 )
        tdict.setdefault( 'nnodes', 2 )
        tdict.setdefault( 'nic_type', 'thor2' )
        tdict.setdefault( 'nccl_ib_hca_list', 'bnxt_re0,bnxt_re1,bnxt_re2,bnxt_re3,bnxt_re4,bnxt_re5,bnxt_re6,bnxt_re7')
        tdict.setdefault( 'nccl_ib_hca', 'bnxt_re0,bnxt_re1,bnxt_re2,bnxt_re3,bnxt_re4,bnxt_re5,bnxt_re6,bnxt_re7')
        tdict.setdefault( 'nccl_socket_ifname', 'ens51f1np1' )
        tdict.setdefault( 'gloo_socket_ifname', 'ens51f1np1' )
        tdict.setdefault( 'nccl_ib_gid_index', '3' )
        tdict.setdefault( 'nccl_debug', 'ERROR' )
        tdict.setdefault( 'data_cache_dir', f'{self.home_dir}/cache' )
        tdict.setdefault( 'log_dir', f'{self.home_dir}/LOG_DIR' )
        tdict.setdefault( 'master_address', '127.0.0.1' )

        self.container_image       = tdict['container_image']
        self.container_name        = tdict['container_name']
        if tdict['distributed_training'] == "True":
            self.distributed_training  = True
        else:
            self.distributed_training  = False
        self.iterations            = tdict['training_iterations']
        self.nnodes                = tdict['nnodes']
        self.nic_type              = tdict['nic_type']
        self.nccl_ib_hca_list      = tdict['nccl_ib_hca_list']
        self.nccl_ib_hca           = tdict['nccl_ib_hca']
        self.nccl_socket_ifname    = tdict['nccl_socket_ifname']
        self.gloo_socket_ifname    = tdict['gloo_socket_ifname']
        self.nccl_ib_gid_index     = tdict['nccl_ib_gid_index']
        self.nccl_debug            = tdict['nccl_debug']
        self.data_cache_dir        = tdict['data_cache_dir']
        self.log_dir               = tdict['log_dir']
        self.master_address        = tdict['master_address']


        # Get the model parameters dict
        print('^^^^')
        print(self.model_params_dict)
        print(self.model_name)
        print(self.gpu_type)
        print('^^^^')
        if not self.distributed_training:
            pdict = self.model_params_dict['single_node'][self.model_name][self.gpu_type]
            self.expected_result_dict  = \
               self.model_params_dict['single_node'][self.model_name][self.gpu_type]['result_dict']
        else:
            pdict = self.model_params_dict['multi_node'][self.model_name][self.gpu_type]
            self.expected_result_dict  = \
               self.model_params_dict['multi_node'][self.model_name][self.gpu_type]['result_dict']


        # Training configs - let us set defaults if not defined in input json file
        # Model Params - Let us set defaults if params not defined in input json file
        pdict.setdefault( 'tokenizer_model', 'meta-llama/Llama-3.1-70B')
        pdict.setdefault( 'model_size', 70)
        pdict.setdefault( 'sequence_length', '8192')
        pdict.setdefault( 'batch_size', '128')
        pdict.setdefault( 'micro_batch_size', '2')
        pdict.setdefault( 'fsdp', '0')
        pdict.setdefault( 'tensor_parallelism', '1')
        pdict.setdefault( 'pipeline_parallelism', '1')
        pdict.setdefault( 'recompute', '0')
        pdict.setdefault( 'precision', 'TE_FP8')

        self.tokenizer_model       = pdict['tokenizer_model']
        self.model_size            = pdict['model_size']
        self.sequence_length       = pdict['sequence_length']
        self.batch_size            = pdict['batch_size']
        self.micro_batch_size      = pdict['micro_batch_size']
        self.fsdp                  = pdict['fsdp']
        self.tensor_parallelism    = pdict['tensor_parallelism']
        self.pipeline_parallelism  = pdict['pipeline_parallelism']
        self.recompute             = pdict['recompute']
        self.precision             = pdict['precision']

        if re.search( 'llama-3', self.tokenizer_model, re.I ):
            self.training_script = '/workspace/Megatron-LM/examples/llama/train_llama3.sh'
        elif re.search( 'llama-2', self.tokenizer_model, re.I ):
            self.training_script = '/workspace/Megatron-LM/examples/llama/train_llama2.sh'

        # Remove and recreate the scripts dir
        self.phdl.exec(f'rm -rf {self.scripts_dir}')
        time.sleep(2)
        self.phdl.exec(f'mkdir {self.scripts_dir}')
        time.sleep(2)
        self.phdl.exec(f'sudo chmod 777 {self.scripts_dir}')

        # Let us override some of the params based on number of nodes and platform
        # if override flag set ..
        if self.tune_model_params:
            #Assuming the training json configs were built with 4 nodes = 32 gpus
            if int(self.batch_size) > 32:
                if int(self.batch_size)%32 == 0:
                    per_gpu_batch_size = int(self.batch_size)/32
                    self.batch_size = per_gpu_batch_size * int(self.nnodes) * 8



    def run_pretraining_tasks(self, ):
        if self.distributed_training is True:
            self.rdma_stats_dict_before = linux_utils.get_rdma_stats_dict(self.phdl)
            self.ethtool_stats_dict_before = linux_utils.get_nic_ethtool_stats_dict(self.phdl)
   


    def exec_nic_setup_scripts( self, ):
        # Run all your backend NIC related bringups for containers here .. 
        if self.distributed_training is True:
            # This is a temporary hack needed for broadcom nics to work within containers ..
            if re.search( 'broadcom|thor', self.nic_type, re.I ):
                # override the gid_index to 3 for broadcom
                self.nccl_ib_gid_index=3
                out_dict = self.phdl.exec(f'docker exec {self.container_name} /bin/bash -c "sudo \
                    cp /usr/lib/x86_64-linux-gnu/libibverbs/libbnxt_re-rdmav34.so.host \
                    /usr/lib/x86_64-linux-gnu/libibverbs/libbnxt_re-rdmav34.so; \
                    sleep 2;ibv_devinfo;sleep 2;"')
                for node in out_dict.keys():
                    if not re.search( 'hca_id:\s+bnxt_', out_dict[node], re.I ):
                        print(out_dict[node])
                        fail_test(f'Broadcom libbnxt rdma driver is not properly copied on node {node}')



    def build_training_job_cmd( self, ):
        # Construct the main megatron training command
        # Compute the batch size and mini batch size based on the cluster size
        # Add NIC and Socket details for distributed training ..
        cmd = ''

        #cmd = f'docker exec {self.container_name} /bin/bash -c """'
       
        cmd = cmd + f'cd /workspace/Megatron-LM; export MOCK_DATA=1; ' + \
              f'export IMAGE={self.container_image}; ' + \
              f'export HF_TOKEN="{self.hf_token}"; ' + \
              f'export DATA_CACHE_PATH={self.data_cache_dir}; ' + \
              f'export TOKENIZER_MODEL={self.tokenizer_model}; ' + \
              f'export LD_LIBRARY_PATH=/usr/local/lib/:/opt/rocm/lib:$LD_LIBRARY_PATH; ' + \
              f'export LOG_DIR={self.log_dir}; ' + \
              f'export EXP_NAME={self.model_name}; '


        #if self.distributed_training is True:
        # Add the backend network related environment variables ..
        cmd = cmd + f'export NCCL_IB_HCA_LIST={self.nccl_ib_hca_list}; ' + \
                  f'export NCCL_IB_HCA={self.nccl_ib_hca_list}; ' + \
                  f'export NCCL_SOCKET_IFNAME={self.nccl_socket_ifname}; ' + \
                  f'export GLOO_SOCKET_IFNAME={self.gloo_socket_ifname}; ' + \
                  f'export NCCL_DEBUG={self.nccl_debug}; ' + \
                  f'export NCCL_IB_GID_INDEX={self.nccl_ib_gid_index}; '

        if self.distributed_training is True:
            # Build CMD List as every node has different node rank
            cmd = cmd + f'cd /workspace/Megatron-LM; RECOMPUTE={self.recompute} ' + \
                      f'SEQ_LENGTH={self.sequence_length} ' + \
                      f'MBS={self.micro_batch_size} BS={self.batch_size} ' + \
                      f'TP={self.tensor_parallelism} ' + \
                      f'PP={self.pipeline_parallelism} FSDP={self.fsdp} ' + \
                      f'MODEL_SIZE={self.model_size} TOTAL_ITERS={self.iterations} '
            if self.precision == "TE_BF16":
                cmd = cmd + 'TE_FP8=0 TE_BF16=1 '
            elif self.precision == "TE_F16":
                cmd = cmd + 'TE_FP8=0 TE_F16=1 '
            else:
                cmd = cmd + 'TE_FP8=1 '

            cmd = cmd + f'MASTER_ADDR={self.master_address} NNODES={self.nnodes} '

            for i in range(0,int(self.nnodes)):
                full_cmd = cmd + f'NODE_RANK={i} nohup bash {self.training_script} &'
                script_cmd = f'echo "{full_cmd}" > {self.scripts_dir}/distributed_wrapper_script_{i}.sh;chmod 777 {self.scripts_dir}/distributed_wrapper_script_{i}.sh'
                self.job_cmd_list.append(script_cmd)
        else:
            # Single node training case, run same cmd on all nodes.
            cmd = cmd + f'cd /workspace/Megatron-LM; RECOMPUTE={self.recompute} ' + \
                      f'SEQ_LENGTH={self.sequence_length} ' + \
                      f'MBS={self.micro_batch_size} BS={self.batch_size} ' + \
                      f'TP={self.tensor_parallelism} ' + \
                      f'PP={self.pipeline_parallelism} FSDP={self.fsdp} ' + \
                      f'MODEL_SIZE={self.model_size} TOTAL_ITERS={self.iterations} '
            if self.precision == "TE_BF16":
                cmd = cmd + 'TE_FP8=0 TE_BF16=1 '
            elif self.precision == "TE_F16":
                cmd = cmd + 'TE_FP8=0 TE_F16=1 '
            else:
                cmd = cmd + 'TE_FP8=1 '
            self.job_cmd = cmd + f'nohup bash {self.training_script} &'


    def start_training_job( self, timeout=500 ):
        print('start training job')
        print(self.job_cmd_list)
        print(self.job_cmd)
        if self.distributed_training:
            self.exec_nic_setup_scripts()
            # Following creates the training script
            out_dict = self.phdl.exec_cmd_list( self.job_cmd_list )
            # Build the docker cmd list to run on each node ..
            docker_cmd_list = []
            for i in range(0, int(self.nnodes)):
                cmd = f'docker exec {self.container_name} /bin/bash -c "nohup \
                      {self.scripts_dir}/distributed_wrapper_script_{i}.sh > \
                      {self.home_dir}/training_logs 2>&1 &"'
                docker_cmd_list.append(cmd)
            out_dict = self.phdl.exec_cmd_list(docker_cmd_list)
        else:
            out_dict = self.phdl.exec( f'echo "{self.job_cmd}" > \
               {self.scripts_dir}/single_node_wrapper_script.sh; \
               chmod 777 {self.scripts_dir}/single_node_wrapper_script.sh' )
            out_dict = self.phdl.exec( f'docker exec {self.container_name} \
               /bin/bash -c "nohup {self.home_dir}/single_node_wrapper_script.sh > \
               {self.home_dir}/training_logs 2>&1 &"' )
            out_dict = self.phdl.exec( f'sudo chmod 777 {self.home_dir}/training_logs' )
        time.sleep(50)



    def get_training_results_dict(self, ):
        training_result_dict = {}
        last_node = self.host_list[len(self.host_list) -1]
        out_dict = self.phdl.exec(f'cat {self.home_dir}/training_logs')
        output = out_dict[last_node]
        training_result_dict['throughput_per_gpu'] = re.findall( \
            'throughput per GPU:\s+([0-9\.]+)', output, re.I)
        training_result_dict['tokens_per_gpu'] = re.findall( \
            'tokens\/GPU\/s: ([0-9]+)', output, re.I )
        training_result_dict['mem_usage'] = re.findall( \
            'mem usages:\s+([0-9\.]+)', output, re.I )
        training_result_dict['elapsed_time_per_iteration'] = re.findall( \
            'elapsed time per iteration: \s+([0-9\.]+)', output, re.I)
        print(training_result_dict)
        return training_result_dict


    def scan_for_training_errors(self, ):
        print('Scan for training errors')
        training_pass=True
        last_node = self.host_list[len(self.host_list) -1]        
        out_dict = self.phdl.exec(f'sudo cat {self.home_dir}/training_logs')
        output = out_dict[last_node] 
        for err_key in training_err_dict:
            if re.search( f'{training_err_dict[err_key]}', output ):
                fail_test(f'ERROR {training_err_dict[err_key]} seen in training logs ..')
                log.error(f'Aborting training log polling')
                training_pass=False
        return training_pass
          
  
    def poll_for_training_completion( self, ):
        print('Poll for training completion ..')
        time.sleep(60)
        last_node = self.host_list[len(self.host_list) -1]

        for i in range(1,30):
            print(f'Starting Iteration {i}')
            if not self.scan_for_training_errors():
                fail_test('Failures seen in training logs, Aborting!!!')
                return
            out_dict = self.phdl.exec(f'sudo cat {self.home_dir}/training_logs')
            output = out_dict[last_node]
            
            if not re.search( 'throughput per GPU:|tokens\/GPU\/s\s+[0-9]+', \
                output, re.I ):
                print('Training still in progress')
                time.sleep(30)
            else:
                if re.search( 'throughput per GPU:\s+[NaN|Inf]', output, re.I ) or \
                       re.search( 'tokens\/GPU\/s:\s+[NaN|Inf]', output, re.I ) or \
                       re.search( 'mem usages:\s+[NaN|Inf]', output, re.I ):
                    fail_test(f'ERROR - NaN or Inf values seen in training results {output}')
                    return
                else:
                    self.training_result_dict = self.get_training_results_dict()
                    print('Completed Training, returning !!!')
                    return
            # Wait 60 secs between every iteration
            time.sleep(60)



    def verify_training_results( self, ):
        # across nodes what numbers we are getting - median variance, per iteration variance.
        # Network errors
        self.training_end_time = self.phdl.exec('date')

        for result_key in self.training_result_dict.keys():
            for result_list in self.training_result_dict[result_key]:
                for result_val in result_list:
                    if re.search( 'nan|inf', result_val):
                        fail_test(f'Failures seen in training_result dict for {result_key}, numbers are either NaN or Inf - f{result_val}')

        # Check if RDMA and Ethtool stats have errors ..
        if self.distributed_training is True:
            self.rdma_stats_dict_after = linux_utils.get_rdma_stats_dict(self.phdl)
            self.ethtool_stats_dict_after = linux_utils.get_nic_ethtool_stats_dict(self.phdl)
            for node in self.rdma_stats_dict_after.keys():
                for counter_nam in self.rdma_stats_dict_after[node]:
                    if re.search( f'{err_counters_pattern}', counter_nam, re.I ):
                        if int(self.rdma_stats_dict_after[node][counter_nam]) >  \
                              int(self.rdma_stats_dict_before[node][counter_nam]):
                            fail_test(f'Error counter {counter_nam} has gone up after training on node {node} \
                              Before = {self.rdma_stats_dict_before[node][counter_nam]}, \
                              After = {self.rdma_stats_dict_after[node][counter_nam]}')
            for node in self.ethtool_stats_dict_after.keys():
                for counter_nam in self.ethtool_stats_dict_after[node]:
                    if re.search( f'{err_counters_pattern}', counter_nam, re.I ):
                        if int(self.ethtool_stats_dict_after[node][counter_nam]) > \
                              int(self.ethtool_stats_dict_before[node][counter_nam]):
                            fail_test(f'Error counter {counter_nam} has gone up after training on node {node} \
                              Before = {self.ethtool_stats_dict_before[node][counter_nam]}, \
                              After = {self.ethtool_stats_dict_after[node][counter_nam]}')

        # Scan Dmesg for errors ..
        verify_dmesg_for_errors( self.phdl, self.training_start_time, self.training_end_time )

        # Compare perf expected numbers from input JSON file ..
        for result_key in self.expected_result_dict.keys():
            if result_key in self.training_result_dict:
                # check if all nodes have met the expected perf numbers
                for actual_perf in self.training_result_dict[result_key]:
                    if float(self.expected_result_dict[result_key]) < \
                          float(actual_perf):
                        fail_test(f'The Training performance numbers are below expected numbers for \
                           {result_key}, expected = {self.expected_result_dict[result_key]}, \
                           actual = {actual_perf}' )
            else:
                log.warn(f'Perf result key {result_key} not provided in input JSON file, so will not be checked')

