#!/bin/bash
OUTPUT=backend_dump.txt
> "$OUTPUT"

echo "=== STRUKTUR FOLDER APP (backend) ===" >> "$OUTPUT"
find app \( -name __pycache__ -o -name venv -o -name .venv \) -prune -o -print >> "$OUTPUT"

echo "" >> "$OUTPUT"
echo "=== ISI FILE ===" >> "$OUTPUT"

find app \( -name __pycache__ -o -name venv -o -name .venv \) -prune -o -type f \( -name '*.py' \) ! -name '.env*' -print0 | while IFS= read -r -d '' file; do
  echo "" >> "$OUTPUT"
  echo "----------------------------------------" >> "$OUTPUT"
  echo "FILE: $file" >> "$OUTPUT"
  echo "----------------------------------------" >> "$OUTPUT"
  cat "$file" >> "$OUTPUT"
done

echo "Selesai. Baris: $(wc -l < "$OUTPUT")"
echo "Lokasi: $(pwd)/$OUTPUT"
