
import csv

input_file = r"e:\AgenticSystem\Leadai\Sales-Multi-Agent-AI\data\JewX_Combined_Leads.csv"
new_leads_file = "new_leads.csv"
output_file = r"e:\AgenticSystem\Leadai\Sales-Multi-Agent-AI\data\JewX_Combined_Leads.csv"

# Read existing leads and update company
existing_leads = []
with open(input_file, "r", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        # row[3] is company
        if row[3] == "JewX":
            row[3] = "Tiffany"
        existing_leads.append(row)

# Read new leads
new_leads = []
with open(new_leads_file, "r", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        new_leads.append(row)

# Combine
all_leads = existing_leads + new_leads

# Write back
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(all_leads)

print(f"Total leads: {len(all_leads)}")
