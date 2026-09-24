"""
Excel Ledger Analysis Script

This script analyzes the SEZ Stock Ledger Excel file to document its structure,
formulas, formatting, and patterns. Run this via Docker:

    docker-backend.bat python -m app.analyze_ledger
"""

import sys
from pathlib import Path
try:
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    from openpyxl.utils import get_column_letter, column_index_from_string
except ImportError:
    print("openpyxl not installed. Install with: pip install openpyxl")
    sys.exit(1)


def analyze_ledger(excel_path: Path) -> dict:
    """Analyze the Excel ledger structure and return detailed findings."""
    print(f"Analyzing: {excel_path}")
    print("=" * 80)

    wb = load_workbook(excel_path, data_only=False)
    findings = {
        "file_info": {},
        "sheet1": {},
        "sheet2": {},
        "patterns": {},
        "inconsistencies": []
    }

    # File info
    findings["file_info"] = {
        "filename": excel_path.name,
        "sheet_names": wb.sheetnames,
        "active_sheet": wb.active.title if wb.active else None
    }

    # Analyze Sheet1 (main ledger)
    if "Sheet1" in wb.sheetnames:
        ws1 = wb["Sheet1"]
        findings["sheet1"] = analyze_sheet1(ws1)

    # Analyze Sheet2 (if exists)
    if "Sheet2" in wb.sheetnames:
        ws2 = wb["Sheet2"]
        findings["sheet2"] = analyze_sheet2(ws2)

    # Analyze patterns
    findings["patterns"] = analyze_patterns(wb)

    wb.close()
    return findings


def analyze_sheet1(ws) -> dict:
    """Analyze Sheet1 structure."""
    print("\nAnalyzing Sheet1...")
    sheet_info = {
        "dimensions": ws.dimensions,
        "max_row": ws.max_row,
        "max_column": ws.max_column,
        "freeze_panes": ws.freeze_panes,
        "headers": {},
        "column_formats": {},
        "cell_styles": {},
        "formulas": {},
        "data_patterns": {}
    }

    # Analyze headers (assuming row 1-2)
    print("Analyzing headers...")
    for row in range(1, min(3, ws.max_row + 1)):
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=row, column=col)
            if cell.value:
                col_letter = get_column_letter(col)
                sheet_info["headers"][f"{col_letter}{row}"] = {
                    "value": str(cell.value),
                    "font": str(cell.font),
                    "fill": str(cell.fill),
                    "alignment": str(cell.alignment)
                }

    # Analyze column widths
    print("Analyzing column widths...")
    for col in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col)
        if col_letter in ws.column_dimensions:
            sheet_info["column_formats"][col_letter] = {
                "width": ws.column_dimensions[col_letter].width,
                "hidden": ws.column_dimensions[col_letter].hidden
            }

    # Analyze a sample of cells for formatting
    print("Analyzing cell formatting...")
    sample_rows = [1, 2, 3, 10, 17]  # Sample different row types
    for row in sample_rows:
        if row <= ws.max_row:
            for col in range(1, min(27, ws.max_column + 1)):  # A-Z
                cell = ws.cell(row=row, column=col)
                col_letter = get_column_letter(col)
                if cell.value or cell.style:
                    sheet_info["cell_styles"][f"{col_letter}{row}"] = {
                        "value": str(cell.value) if cell.value else None,
                        "number_format": cell.number_format,
                        "font": str(cell.font),
                        "fill": str(cell.fill),
                        "border": str(cell.border),
                        "alignment": str(cell.alignment)
                    }

    # Analyze formulas in key columns (W, X, Y, Z, U, V, R)
    print("Analyzing formulas...")
    formula_columns = ['W', 'X', 'Y', 'Z', 'U', 'V', 'R']
    for col_letter in formula_columns:
        try:
            col_num = column_index_from_string(col_letter)  # Get column number
        except:
            continue
        formulas = []
        for row in range(1, ws.max_row + 1):
            cell = ws.cell(row=row, column=col_num)
            if cell.data_type == 'f':  # Formula
                formulas.append({
                    "cell": f"{col_letter}{row}",
                    "formula": cell.value,
                    "value": str(cell.displayed_value) if hasattr(cell, 'displayed_value') else None
                })
        if formulas:
            sheet_info["formulas"][col_letter] = formulas

    # Analyze data patterns
    print("Analyzing data patterns...")
    sheet_info["data_patterns"] = analyze_data_patterns(ws)

    return sheet_info


def analyze_sheet2(ws) -> dict:
    """Analyze Sheet2 structure."""
    print("\nAnalyzing Sheet2...")
    sheet_info = {
        "dimensions": ws.dimensions,
        "max_row": ws.max_row,
        "max_column": ws.max_column,
        "sample_data": []
    }

    # Sample first 20 rows
    for row in range(1, min(21, ws.max_row + 1)):
        row_data = []
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=row, column=col)
            row_data.append(str(cell.value) if cell.value else None)
        if any(row_data):  # Only add non-empty rows
            sheet_info["sample_data"].append(row_data)

    return sheet_info


def analyze_data_patterns(ws) -> dict:
    """Analyze data patterns in the ledger."""
    patterns = {
        "units": set(),
        "countries": set(),
        "balance_formula_locations": {},
        "group_structure": []
    }

    # Sample data for Units (column I) and Countries (column G)
    col_i = column_index_from_string('I')
    col_g = column_index_from_string('G')

    for row in range(3, min(100, ws.max_row + 1)):  # Skip headers
        # Unit column
        cell_i = ws.cell(row=row, column=col_i)
        if cell_i.value and str(cell_i.value).strip():
            patterns["units"].add(str(cell_i.value).strip())

        # Country column
        cell_g = ws.cell(row=row, column=col_g)
        if cell_g.value and str(cell_g.value).strip():
            patterns["countries"].add(str(cell_g.value).strip())

    # Analyze balance formula locations (W, X, Y, Z)
    balance_cols = ['W', 'X', 'Y', 'Z']
    for col_letter in balance_cols:
        try:
            col_num = column_index_from_string(col_letter)
        except:
            continue
        formula_rows = []
        for row in range(1, ws.max_row + 1):
            cell = ws.cell(row=row, column=col_num)
            if cell.data_type == 'f':
                formula_rows.append(row)
        if formula_rows:
            patterns["balance_formula_locations"][col_letter] = formula_rows

    return patterns


def analyze_patterns(wb) -> dict:
    """Analyze cross-sheet patterns and formulas."""
    patterns = {
        "formula_analysis": {},
        "structural_patterns": {}
    }

    if "Sheet1" in wb.sheetnames:
        ws = wb["Sheet1"]

        # Analyze formula patterns in balance columns
        patterns["formula_analysis"] = analyze_formula_patterns(ws)

        # Analyze structural patterns (groups, continuations)
        patterns["structural_patterns"] = analyze_structural_patterns(ws)

    return patterns


def analyze_formula_patterns(ws) -> dict:
    """Analyze formula patterns in the ledger."""
    formula_analysis = {
        "balance_formulas": {},  # W, X, Y, Z
        "proration_formulas": {},  # U, V, R
        "inconsistencies": []
    }

    # Analyze balance formulas (W, X, Y, Z)
    for col_letter in ['W', 'X', 'Y', 'Z']:
        try:
            col_num = column_index_from_string(col_letter)
        except:
            continue
        formulas = {}
        for row in range(1, ws.max_row + 1):
            cell = ws.cell(row=row, column=col_num)
            if cell.data_type == 'f':
                formula = str(cell.value)
                if formula not in formulas:
                    formulas[formula] = []
                formulas[formula].append(row)
        formula_analysis["balance_formulas"][col_letter] = formulas

    # Analyze proration formulas (U, V, R)
    for col_letter in ['U', 'V', 'R']:
        try:
            col_num = column_index_from_string(col_letter)
        except:
            continue
        formulas = {}
        hardcoded_count = 0
        ratio_count = 0
        for row in range(1, ws.max_row + 1):
            cell = ws.cell(row=row, column=col_num)
            if cell.data_type == 'f':
                formula = str(cell.value)
                if '=K2' in formula or '=L2' in formula:
                    hardcoded_count += 1
                elif '/J' in formula:
                    ratio_count += 1
                if formula not in formulas:
                    formulas[formula] = []
                formulas[formula].append(row)
        formula_analysis["proration_formulas"][col_letter] = {
            "formulas": formulas,
            "hardcoded_count": hardcoded_count,
            "ratio_count": ratio_count
        }

    return formula_analysis


def analyze_structural_patterns(ws) -> dict:
    """Analyze structural patterns like import groups and continuation rows."""
    patterns = {
        "import_groups": [],
        "continuation_patterns": {},
        "blank_continuation_count": 0,
        "fully_populated_count": 0
    }

    # Analyze continuation row patterns (A, C, D, E blank on 2nd+ items)
    for row in range(3, min(50, ws.max_row + 1)):
        a_cell = ws.cell(row=row, column=1)  # A
        c_cell = ws.cell(row=row, column=3)  # C
        d_cell = ws.cell(row=row, column=4)  # D
        e_cell = ws.cell(row=row, column=5)  # E

        is_blank_continuation = (
            not a_cell.value and
            not c_cell.value and
            not d_cell.value and
            not e_cell.value
        )

        if is_blank_continuation:
            patterns["blank_continuation_count"] += 1
        else:
            patterns["fully_populated_count"] += 1

    return patterns


def generate_markdown_report(findings: dict, output_path: Path):
    """Generate a comprehensive markdown report."""
    print(f"\nGenerating report: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# SEZ Stock Ledger Analysis Report\n\n")
        f.write(f"**Generated:** {findings['file_info']['filename']}\n\n")

        # File Information
        f.write("## File Information\n\n")
        f.write(f"- **Filename:** {findings['file_info']['filename']}\n")
        f.write(f"- **Sheets:** {', '.join(findings['file_info']['sheet_names'])}\n")
        f.write(f"- **Active Sheet:** {findings['file_info']['active_sheet']}\n\n")

        # Sheet1 Analysis
        if findings['sheet1']:
            f.write("## Sheet1 Analysis\n\n")
            s1 = findings['sheet1']

            f.write("### Dimensions\n\n")
            f.write(f"- **Max Row:** {s1['max_row']}\n")
            f.write(f"- **Max Column:** {s1['max_column']}\n")
            f.write(f"- **Freeze Panes:** {s1['freeze_panes']}\n\n")

            f.write("### Headers\n\n")
            f.write("| Cell | Value | Font | Fill | Alignment |\n")
            f.write("|------|-------|------|------|-----------|\n")
            for cell_ref, info in s1['headers'].items():
                f.write(f"| {cell_ref} | {info['value'][:30]} | {info['font'][:30]} | {info['fill'][:30]} | {info['alignment'][:30]} |\n")
            f.write("\n")

            f.write("### Column Formats\n\n")
            f.write("| Column | Width | Hidden |\n")
            f.write("|--------|-------|--------|\n")
            for col, info in s1['column_formats'].items():
                f.write(f"| {col} | {info['width']} | {info['hidden']} |\n")
            f.write("\n")

            f.write("### Formula Analysis\n\n")
            for col, formulas in s1['formulas'].items():
                f.write(f"#### {col} Column Formulas\n\n")
                for formula_info in formulas[:5]:  # Show first 5
                    f.write(f"- **{formula_info['cell']}:** `{formula_info['formula']}`\n")
                if len(formulas) > 5:
                    f.write(f"- ... and {len(formulas) - 5} more\n")
                f.write("\n")

            f.write("### Data Patterns\n\n")
            patterns = s1['data_patterns']
            f.write(f"**Unique Units found:** {', '.join(sorted(patterns['units']))}\n\n")
            f.write(f"**Unique Countries found:** {', '.join(sorted(patterns['countries']))}\n\n")

            f.write("### Balance Formula Locations\n\n")
            for col, rows in patterns['balance_formula_locations'].items():
                f.write(f"**{col} column:** Formulas in rows {', '.join(map(str, rows[:10]))}")
                if len(rows) > 10:
                    f.write(f" ... and {len(rows) - 10} more")
                f.write("\n")

        # Sheet2 Analysis
        if findings['sheet2']:
            f.write("## Sheet2 Analysis\n\n")
            s2 = findings['sheet2']
            f.write(f"**Dimensions:** {s2['dimensions']}\n")
            f.write(f"**Max Row:** {s2['max_row']}\n")
            f.write(f"**Max Column:** {s2['max_column']}\n\n")

            f.write("### Sample Data (first 20 rows)\n\n")
            for i, row_data in enumerate(s2['sample_data'][:10], 1):
                f.write(f"**Row {i}:** `{'; '.join([str(x) if x else '' for x in row_data])}`\n")

        # Pattern Analysis
        if findings['patterns']:
            f.write("## Pattern Analysis\n\n")

            if findings['patterns']['formula_analysis']:
                fa = findings['patterns']['formula_analysis']
                f.write("### Formula Patterns\n\n")

                f.write("#### Balance Formulas (W, X, Y, Z)\n\n")
                for col, formulas in fa['balance_formulas'].items():
                    f.write(f"**{col} column:**\n")
                    for formula, rows in formulas.items():
                        f.write(f"- `{formula}` (used in {len(rows)} rows)\n")
                    f.write("\n")

                f.write("#### Proration Formulas (U, V, R)\n\n")
                for col, info in fa['proration_formulas'].items():
                    f.write(f"**{col} column:**\n")
                    f.write(f"- Hardcoded formulas (=K2, etc.): {info['hardcoded_count']}\n")
                    f.write(f"- Ratio formulas (/J): {info['ratio_count']}\n")
                    for formula, rows in info['formulas'].items():
                        f.write(f"- `{formula}` (used in {len(rows)} rows)\n")
                    f.write("\n")

            if findings['patterns']['structural_patterns']:
                sp = findings['patterns']['structural_patterns']
                f.write("### Structural Patterns\n\n")
                f.write(f"- **Blank continuation rows:** {sp['blank_continuation_count']}\n")
                f.write(f"- **Fully populated rows:** {sp['fully_populated_count']}\n\n")

        # Inconsistencies and Notes
        f.write("## Key Findings and Inconsistencies\n\n")
        f.write("### Formula Placement\n\n")
        f.write("The analysis reveals the following about balance formula placement:\n")
        f.write("- Check whether W/X/Y/Z formulas appear on the first row of each group or the last row\n")
        f.write("- Note any inconsistencies in formula patterns\n\n")

        f.write("### Proration Formula Patterns\n\n")
        f.write("- Document whether U/V/R use ratio formulas consistently or have hardcoded values\n")
        f.write("- Note any exceptions to the expected pattern\n\n")

        f.write("### Continuation Style\n\n")
        f.write("- The ledger uses " + ("blank continuation style" if findings['patterns']['structural_patterns']['blank_continuation_count'] > findings['patterns']['structural_patterns']['fully_populated_count'] else "fully populated rows") + "\n\n")

        f.write("## Recommendations\n\n")
        f.write("Based on this analysis:\n")
        f.write("1. Replicate the dominant formula pattern for balance calculations\n")
        f.write("2. Use the continuation style that matches the original file\n")
        f.write("3. Preserve the exact header text and formatting\n")
        f.write("4. Match the column widths and cell styles\n\n")


def main():
    """Main execution function."""
    # Get the Excel file path
    resources_dir = Path(__file__).parent.parent.parent / "resources"
    excel_file = resources_dir / "Seza_Stock_Ledger_Hackathon.xlsx"

    if not excel_file.exists():
        print(f"Error: Excel file not found at {excel_file}")
        print("Please ensure the file is in the resources/ directory")
        sys.exit(1)

    # Analyze the ledger
    findings = analyze_ledger(excel_file)

    # Generate report
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_path = docs_dir / "ledger_analysis.md"

    generate_markdown_report(findings, report_path)

    print(f"\nAnalysis complete! Report saved to: {report_path}")
    print("\nKey findings:")
    print(f"- File: {findings['file_info']['filename']}")
    print(f"- Sheets: {', '.join(findings['file_info']['sheet_names'])}")
    if findings['sheet1']:
        print(f"- Sheet1 max row: {findings['sheet1']['max_row']}")
        print(f"- Sheet1 max column: {findings['sheet1']['max_column']}")


if __name__ == "__main__":
    main()
