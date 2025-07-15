# Add all additional cmd line arguments for the script
def pytest_addoption(parser):
    parser.addoption( "--cluster_file", action="store", required=True, help="Input file with all the details of the cluster, nodes, switches in JSON format" )
    parser.addoption( "--config_file", action="store", required=True, help="Input file with all configurations and parameters for tests in JSON format" )
