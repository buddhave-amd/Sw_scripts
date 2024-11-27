import csv
import sys

def load_csv(file_path):
    """Load the contents of a CSV file into a list of dictionaries."""
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
    return rows

def compare_csv(file1, file2):
    """
    Compare two CSV files:
    - If the `Result` is `PASS`, check for differences in `MD5 sum`.
    - If the `Result` is `FAIL`, record the status and command executed.
    """
    data1 = load_csv(file1)
    data2 = load_csv(file2)

    # Ensure both CSV files have the same number of rows
    if len(data1) != len(data2):
        print("Warning: The CSV files have a different number of rows!")
    
    differences = []
    
    '''
    # Compare rows by position (index)
    for i in range(min(len(data1), len(data2))):
        row1 = data1[i]
        row2 = data2[i]
    '''
    i=0
    for row1, row2 in zip(data1, data2):
        i=i+1
        # Check if the TC ids match
        if row1['TC id'] != row2['TC id']:
            print(f"Warning: Mismatched test case IDs: {row1['TC id']} vs {row2['TC id']}")
            differences.append({
                'S.No' : f"{i}",
                'TC id': f"NOCHECK: Different testcaseIDs",
                'MD5 sum 1': 'NOCHECK',
                'MD5 sum 2': 'NOCHECK',
                'Command': 'NOCHECK',
                'Result': "NOCHECK",
                'Final result': "NOCHECK"
            })            
            continue    
        final_result = ""  # Initialize the final result column for each row

        if row1['Result'] == 'PASS' and row2['Result'] == 'PASS':
            # Compare MD5 sums for PASS cases
            if row1['MD5 sum'] != row2['MD5 sum']:
                final_result = "MISMATCH"
                differences.append({
                    'S.No' : f"{i}",
                    'TC id': row1['TC id'],
                    'MD5 sum 1': row1['MD5 sum'],
                    'MD5 sum 2': row2['MD5 sum'],
                    'Command': row1['Executed Command'],
                    'Result': "PASS",
                    'Final result': "MISMATCH"
                })
            else:
                final_result = "MATCH"
                differences.append({
                    'S.No' : f"{i}",
                    'TC id': row1['TC id'],
                    'MD5 sum 1': row1['MD5 sum'],
                    'MD5 sum 2': row2['MD5 sum'],
                    'Command': row1['Executed Command'],
                    'Result': "PASS",
                    'Final result': "MATCH"
                })
        else:
            final_result = "EXECUTION FAIL"
            # Record FAIL cases
            differences.append({
                'S.No' : f"{i}",
                'TC id': row1['TC id'],
                'MD5 sum 1': '',
                'MD5 sum 2': '',
                'Command': row1['Executed Command'],
                'Result': 'FAIL',
                'Final result': "EXECUTION FAIL"
            })

    return differences

def write_csv(results, output_file):
    """Write comparison results to a CSV file."""
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['S.No','TC id', 'Result', 'MD5 sum 1', 'MD5 sum 2', 'Command', 'Final result']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow(result)

def main():
    if len(sys.argv) != 4:
        print("Usage: python compare_csv.py <csv_file1> <csv_file2> <output_csv_file>")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]
    output_file = sys.argv[3]

    differences = compare_csv(file1, file2)

    # Write results to the output CSV file
    write_csv(differences, output_file)

    print(f"Comparison results have been written to {output_file}")

if __name__ == "__main__":
    main()
