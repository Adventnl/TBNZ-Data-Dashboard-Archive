from pathlib import Path
import sys

import pandas as pd


def inspect_excel(file_path: Path) -> int:
    if not file_path.exists():
        print(f"FILE_NOT_FOUND:{file_path}")
        return 1

    excel = pd.ExcelFile(file_path, engine="openpyxl")
    print("SHEETS=" + ",".join(excel.sheet_names))

    for sheet in excel.sheet_names:
        df = excel.parse(sheet)
        print(f"ROWS:{sheet}={len(df)}")

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_excel.py <excel-path>")
        sys.exit(1)

    target = Path(sys.argv[1]).resolve()
    sys.exit(inspect_excel(target))
