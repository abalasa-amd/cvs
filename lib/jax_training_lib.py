
import sys
import os
import re
import time

import globals
log = globals.log

from utils_lib import *
from verify_lib import *
import linux_utils



training_err_dict = {
    'cache_err': 'Unable to save MockGPTDataset indexes because path_to_cache is None',
    'NCCL ERROR': 'NCCL ERROR|NCCL timeout|local work queue catastrophic error',
    'GPU HW ERROR': 'HW Exception by GPU|GPU Hang|Uncorrectable error|GPU Reset',
    'AssertionError': 'AssertionError'
}

err_counters_pattern = 'err|retransmit|drop|discard|naks|invalid|oflow|out_of_buffer|reset|fail'



def textwrap_for_yml( msg_string ):
    return ('\n'.join([m.lstrip() for m in msg_string.split('\n')]))


class JaxTrainingJob():

    def __init__( self,  phdl, model_name,
        training_config_dict, model_params_dict,
        hf_token, gpu_type='mi300',
        tune_model_params=True, scripts_dir=os.path.expanduser("~") + '/SCRIPTS'  ):

        self.phdl                        = phdl
        self.host_list                   = phdl.host_list
        self.model_name                  = model_name
        self.hf_token                    = hf_token
        self.gpu_type                    = gpu_type

        # Sample training config and model params dict saved above
        self.training_config_dict        = training_config_dict
        self.tc_dict                     = training_config_dict
        self.model_params_dict           = model_params_dict
        self.tune_model_params           = tune_model_params

        self.scripts_dir                 = scripts_dir

        self.job_cmd                     = ''
        self.job_cmd_list                = []
        self.training_result_dict        = {}
        print(self.gpu_type)

        # Intialize cluster stats dicts ..
        self.rdma_stats_dict_before      = {}
        self.ethtool_stats_dict_before   = {}
        self.rdma_stats_dict_after       = {}
        self.training_start_time         = self.phdl.exec('date')
        self.training_end_time           = None


        # Training configs - let us set defaults if not defined in input json file
        self.home_dir                   = os.path.expanduser("~")
        self.tc_dict.setdefault( 'container_image', 'rocm/jax-training:maxtext-v25.5' )
        self.tc_dict.setdefault( 'container_name', 'jax_container' )
        self.tc_dict.setdefault( 'distributed_training', True )
        self.tc_dict.setdefault( 'training_steps', 10 )
        self.tc_dict.setdefault( 'nnodes', 2 )
        self.tc_dict.setdefault( 'nic_type', 'thor2' )
        self.tc_dict.setdefault( 'nccl_ib_hca_list', 'rdma0,rdma1,rdma2,rdma3,rdma4,rdma5,rdma6,rdma7')
        self.tc_dict.setdefault( 'nccl_ib_hca', 'rdma0,rdma1,rdma2,rdma3,rdma4,rdma5,rdma6,rdma7')
        self.tc_dict.setdefault( 'nccl_socket_ifname', 'ens51f1np1' )
        self.tc_dict.setdefault( 'gloo_socket_ifname', 'ens51f1np1' )
        self.tc_dict.setdefault( 'nccl_ib_gid_index', '3' )
        self.tc_dict.setdefault( 'nccl_debug', 'ERROR' )
        self.tc_dict.setdefault( 'data_cache_dir', f'{self.home_dir}/cache' )
        self.tc_dict.setdefault( 'log_dir', f'{self.home_dir}/LOG_DIR' )
        self.tc_dict.setdefault( 'master_address', '127.0.0.1' )

        self.container_image       = self.tc_dict['container_image']
        self.container_name        = self.tc_dict['container_name']

        if self.tc_dict['distributed_training'] == "True":
            self.distributed_training  = True
        else:
            self.distributed_training  = False


        self.training_steps        = self.tc_dict['training_steps']
        self.nnodes                = self.tc_dict['nnodes']
        self.nic_type              = self.tc_dict['nic_type']
        self.nccl_ib_hca_list      = self.tc_dict['nccl_ib_hca_list']
        self.nccl_ib_hca           = self.tc_dict['nccl_ib_hca']
        self.nccl_socket_ifname    = self.tc_dict['nccl_socket_ifname']
        self.gloo_socket_ifname    = self.tc_dict['gloo_socket_ifname']
        self.nccl_ib_gid_index     = self.tc_dict['nccl_ib_gid_index']
        self.nccl_debug            = self.tc_dict['nccl_debug']
        self.data_cache_dir        = self.tc_dict['data_cache_dir']
        self.log_dir               = self.tc_dict['log_dir']
        self.coordinator_ip        = self.tc_dict['coordinator_ip']


        # Let us assume 1 training step can complete in 10 polling iterations
        self.training_poll_iterations = int(self.training_steps * 10)

        # Get the model parameters dict
        if not self.distributed_training:
            self.mp_dict = self.model_params_dict['single_node'][self.model_name][self.gpu_type]
            self.expected_result_dict  = \
               self.model_params_dict['single_node'][self.model_name][self.gpu_type]['result_dict']
        else:
            self.mp_dict = self.model_params_dict['multi_node'][self.model_name][self.gpu_type]
            self.expected_result_dict  = \
               self.model_params_dict['multi_node'][self.model_name][self.gpu_type]['result_dict']


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


    def launch_docker_container(self, container_name, image, device_list, volume_dict, env_dict ):
        docker_lib.launch_docker_container( self.phdl, container_name, image, 
           device_list, volume_dict, env_dict )


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

        cmd = f'''docker exec {self.container_name} /bin/bash -c "echo 'base_config: base.yml
                  run_name: {self.model_name}-job
                  hardware: gpu
                  steps: {self.training_config_dict['training_steps']}
                  model_name: {self.model_name}
                  enable_checkpointing: {self.training_config_dict['enable_checkpointing']}
                  attention: {self.mp_dict['attention']}
                  dcn_data_parallelism: {self.mp_dict['dcn_data_parallelism']}
                  dcn_fsdp_parallelism: {self.mp_dict['dcn_fsdp_parallelism']}
                  dcn_pipeline_parallelism: {self.mp_dict['dcn_pipeline_parallelism']}
                  dcn_tensor_parallelism: {self.mp_dict['dcn_tensor_parallelism']}
                  dcn_sequence_parallelism: {self.mp_dict['dcn_sequence_parallelism']}
                  ici_fsdp_parallelism: {self.mp_dict['ici_fsdp_parallelism']}
                  ici_data_parallelism: {self.mp_dict['ici_data_parallelism']}
                  ici_sequence_parallelism: {self.mp_dict['ici_sequence_parallelism']}
                  ici_tensor_parallelism: {self.mp_dict['ici_tensor_parallelism']}
                  ici_pipeline_parallelism: {self.mp_dict['ici_pipeline_parallelism']}
                  remat_policy: {self.mp_dict['remat_policy']}
                  use_iota_embed: {self.mp_dict['use_iota_embed']}
                  scan_layers: {self.mp_dict['scan_layers']}
                  dataset_type: {self.mp_dict['dataset_type']}
                  hf_path: {self.mp_dict['hf_path']}
                  hf_train_files: {self.mp_dict['hf_train_files']}
                  tokenizer_path: {self.mp_dict['tokenizer_path']}
                  async_checkpointing: {self.mp_dict['async_checkpointing']}
                  logits_dot_in_fp32: {self.mp_dict['logits_dot_in_fp32']}
                  megablox: {self.mp_dict['megablox']}
                  dtype: {self.mp_dict['dtype']}
                  quantization: {self.mp_dict['quantization']}
                  quantize_kvcache: {self.mp_dict['quantize_kvcache']}
                  kv_quant_axis: {self.mp_dict['kv_quant_axis']}
                  kv_quant_dtype: {self.mp_dict['kv_quant_dtype']}
                  weight_dtype: {self.mp_dict['weight_dtype']}
                  checkpoint_is_quantized: {self.mp_dict['checkpoint_is_quantized']}
                  per_device_batch_size: {self.mp_dict['per_device_batch_size']}
                  max_target_length: {self.mp_dict['max_target_length']}
                  skip_first_n_steps_for_profiler: {self.mp_dict['skip_first_n_steps_for_profiler']}' > /workspace/maxtext/MaxText/configs/training_config_for_jax.yml" '''
        formatted_cmd = textwrap_for_yml(cmd)
        self.phdl.exec(formatted_cmd)

        # Create the config yml file
        cmd = f'''docker exec {self.container_name} /bin/bash -c "echo '
                  base_emb_dim: {self.mp_dict['base_emb_dim']}
                  base_num_query_heads: {self.mp_dict['base_num_query_heads']}
                  base_num_kv_heads: {self.mp_dict['base_num_kv_heads']}
                  base_num_decoder_layers: {self.mp_dict['base_num_decoder_layers']}
                  base_mlp_dim: {self.mp_dict['base_mlp_dim']}
                  head_dim: {self.mp_dict['head_dim']}
                  mlp_activations: {self.mp_dict['mlp_activations']}
                  vocab_size: {self.mp_dict['vocab_size']}
                  enable_dropout: {self.mp_dict['enable_dropout']}
                  logits_via_embedding: {self.mp_dict['logits_via_embedding']}
                  normalization_layer_epsilon: {self.mp_dict['normalization_layer_epsilon']}
                  rope_max_timescale: {self.mp_dict['rope_max_timescale']}
                  decoder_block: {self.mp_dict['decoder_block']} '  > /workspace/maxtext/MaxText/configs/models/model_config_for_jax.yml" '''
        formatted_cmd = textwrap_for_yml(cmd)
        self.phdl.exec(formatted_cmd)

        xla_dict = self.mp_dict['xla_flags']
        cmd = f'''docker exec {self.container_name} /bin/bash -c \"echo export XLA_FLAGS=--xla_gpu_enable_cublaslt={xla_dict['xla_gpu_enable_cublaslt']} --xla_gpu_graph_level={xla_dict['xla_gpu_graph_level']} --xla_gpu_autotune_level={xla_dict['xla_gpu_autotune_level']} --xla_gpu_enable_reduce_scatter_combine_by_dim={xla_dict['xla_gpu_enable_reduce_scatter_combine_by_dim']} --xla_gpu_reduce_scatter_combine_threshold_bytes={xla_dict['xla_gpu_reduce_scatter_combine_threshold_bytes']} --xla_gpu_all_reduce_combine_threshold_bytes={xla_dict['xla_gpu_all_reduce_combine_threshold_bytes']}  --xla_gpu_all_gather_combine_threshold_bytes={xla_dict['xla_gpu_all_gather_combine_threshold_bytes']} --xla_gpu_enable_all_gather_combine_by_dim={xla_dict['xla_gpu_enable_all_gather_combine_by_dim']} > /workspace/maxtext/maxtext_env.sh\"'''
        self.phdl.exec(cmd)

        # Hack to add the double quotes ..
        cmd = f'''docker exec {self.container_name} /bin/bash -c 'sed -i -e "s/XLA_FLAGS=/XLA_FLAGS=\\\"/g" -e "/XLA_FLAGS/s/$/\\\"/g" /workspace/maxtext/maxtext_env.sh'  '''
        self.phdl.exec(cmd)

        time.sleep(5)


        # Need check for Single Node vs Double node ..
        cmd_list = []
        for i in range(0,int(self.nnodes)):
            cmd = f'''docker exec {self.container_name} /bin/bash -c  "echo  '
                      export NNODES={int(self.nnodes)}
                      export NODE_RANK={i}
                      export HSA_FORCE_FINE_GRAIN_PCIE=1
                      export GPU_MAX_HW_QUEUES={self.tc_dict['gpu_max_hw_queues']}
                      export HIP_FORCE_DEV_KERNARG=1
                      export NVTE_FUSED_ATTN=1
                      export NVTE_ALLOW_NONDETERMINISTIC_ALGO=1
                      export XLA_PYTHON_CLIENT_MEM_FRACTION={self.tc_dict['xla_python_client_mem_fraction']}
                      export LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH
                      export NCCL_DEBUG={self.tc_dict['nccl_debug']}
                      export NCCL_CHECKS_DISABLE={self.tc_dict['nccl_checks_disable']}
                      export NCCL_IB_HCA={self.tc_dict['nccl_ib_hca']}
                      export NCCL_IB_GID_INDEX={self.tc_dict['nccl_ib_gid_index']}
                      export NCCL_CROSS_NIC=0
                      export NCCL_PROTO={self.tc_dict['nccl_proto']}
                      export HSA_FORCE_FINE_GRAIN_PCIE=1
                      export NCCL_IB_TC={self.tc_dict['nccl_ib_tc']}
                      export NCCL_IB_SL={self.tc_dict['nccl_ib_sl']}
                      export NCCL_SOCKET_IFNAME={self.tc_dict['nccl_socket_ifname']}
                      export GLOO_SOCKET_IFNAME={self.tc_dict['gloo_socket_ifname']}
                      export NCCL_CHECKS_DISABLE={self.tc_dict['nccl_checks_disable']}
                      export HSA_FORCE_FINE_GRAIN_PCIE=1
                      export NVTE_CK_BWD_V3={self.tc_dict['nvte_ck_bwd_v3']}
                      export NVTE_CK_V3_BF16_CVT={self.tc_dict['nvte_ck_v3_bf16_cvt']}' >> /workspace/maxtext/maxtext_env.sh"'''
            formatted_cmd = textwrap_for_yml(cmd)
            cmd_list.append(formatted_cmd)
        self.phdl.exec_cmd_list(cmd_list)

        cmd_list = []
        for i in range(0,int(self.nnodes)):
            cmd = f'''docker exec {self.container_name} /bin/bash -c "mkdir -p {self.tc_dict['log_dir']}/jax-logs/out-node{i}"'''
            cmd_list.append(cmd)
        self.phdl.exec_cmd_list(cmd_list)


        cmd_list = []
        for i in range(0,int(self.nnodes)):
            # Take a reference config yml like llama2_70b
            cmd = f'''docker exec {self.container_name} /bin/bash -c "echo '
                      mkdir -p {self.tc_dict['log_dir']}/jax-logs/out-node{i}
                      cd /workspace/maxtext; python /workspace/maxtext/MaxText/train.py MaxText/configs/llama2_70b_gpu_bs7.yml base_output_directory={self.tc_dict['log_dir']} 2>&1 | tee >(grep -v 'external/xla/xla/') > {self.tc_dict['log_dir']}/jax-logs/out-node{i}/training.log' > /workspace/maxtext/training_wrapper_script.sh"'''
            formatted_cmd = textwrap_for_yml(cmd)
            cmd_list.append(formatted_cmd)
        self.phdl.exec_cmd_list(cmd_list)

        # Replace with the config.yml we generated
        cmd = f'''docker exec {self.container_name} /bin/bash -c 'sed -i -e "s/llama2_70b_gpu_bs7.yml/training_config_for_jax.yml/g"  /workspace/maxtext/training_wrapper_script.sh'  '''
        self.phdl.exec(cmd)



    def start_training_job( self, ):
        print('Start Training on all Nodes')
        cmd_list = []
        for i in range(0,int(self.nnodes)):
            cmd = f'''docker exec {self.container_name} /bin/bash -c "source /workspace/maxtext/maxtext_env.sh && nohup bash /workspace/maxtext/training_wrapper_script.sh > {self.tc_dict['log_dir']}/jax-logs/out-node{i}/training_redirect_logs"'''
            cmd_list.append(cmd)
        self.phdl.exec_cmd_list(cmd_list)
        time.sleep(60)


    def check_deviation_from_median(self, training_results_dict, metric_name, percentage_off ):
        list_of_values = []
        #To avoid any outliers, we exclude the first couple of steps ..
        for i in range(2, self.training_steps ):
            list_of_values.append(training_results_dict[i][metric_name])
        median_value = statistics.median(list_of_values)
        upper_bound = median_value * (1 + percentage_off )
        lower_bound = median_value * (1 - percentage_off )
        for i in range(2, self.training_steps ):
            if lower_bound <= training_results_dict[i][metric_name] <= upper_bound:
                print(f'Training step {i} training metric {metric_name} is in expected range')
            else:
                fail_test(f'FAIL Training step {i} training metric {metric_name} is over {percentage_off}% from median value {median_value} - actual value {training_results_dict[i][metric_name]}')
       
            

    def get_training_results_dict(self, ):
        training_results_dict = {}
        percentage_off = 0.10
        last_node = self.host_list[len(self.host_list) -1]
        out_dict = self.phdl.exec(f'cat {self.home_dir}/training_logs')
        output = out_dict[last_node]
        for i in range(0, self.training_steps):
            training_results_dict[i] = {}
            match = re.search( f'completed step:\s{i}, seconds:\s([0-9\.]+),\sTFLOP\/s\/device:\s([0-9\.]+)\s+Tokens\/s\/device:\s([0-9\.]+),\s+total_weights:\s([0-9\.]+),\s+loss:\s([0-9\.]+)', output, re.I )
            training_results_dict[i]['time_elapsed'] = match.group(1)
            training_results_dict[i]['tflops_per_sec_per_gpu'] = match.group(2)
            training_results_dict[i]['tokens_per_sec_per_gpu'] = match.group(3)
            training_results_dict[i]['total_weights'] = match.group(4)
            training_results_dict[i]['loss'] = match.group(5)

        #TO DO
        # Check if the Loss function is not growing by over 10%
        self.check_deviation_from_median( training_results_dict, 'tflops_per_sec_per_gpu', percentage_off )    
        self.check_deviation_from_median( training_results_dict, 'tokens_per_sec_per_gpu', percentage_off )    
        self.check_deviation_from_median( training_results_dict, 'loss', percentage_off )    
            
        print(training_result_dict)
        return training_result_dict


    def scan_for_training_errors(self, ):
        print('Scan for training errors')
        training_pass=True
        last_node = self.host_list[len(self.host_list) -1]
        cmd_list = []
        for j in range(0,int(self.nnodes)):
            cmd = f"sudo cat {self.tc_dict['log_dir']}/jax-logs/out-node{j}/training.log"
            cmd_list.append(cmd)
        out_dict = self.phdl.exec_cmd_list(cmd_list) 
        output = out_dict[last_node]
        for err_key in training_err_dict:
            if re.search( f'{training_err_dict[err_key]}', output ):
                fail_test(f'ERROR {training_err_dict[err_key]} seen in training logs ..')
                log.error(f'Aborting training log polling')
                training_pass=False
        return training_pass


    def poll_for_training_completion( self, ):
        print('Poll for training completion')
        time.sleep(60)
        last_node = self.host_list[len(self.host_list) -1]

        for i in range(1,int(self.training_poll_iterations)):
            print(f'Starting iteration {i}')
            if not self.scan_for_training_errors():
                fail_test('Failures seen in training logs, Aborting!!!')
                return
            cmd_list = []
            for j in range(0,int(self.nnodes)):
                cmd = f"sudo tail -2000 {self.tc_dict['log_dir']}/jax-logs/out-node{j}/training.log"
                cmd_list.append(cmd)
            out_dict = self.phdl.exec_cmd_list(cmd_list)
            output = out_dict[last_node]

            max_iterations = int(self.training_steps)-1
            if not re.search( f'completed step:\s+{max_iterations},', output, re.I ):
                print('Training still in progress')
                time.sleep(30)
            else:
                if re.search( 'TFLOPS\/s\/device:\s+[NaN|Inf]', output, re.I ) or \
                       re.search( 'Tokens\/s\/device:\s+[NaN|Inf]', output, re.I ):
                    fail_test(f'ERROR - NaN or Inf values seen in training results {output}')
                    return
                else:
                    self.training_result_dict = self.get_training_results_dict()
                    print('Completed Training, returning !!!')
                    return
            # Wait 60 secs between every iteration
            time.sleep(60)

        
    def verify_training_results( self, ):
        print('Verify Training Results')
