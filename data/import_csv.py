import csv

# Open the input CSV file for reading
with open('input.csv', 'r') as infile:
    # Open the output CSV file for writing
    with open('output.csv', 'w', newline='') as outfile:
        # Create a CSV reader
        reader = csv.reader(infile)
        # Create a CSV writer
        writer = csv.writer(outfile)
        # Iterate over each row in the input CSV
        for row in reader:
            # Add a single quote to the beginning of each text field
            modified_row = [f"'{field}" for field in row]
            # Write the modified row to the output CSV
            writer.writerow(modified_row)
