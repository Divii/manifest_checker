# Left off on:
# Generate results for every check first, then generate OR results

# List globals at some point

#Potential issues:
#If the first line from an OR block matches any other line in the checks files, the results generation may wig out

import sys
import re

id_col = 0
absence_col = 1
case_col = 2
check_col = 3
regex_col = 4
all_status_col = 5
final_status_col = 6
reason_col = 7
freq_col = 8

# Create the manifest text that will be searched
android_manifest = open('AndroidManifest.xml', 'r')
manifest_text = android_manifest.read()
manifest_sans_comments = re.sub('<!--.*?-->', '', manifest_text)

# Create the manifest checks list
manifest_checks = open('manifest_checks.txt', 'r')
manifest_checks_text = manifest_checks.read()

def generate_check_table():
	global manifest_check_line
	manifest_check_line = manifest_checks_text.splitlines()

	# Create version_info list out of the first line
	version_info = []
	for item in manifest_check_line[0].split('||'):
		left, right = item.split(':', 1)
		version_info.append(right.strip())

	# Stripping the version info row out as it is no longer needed
	manifest_check_line = manifest_check_line[1:]
	global manifest_check_count
	manifest_check_count = len(manifest_check_line)

	# Creating check table
	global check_table
	check_table = [['null' for col_count in range(8)] for row_count in range(manifest_check_count)] 

	for loop_index, item in enumerate(manifest_check_line):
		# Will be used to pull Test ID and actual check string
		check_split = str.split(item, '||')

		if 'TEST_ID' in check_split[0]:
			check_table[loop_index][id_col] = check_split[0][8:]
		else:
			check_table[loop_index][id_col] = ''

		if 'ABSENT||' in manifest_check_line[loop_index]:
			check_table[loop_index][absence_col] = 'A'
		else:
			check_table[loop_index][absence_col] = ''

		if 'CASE||' in manifest_check_line[loop_index]:
			check_table[loop_index][case_col] = 'C'
		else:
			check_table[loop_index][case_col] = ''

		if 'OR >   ' in check_split[-1]:
			check_table[loop_index][check_col] = check_split[-1][7:]
		else:
			check_table[loop_index][check_col] = check_split[-1]

		#print "\n" + check_split[-1] + "\n" + check_table[loop_index][check_col]

def convert_and_escape_checks():
	for loop_index, item in enumerate(manifest_check_line):
		result = re.match(r'.*?\.\.\..*?\.\.\..*?', check_table[loop_index][check_col])
		if result:
			ellipsis_content = re.search(r'(.*?)\.\.\.(.*?)\.\.\.(.*?)$', check_table[loop_index][check_col])
			group1 = re.escape(ellipsis_content.group(1))
			group2 = re.escape(ellipsis_content.group(2))
			group3 = re.escape(ellipsis_content.group(3))
			check_table[loop_index][regex_col] = group1 + "((?!" + group3 + ").)*" + group2
		else:
			check_table[loop_index][regex_col] = re.escape(check_table[loop_index][check_col])

		#print loop_index + 1, check_table[loop_index][check_col] + "\n" + check_table[loop_index][regex_col] + "\n"	

def account_for_whitespace():
	for loop_index, item in enumerate(manifest_check_line):
		# Spaces are being escaped in convert_and_escape_checks. Have to search for '/ ' instead of just ' ' as a result.
		check_table[loop_index][regex_col] = re.sub(r'(\\\s+)+', '\s+', check_table[loop_index][regex_col])
		# < -> \<
		check_table[loop_index][regex_col] = re.sub(r'\\<(?!\\/)', '\s*\<\s*', check_table[loop_index][regex_col])
		# </ -> \<\/
		check_table[loop_index][regex_col] = re.sub(r'\\<\\/', '\s*\<\/\s*', check_table[loop_index][regex_col])
		# > -> \>
		check_table[loop_index][regex_col] = re.sub(r'(?<!\\/)\\>', '\s*\>\s*', check_table[loop_index][regex_col])
		# /> -> \/\>
		check_table[loop_index][regex_col] = re.sub(r'\\/\\>', '\s*\/\>\s*', check_table[loop_index][regex_col])

def account_for_case_sensitivity():
	for loop_index, item in enumerate(manifest_check_line):
		if 'C' not in check_table[loop_index][case_col]:
			check_table[loop_index][regex_col] = '(?i)' + check_table[loop_index][regex_col]

		#print loop_index, check_table[loop_index][check_col] + "\n" + check_table[loop_index][regex_col] + "\n"	

def generate_or_blocks():
	if 'OR >   ' in manifest_check_line[0]:
		sys.exit("ERROR: First check in manifest_checks.txt is an OR. \nAn OR block's first check cannot contain 'OR >   ' \nExiting.")

	global or_block
	or_block = []
	or_block_number = -1
	current_item = 0
	next_item = current_item + 1
	while manifest_check_count - 1 >= current_item:
		if manifest_check_count -1 != current_item and 'OR >   ' not in manifest_check_line[current_item] and 'OR >   ' in manifest_check_line[next_item]:
			or_block_number += 1
			#print 'Adding block number:', or_block_number
			or_block.append([check_table[current_item][regex_col]])
			while 'OR >   ' in manifest_check_line[next_item]:
				or_block[or_block_number].append(check_table[next_item][regex_col]) 
				current_item += 1
				next_item += 1
			#print or_block[or_block_number]
		else:
			current_item += 1
			next_item += 1

def generate_statuses():
	for loop_index, item in enumerate(manifest_check_line):
		result = re.search(check_table[loop_index][regex_col], manifest_sans_comments)
		if check_table[loop_index][absence_col] == 'A':
			if result == None:
				check_table[loop_index][all_status_col] = 'Pass'
				check_table[loop_index][reason_col] = ''
			else:
				check_table[loop_index][all_status_col] = 'FAIL'
				check_table[loop_index][reason_col] = generate_fail_reasons(loop_index, 'text_present')
		else:
			if result == None:
				check_table[loop_index][all_status_col] = 'FAIL'
				check_table[loop_index][reason_col] = generate_fail_reasons(loop_index, 'text_absent')
			else:
				check_table[loop_index][all_status_col] = 'Pass'
				check_table[loop_index][reason_col] = ''
			# print check_table[loop_index][regex_col]
			# print loop_index + 1, result
			# print ''
		print loop_index + 1, check_table[loop_index][all_status_col], check_table[loop_index][reason_col]

def generate_fail_reasons(check_number, fail_type):
	#Acceptable arguments:
	# - check_number = self explanatory
	# - fail_type can be either 'test_present' or 'test_absent'
	fail_reason = 'null'
	if fail_type == 'text_present':
		if check_table[check_number][case_col] == 'C':
			fail_reason = 'Text found with matching capitalization'
		else:
			fail_reason = 'Text found and not commented out'
	elif fail_type == 'text_absent':
		if check_table[check_number][case_col] == 'C':
			case_check_string = '(?i)' + check_table[check_number][regex_col]

			if re.search(case_check_string, manifest_sans_comments):
				fail_reason = 'Incorrect capitalization'

			elif re.search(case_check_string, manifest_sans_comments) == None:
				if re.search(check_table[check_number][regex_col], manifest_text):
					fail_reason = 'Text commented out'
				elif re.search(check_table[check_number][regex_col], manifest_text) == None:
					if re.search(case_check_string, manifest_text):
						fail_reason = "Text commented out and incorrectly capitalized"
					elif re.search(case_check_string, manifest_text) == None:
						fail_reason = "Text not found"
		elif check_table[check_number][case_col] == '':
			if re.search(check_table[check_number][regex_col], manifest_text):
				fail_reason = 'Text commented out'
			elif re.search(check_table[check_number][regex_col], manifest_text) == None:
				fail_reason = 'Text not found'
	return fail_reason

generate_check_table()
convert_and_escape_checks()
account_for_whitespace()
account_for_case_sensitivity()
generate_or_blocks()
generate_statuses()