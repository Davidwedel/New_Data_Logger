#!/bin/bash

# Interactive XML field inspector
# Shows available dates, then available fields, then prints selected field from all files

cd "$(dirname "$0")/.." || exit 1

# Force dev environment
export DATALOGGER_CONFIG_DIR="$HOME/.datalogger"

# Load config to get XML path
CONFIG_FILE="$HOME/.datalogger/config.json"
XML_DIR=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['xml']['path'])")

echo "================================================================"
echo "XML Field Inspector"
echo "================================================================"
echo "XML Directory: $XML_DIR"
echo ""

# Get list of unique dates from XML filenames
echo "Available dates:"
DATES=$(ls "$XML_DIR"/*.xml 2>/dev/null | xargs -n1 basename | cut -d_ -f1 | cut -c1-8 | sort -u | nl)

if [ -z "$DATES" ]; then
    echo "No XML files found in $XML_DIR"
    exit 1
fi

echo "$DATES"
echo ""
read -p "Select date number: " DATE_NUM

# Get the selected date
SELECTED_DATE=$(echo "$DATES" | sed -n "${DATE_NUM}p" | awk '{print $2}')

if [ -z "$SELECTED_DATE" ]; then
    echo "Invalid selection"
    exit 1
fi

echo ""
echo "Selected date: $SELECTED_DATE"
echo ""

# Get list of XML files for this date
XML_FILES=("$XML_DIR/${SELECTED_DATE}"*.xml)

if [ ! -f "${XML_FILES[0]}" ]; then
    echo "No files found for date $SELECTED_DATE"
    exit 1
fi

echo "Found ${#XML_FILES[@]} files for this date"
echo ""

# Parse first file to get available fields
echo "Available fields (from first file):"
FIELDS=$(python3 <<EOF
import xml.etree.ElementTree as ET
import sys

tree = ET.parse("${XML_FILES[0]}")
root = tree.getroot()

fields = []
def get_paths(element, path=""):
    current_path = f"{path}/{element.tag}" if path else element.tag
    if element.text and element.text.strip() and len(element) == 0:
        fields.append(current_path)
    for child in element:
        get_paths(child, current_path)

get_paths(root)
for i, field in enumerate(sorted(fields), 1):
    print(f"{i:3d}. {field}")
EOF
)

echo "$FIELDS"
echo ""
read -p "Select field number: " FIELD_NUM

# Get the selected field path
SELECTED_FIELD=$(echo "$FIELDS" | sed -n "${FIELD_NUM}p" | awk '{print $2}')

if [ -z "$SELECTED_FIELD" ]; then
    echo "Invalid selection"
    exit 1
fi

echo ""
echo "================================================================"
echo "Field: $SELECTED_FIELD"
echo "Date: $SELECTED_DATE"
echo "================================================================"
echo ""

# Create temp file with file list
TEMP_FILE=$(mktemp)
printf "%s\n" "${XML_FILES[@]}" > "$TEMP_FILE"

# Extract and display the selected field from all files
python3 - "$TEMP_FILE" "$SELECTED_FIELD" <<'EOF'
import xml.etree.ElementTree as ET
import sys

temp_file = sys.argv[1]
field_path = sys.argv[2]

# Read file list from temp file
with open(temp_file, "r") as f:
    files = [line.strip() for line in f if line.strip()]

print(f"{'Filename':<30} {'Time':<10} {'Value'}")
print("-" * 60)

for filepath in sorted(files):
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Remove root element name from path (e.g., "XMLExport/General/Time" -> "General/Time")
        path_parts = field_path.split('/')
        if path_parts[0] == root.tag:
            search_path = '/'.join(path_parts[1:])
        else:
            search_path = field_path

        # Get the field value using the path relative to root
        element = root.find(f"./{search_path}")
        value = element.text if element is not None else "N/A"

        # Get time from General/Time if available
        time_elem = root.find(".//General/Time")
        time_str = time_elem.text if time_elem is not None else "?"

        # Get just the filename
        filename = filepath.split('/')[-1]

        print(f"{filename:<30} {time_str:<10} {value}")
    except Exception as e:
        filename = filepath.split('/')[-1]
        print(f"{filename}: Error - {e}", file=sys.stderr)

EOF

# Clean up temp file
rm -f "$TEMP_FILE"

echo ""
echo "================================================================"
