# Utility scripts

This folder comprises of standalone native Python scripts that offer different utility functions.    

## Cluster Health Checker

This is a python script that generates a health report of your cluster by collecting various logs and metrics of the GPU nodes. It can help
identify any hardware failure/degradation signatures like RAS errors, PCIe/XGMI errors, network drop/error counters 

### Cluster Health Checker

This is a python script that generates an overall health report of your cluster by collecting various logs and metrics of the GPU nodes.

It can help identify various

1. Hardware failures/degradation signatures like RAS errors, PCIe/XGMI errors, network drop/error counters.
2. Software failures - By looking for failure signatures in demsg, journlctl logs

This also acts as triaging tool to troubleshoot any performance issues that may be related to the AI infrastructure. It allows you to take s
napshot of all counters (GPU/NIC) while your training/inference workloads are in progress and compare the counters and identify any increment of unexpected counters across all nodes in the cluster to find needle in a haystack.            


### Usage for Cluster Health Checker


```
(myenv) [ubuntu-host]~/cvs:(main)$
(myenv) [ubuntu-host]~/cvs:(main)$python3 ./utils/check_cluster_health.py -h
usage: check_cluster_health.py [-h] --hosts_file HOSTS_FILE --username USERNAME (--password PASSWORD | --key_file KEY_FILE)
                               [--iterations ITERATIONS] [--time_between_iters TIME_BETWEEN_ITERS] [--report_file REPORT_FILE]

Check Cluster Health

options:
  -h, --help            show this help message and exit
  --hosts_file HOSTS_FILE
                        File name with list of IP address one per line
  --username USERNAME   Username to ssh to the hosts
  --password PASSWORD   Password for username
  --key_file KEY_FILE   Private Keyfile for username
  --iterations ITERATIONS
                        Number of iterations to run the checks
  --time_between_iters TIME_BETWEEN_ITERS
                        Time duration to sleep between iterations ..
  --report_file REPORT_FILE
(myenv) [ubuntu-host]~/cvs:(main)$
(myenv) [ubuntu-host]~/cvs:(main)$
(myenv) [ubuntu-host]~/cvs/utils:(main)$
(myenv) [ubuntu-host]~/cvs/utils:(main)$python3 ./utils/check_cluster_health.py --hosts_file /home/user1/hosts_file.txt --username user1  --key_file /home/user1/.ssh/id_rsa --iterations 2

```

