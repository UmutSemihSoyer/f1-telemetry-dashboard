import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os

# 1. Hide Tkinter's unnecessary main window
root = tk.Tk()
root.withdraw()

# Keep on top
root.attributes('-topmost', True)

print("[SYSTEM] Waiting for file selection... (Select your CSV file from the dialog)")

# 2. Prompt user to select a file
dosya_yolu = filedialog.askopenfilename(
    title="Select Telemetry CSV to Analyze",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)

# 3. Stop system if user cancels
if not dosya_yolu:
    print("❌ File selection canceled. System shutting down.")
    exit()

# Parse filename to print it
dosya_adi = os.path.basename(dosya_yolu)
print(f"\n[PROCESSING] Target Locked: {dosya_adi}")

# 4. Read Data and Extract Anatomy
try:
    df = pd.read_csv(dosya_yolu)
    print("\n✅ FILE LOADED SUCCESSFULLY!")
    
    print("\n--- COLUMN NAMES ---")
    print(list(df.columns))
    
    print(f"\n--- DATA SIZE ---")
    print(f"Total Rows: {len(df)}")
    
    print("\n--- FIRST 3 ROWS PREVIEW ---")
    print(df.head(3))

except Exception as e:
    print(f"\n❌ READ ERROR: Failed to fetch data. Error details:\n{e}")