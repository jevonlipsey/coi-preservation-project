import os
import re
import pandas as pd

def is_public_comment_file(filename):
    """
    checks if the file is an excel file and contains the words
    'public comment' or 'public comments' in a case-insensitive way.
    """
    if not filename.lower().endswith('.xlsx'):
        return False
    
    # strip all weird chars
    normalized = filename.lower().replace(' ', '').replace('-', '').replace('_', '')

    return 'publiccomment' in normalized

def sanitize_name(name):
    """
    sanitizes file and sheet names for file paths.
    """
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    return name.strip()

def process_xlsx_files(source_dirs, output_dir):
    """
    walks through the source directories, finds matching excel files,
    and exports all sheets from each file to csv format in output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    processed_count = 0
    csv_count = 0
    
    for src_dir in source_dirs:
        if not os.path.exists(src_dir):
            print(f"directory '{src_dir}' does not exist.")
            continue
            
        print(f"searching in {src_dir}...")
        for root, _, files in os.walk(src_dir):
            for file in files:
                if is_public_comment_file(file):
                    file_path = os.path.join(root, file)
                    base_name = os.path.splitext(file)[0]
                    
                    print(f"processing excel file {file}")
                    try:
                        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
                        
                        for sheet_name in excel_file.sheet_names:
                            df = excel_file.parse(sheet_name)
                            clean_base = sanitize_name(base_name)
                            clean_sheet = sanitize_name(sheet_name)
                            csv_filename = f"{clean_base} - {clean_sheet}.csv"
                            csv_path = os.path.join(output_dir, csv_filename)

                            df.to_csv(csv_path, index=False)
                            print(f"  -> exported sheet {sheet_name} to {csv_filename}")
                            csv_count += 1
                            
                        processed_count += 1
                    except Exception as e:
                        print(f"error processing {file_path}: {e}")
                        
    print(f"\nprocessed {processed_count} excel files, generated {csv_count} csv files in {output_dir}")

if __name__ == '__main__':
    search_folders = [
        ## put folders here
    ]
    destination_folder = 'data/public-comments'
    
    process_xlsx_files(search_folders, destination_folder)
