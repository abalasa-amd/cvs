import re
import argparse
import os




def main():
    parser = argparse.ArgumentParser(description="Generate cluster json file" )
    parser.add_argument("--input_hosts_file", required=True,
           help = "Input file with host IPs - one address per line")
    parser.add_argument("--output_json_file", required=True,
           help = "Output cluster file in JSON format")
    parser.add_argument("--username", required=True,
           help = "Username to ssh to the hosts")
    parser.add_argument("--key_file", required=True,
           help = "keyfile with private keys")
    args = parser.parse_args()


    with open(args.input_hosts_file, "r") as f:
         node_list = [ line.strip() for line in f if line.strip()]
    if not node_list:
        print("ERROR !! No hosts in the file, this is mandatory, aborting !!")
        sys.exit(1)
    if len(node_list) == 0:
        print("ERROR !! No hosts in the file, this is mandatory, aborting !!")
        sys.exit(1)

    with open(args.output_json_file, "w") as fp:
         fp.write("{\n")
         fp.write(f'"username": "{args.username}",\n')
         fp.write(f'"priv_key_file": "{args.key_file}",\n')
         fp.write(f'"head_node_dict":\n')
         fp.write("{\n")
         fp.write(f'"mgmt_ip": "{node_list[0]}"\n')
         fp.write("},\n")
         fp.write(f'"node_dict":\n')
         fp.write("  {\n")
         node_list_len=len(node_list)
         i = 0
         for node in node_list:
             fp.write(f'  "{node}":\n')
             fp.write("   {\n")
             fp.write(f'       "bmc_ip": "NA",\n')
             fp.write(f'       "vpc_ip": "{node}"\n')
             if i == node_list_len-1:
                 fp.write("   }\n")
             else:    
                 fp.write("   },\n")
             i = i + 1 
         fp.write("  }\n")
         fp.write("}\n")
               

if __name__ == "__main__":
    main()

