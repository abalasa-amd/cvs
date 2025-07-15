import re
import os
import sys
import json

import pytest
import globals

log = globals.log

def fail_test(msg):
    #pytest.fail('FAIL - {}'.format(msg))
    print('FAIL - {}'.format(msg))
    log.error('FAIL - {}'.format(msg))
    globals.error_list.append(msg)

def update_test_result():
    if len(globals.error_list) > 0:
        pytest.fail('Following FAILURES seen - {}'.format(globals.error_list))



def print_test_output(log, out_dict):
    print('#========================================================#')
    print('\t\t ** Test Output **')
    print('#========================================================#')
    for node in out_dict.keys():
        print(f'==== {node} ====')
        print(out_dict[node]) 



def scan_test_results(out_dict):
    word_count = 5
    for host in out_dict.keys():
        match = re.search( 'test FAIL |test ERROR |ABORT|Traceback|No such file|FATAL', out_dict[host], re.I )
        if match:
            start_index = match.start()
            end_index = match.end()
            words = out_dict[host].split()
            # Find the index of the target word in the list of words
            target_word_index = -1
            for i, word in enumerate(words):
                if re.search('FAIL|ERR|ABORT|Traceback', word, re.I): # Check if the pattern is part of the word
                    target_word_index = i
                    actual_word = word
                    break

            if target_word_index != -1:
                # Get the words before the match
                before_words = words[max(0, target_word_index - word_count) : target_word_index]
                # Get the words after the match
                after_words = words[target_word_index + 1 : min(len(words), target_word_index + word_count + 1)]
                print(f"Words before: {before_words}")
                print(f"Words after: {after_words}")
                print(f'Test failed in scan_result on node {host} due to pattern ')
            fail_test(f'Test failed in scan_result on node {host} due to pattern {before_words} {actual_word} {after_words}')




def json_to_dict(json_string):
    print('^^^^^^^^^')
    print(json_string)
    return json.loads(json_string) 


def convert_phdl_json_to_dict( dict_json ):
    out_dict = {}
    for node in dict_json.keys():
        try:
            out_dict[node] = json_to_dict( dict_json[node] )
        except Exception as e:
            print(f'ERROR converting Json output to dict for node {node}')
            fail_test(f'ERROR converting Json output to dict for node {node}')
            out_dict[node] = {}
    return out_dict



def get_model_from_rocm_smi_output(smi_output):
    if re.search( 'MI300X', smi_output, re.I ):
        model = 'mi300x'  
    elif re.search( 'MI325', smi_output, re.I ):
        model = 'mi325' 
    elif re.search( 'MI350', smi_output, re.I ):
        model = 'mi350'
    elif re.search( 'MI355', smi_output, re.I ):
        model = 'mi355'
    else:  
        model = 'mi300x'
    return model



def convert_hms_to_secs( time_string ):
    try:
        parts = time_string.split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])  # Use float to handle potential decimal seconds
            total_seconds = (hours * 3600) + (minutes * 60) + seconds
            return total_seconds
        else:
            print("Invalid time format. Please use 'hr:min:sec'.")
            return None
    except ValueError:
        print("Invalid time format. Please ensure hours, minutes, and seconds are numeric.")
        return None
