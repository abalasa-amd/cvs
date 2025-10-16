.. meta::
  :description: Configure the Health configuration file variables
  :keywords: health, ROCm, install, cvs

******************************
Health test configuration file
******************************

Configuration file
==================

Here's a code snippet of the ``mi300_health_config.json`` file for reference:

.. code:: json
  
 {

    "agfhc":
    {
         "path": "/opt/amd/agfhc",
         "package_tar_ball": "/root/cache/PACKAGES/agfhc-mi300x_1.22.0_ub2204.tar.bz2",
         "install_dir": "/root/cache/INSTALL/agfhc/",
         "nfs_install": "True",
         "hbm_test_duration": "00:01:30"
    },
    "transferbench":
    {
       "path": "/opt/amd/transferbench",
       "example_tests_path": "/root/cache/INSTALL/TransferBench/examples",
       "git_install_path": "/root/cache/INSTALL/",
       "git_url": "https://github.com/ROCm/TransferBench.git",
       "nfs_install": "True",
       "results":
       {
           "bytes_to_transfer": "268435456",
           "path": "/opt/amd/transferbench",
           "gpu_to_gpu_a2a_rtotal": "320.0",
           "avg_gpu_to_gpu_p2p_unidir_bw": "33.9",
           "avg_gpu_to_gpu_p2p_bidir_bw": "43.9",
           "best_gpu0_bw": "480.0",
           "32_cu_local_read": "1650",
           "32_cu_local_write": "1250.0",
           "32_cu_local_copy": "1250.0",
           "32_cu_rem_read": "48.0",
           "32_cu_rem_write": "48.0",
           "32_cu_rem_copy": "48.0",
           "example_results":
           {
               "test1": "47.1",
               "test2": "48.4",
               "test3_0_to_1": "31.9",
               "test3_1_to_0": "38.9",
               "test4": "1264",
               "test6": "48.6"
           }

       }
    },
    "rocblas":
    {
       "path": "/root/cache/INSTALL/rocBLAS/build/release/clients/staging",
       "git_install_path": "/root/cache/INSTALL",
       "git_url": "https://github.com/ROCm/rocBLAS.git",
       "rocm_version": "7.0.0",
       "nfs_install": "True",
       "results":
       {
           "fp32_gflops": "94100",
           "bf16_gflops": "130600",
           "int8_gflops": "162700"
       }
    },
    "rochpl":
    {
       "path": "/root/cache/INSTALL/rocHPL",
       "git_install_path": "/root/cache/INSTALL",
       "git_url": "https://github.com/ROCm/rocHPL.git",
       "nfs_install": "True",
       "results":
       {
           "fp32_gflops": "94100",
           "bf16_gflops": "130600",
           "int8_gflops": "162700"
       }
    },
    "babelstream":
    {
       "path": "/root/cache/INSTALL/BabelStream/build",
       "git_install_path": "/root/cache/INSTALL",
       "git_url": "https://github.com/UoB-HPC/BabelStream.git",
       "nfs_install": "True",
       "results":
       {
           "copy": "4177285",
           "mul": "4067069",
           "add": "3920853",
           "triad": "3885301",
           "dot": "3660781"
       }
    }

 }

Parameters
==========

Here's an exhaustive list of the available parameters in the Health configuration file.

AGFHC
-----

.. list-table::
   :widths: 15 10 30
   :header-rows: 1

   * - Configuration parameters
     - Default values
     - Description
   * - ``path``
     - ``/root/cache/PACKAGES/agfhc-mi300x_1.22.0_ub2204.tar.bz2``
     - Path where AGFHC is installed
   * - ``package_tar_ball``
     - ``/root/cache/INSTALL/agfhc/``
     - Path where the tar ball is downloaded   
   * - ``install_dir``
     - ``/root/cache/INSTALL/agfhc/``
     - Path where AGFHC runs
   * - ``nfs_install``
     - True
     - Set the flag to install nfs
   * - ``hbm_test_duration``
     - 00:01:30
     - HBM test duration

TransferBench
-------------

.. list-table::
   :widths: 15 10 30
   :header-rows: 1

   * - Configuration parameters
     - Default values
     - Description
   * - ``path``
     - ``/opt/amd/transferbench``
     - Path where Transferbench is installed
   * - ``example_tests_path``
     - ``/root/cache/INSTALL/TransferBench/examples``
     - Path where Transferbench examples are installed
   * - ``git_install_path``
     - ``/root/cache/INSTALL/``
     - Path where the Git repo is installed
   * - ``git_url``
     - `https://github.com/ROCm/TransferBench.git <https://github.com/ROCm/TransferBench.git>`_
     - URL for git repo
   * - ``nfs_install``
     - True
     - Set the flag to install nfs
   * - ``bytes_to_transfer``
     - 268435456
     - Amount of data to transfer in bytes (256 MB) ̶  this is the payload size for bandwidth tests
   * - ``gpu_to_gpu_a2a_rtotal``
     - 320.0
     - All-to-all communication total bandwidth in GB/s across all GPUs 
   * - ``avg_gpu_to_gpu_p2p_unidir_bw``
     - 33.9
     - Average peer-to-peer unidirectional bandwidth (GB/s) between GPU pairs
   * - ``avg_gpu_to_gpu_p2p_bidir_bw``
     - 43.9
     - Average peer-to-peer bidirectional bandwidth (GB/s) between GPU pair
   * - ``best_gpu0_bw``
     - 480.0
     - Best measured bandwidth (GB/s) for GPU 0
   * - ``32_cu_local_read``
     - 1650
     - Local memory read bandwidth (GB/s) using 32 CUs
   * - ``32_cu_local_write``
     - 1250.0
     - Local memory write bandwidth (GB/s) using 32 CUs
   * - ``32_cu_local_copy``
     - 1250.0
     - Local memory copy bandwidth (GB/s) using 32 CUs
   * - ``32_cu_rem_read``
     - 48.0
     - Remote memory read bandwidth (GB/s) using 32 CUs
   * - ``32_cu_rem_write``
     - 48.0
     - Remote memory write bandwidth (GB/s) using 32 CUs
   * - ``32_cu_rem_copy``
     - 48.0
     - Remote memory copy bandwidth (GB/s) using 32 CUs
   * - ``test1``
     - 47.1
     - Specific benchmark result (likely bandwidth in GB/s)
   * - ``test2``
     - 48.4
     - Another benchmark result
   * - ``test3_0_to_1``
     - 31.9
     - Directional test from GPU 0 to GPU 1
   * - ``test3_1_to_0``
     - 38.9
     - Directional test from GPU 1 to GPU 0
   * - ``test4``
     - 1264
     - High-performance test result (possibly local memory)
   * - ``test6``
     - 48.6
     - Additional benchmark result
  
RocBLAS
-------

.. list-table::
   :widths: 15 10 30
   :header-rows: 1

   * - Configuration parameters
     - Default values
     - Description
   * - ``path``
     - ``/root/cache/INSTALL/rocBLAS/build/release/clients/staging``
     - Path to run rocblas test
   * - ``git_install_path``
     - ``/root/cache/INSTALL``
     - Path where rocBLAS is installed
   * - ``git_url``
     - `https://github.com/ROCm/rocBLAS.git <https://github.com/ROCm/rocBLAS.git>`_
     - URL for git repo
   * - ``rocm_version``
     - 7.0.0
     - ROCm Version
   * - ``nfs_install``
     - True
     - Set the flag to install nfs
   * - ``fp32_gflops``
     - 94100
     - 32 bit floating point computational performance benchmarks
   * - ``bf16_gflops``
     - 130600
     - 16 bit floating point computational performance benchmarks
   * - ``int8_gflops``
     - 162700
     - 8 bit floating point computational performance benchmarks

rocHPL
------

.. list-table::
   :widths: 15 10 30
   :header-rows: 1

   * - Configuration parameters
     - Default values
     - Description
   * - ``path``
     - ``/root/cache/INSTALL/rocHPL``
     - Path to run the rocHPL test
   * - ``git_install_path``
     - ``/root/cache/INSTALL``
     - Path where rocHPL is installed
   * - ``git_url``
     - `https://github.com/ROCm/rocHPL.com <https://github.com/ROCm/rocHPL.com>`_
     - URL for git repo
   * - ``nfs_install``
     - True
     - Set the flag to install nfs
   * - ``fp32_gflops``
     - 94100
     - 32 bit floating point computational performance benchmarks
   * - ``bf16_gflops``
     - 130600
     - 16 bit floating point computational performance benchmarks
   * - ``int8_gflops``
     - 162700
     - 8 bit floating point computational performance benchmarks

BabelStream
-----------

.. list-table::
   :widths: 15 10 30
   :header-rows: 1

   * - Configuration parameters
     - Default values
     - Description
   * - ``path``
     - ``/root/cache/INSTALL/BabelStream/build``
     - Path to run babelstream test
   * - ``git_install_path``
     - ``/root/cache/INSTALL``
     - Path where babelstream is installed
   * - ``git_url``
     - `https://github.com/UoB-HPC/BabelStream.git <https://github.com/UoB-HPC/BabelStream.git>`_
     - 
   * - ``nfs_install``
     - True
     - Set the flag to install nfs
   * - ``copy``
     - 4177285
     - Memory copy operation
   * - ``mul``
     - 4067069
     -  Multiplication operation
   * - ``add``
     - 3920853
     - Addition operation
   * - ``triad``
     - 3885301
     - Triad operation
   * - ``dot``
     - 3660781
     - Dot product


