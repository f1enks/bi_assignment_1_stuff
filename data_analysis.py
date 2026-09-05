import os
import csv
import random
import pandas as pd
from collections import Counter

# file locations and analysis settings

BASE_DIR = r"C:/"

ORIGINALS_DIR = os.path.join(BASE_DIR, "originals")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

POSTINGS_FILE = os.path.join(ORIGINALS_DIR, "linkedin_job_postings.csv")
SKILLS_FILE = os.path.join(ORIGINALS_DIR, "job_skills.csv")
SUMMARY_FILE = os.path.join(ORIGINALS_DIR, "job_summary.csv")

SAMPLE_SIZE = 100_000
RANDOM_SEED = 42
CHUNK_SIZE = 50_000

os.makedirs(SAMPLES_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

random.seed(RANDOM_SEED)

print("LinkedIn dataset analysis")
print("Checking structure, data quality, table relationships and creating a sample.")
print("Original files will not be modified.")

# get column names from a CSV

def get_columns(filepath):
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        return next(reader)

# dataset overview

print("\n[1/7] Reading dataset structure...")

files = {
    "linkedin_job_postings": POSTINGS_FILE,
    "job_skills": SKILLS_FILE,
    "job_summary": SUMMARY_FILE
}

overview_rows = []

for name, filepath in files.items():

    print(f"\nInspecting: {name}")

    columns = get_columns(filepath)

    print("Columns:")
    for col in columns:
        print(f"  - {col}")

    # count rows without loading the whole file
    row_count = 0

    with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
        for _ in f:
            row_count += 1

    # remove the header row
    row_count -= 1

    overview_rows.append({
        "table": name,
        "file": os.path.basename(filepath),
        "rows": row_count,
        "columns": len(columns),
        "column_names": " | ".join(columns)
    })

    print(f"Rows: {row_count:,}")
    print(f"Columns: {len(columns)}")

overview_df = pd.DataFrame(overview_rows)
overview_df.to_csv(
    os.path.join(REPORTS_DIR, "dataset_overview.csv"),
    index=False
)

print("\nDataset overview saved.")

# completeness / missing values

print("\n[2/7] Calculating missing-value statistics...")
print("This may take some time because the full files are being scanned.")

missing_results = []

for name, filepath in files.items():

    print(f"\nProcessing missing values: {name}")

    columns = get_columns(filepath)

    total_rows = 0
    missing_counts = Counter()

    for chunk in pd.read_csv(
        filepath,
        chunksize=CHUNK_SIZE,
        dtype=str,
        low_memory=False,
        encoding="utf-8-sig",
        on_bad_lines="skip"
    ):

        total_rows += len(chunk)

        for col in columns:
            if col in chunk.columns:
                missing_counts[col] += chunk[col].isna().sum()

    for col in columns:

        missing = missing_counts[col]

        missing_results.append({
            "table": name,
            "variable": col,
            "total_rows": total_rows,
            "missing_count": int(missing),
            "missing_percentage": round(
                (missing / total_rows) * 100, 4
            ) if total_rows else None
        })

missing_df = pd.DataFrame(missing_results)

missing_df.to_csv(
    os.path.join(REPORTS_DIR, "missing_values.csv"),
    index=False
)

print("Missing-value report saved.")

# check job_link uniqueness

print("\n[3/7] Checking job_link uniqueness...")

uniqueness_results = []

for name, filepath in files.items():

    print(f"\nChecking: {name}")

    total_rows = 0
    null_links = 0
    link_counter = Counter()

    for chunk in pd.read_csv(
        filepath,
        usecols=["job_link"],
        chunksize=CHUNK_SIZE,
        dtype=str,
        encoding="utf-8-sig",
        on_bad_lines="skip"
    ):

        total_rows += len(chunk)

        null_links += chunk["job_link"].isna().sum()

        # count links across the dataset
        for link in chunk["job_link"].dropna():
            link_counter[link] += 1

    unique_links = len(link_counter)
    duplicate_rows = total_rows - unique_links

    uniqueness_results.append({
        "table": name,
        "total_rows": total_rows,
        "unique_job_links": unique_links,
        "duplicate_rows": duplicate_rows,
        "duplicate_percentage": round(
            (duplicate_rows / total_rows) * 100, 4
        ) if total_rows else None,
        "missing_job_links": int(null_links),
        "missing_job_link_percentage": round(
            (null_links / total_rows) * 100, 4
        ) if total_rows else None
    })

    print(f"Rows: {total_rows:,}")
    print(f"Unique job links: {unique_links:,}")
    print(f"Duplicate rows: {duplicate_rows:,}")
    print(f"Missing links: {null_links:,}")

uniqueness_df = pd.DataFrame(uniqueness_results)

uniqueness_df.to_csv(
    os.path.join(REPORTS_DIR, "uniqueness.csv"),
    index=False
)

print("Uniqueness report saved.")

# check relationships between tables

print("\n[4/7] Checking relationships between tables...")

print("\nCollecting unique job_links from main postings table...")

posting_links = set()

for chunk in pd.read_csv(
    POSTINGS_FILE,
    usecols=["job_link"],
    chunksize=CHUNK_SIZE,
    dtype=str,
    encoding="utf-8-sig",
    on_bad_lines="skip"
):

    posting_links.update(
        chunk["job_link"].dropna().tolist()
    )

print(f"Unique posting links: {len(posting_links):,}")

relationship_results = []

for name, filepath in {
    "job_skills": SKILLS_FILE,
    "job_summary": SUMMARY_FILE
}.items():

    print(f"\nChecking relationship: {name}")

    total_rows = 0
    unique_links = set()
    matched_rows = 0
    unmatched_rows = 0

    for chunk in pd.read_csv(
        filepath,
        usecols=["job_link"],
        chunksize=CHUNK_SIZE,
        dtype=str,
        encoding="utf-8-sig",
        on_bad_lines="skip"
    ):

        total_rows += len(chunk)

        for link in chunk["job_link"].dropna():

            unique_links.add(link)

            if link in posting_links:
                matched_rows += 1
            else:
                unmatched_rows += 1

    relationship_results.append({
        "child_table": name,
        "total_rows": total_rows,
        "unique_job_links": len(unique_links),
        "matched_to_postings": matched_rows,
        "unmatched_to_postings": unmatched_rows,
        "matched_percentage": round(
            (matched_rows / total_rows) * 100, 4
        ) if total_rows else None,
        "unmatched_percentage": round(
            (unmatched_rows / total_rows) * 100, 4
        ) if total_rows else None
    })

    print(f"Rows: {total_rows:,}")
    print(f"Matched: {matched_rows:,}")
    print(f"Unmatched: {unmatched_rows:,}")

relationship_df = pd.DataFrame(relationship_results)

relationship_df.to_csv(
    os.path.join(REPORTS_DIR, "relationships.csv"),
    index=False
)

print("Relationship report saved.")

# create a reproducible sample

print("\n[5/7] Creating reproducible random sample...")

print(f"Target sample size: {SAMPLE_SIZE:,}")
print(f"Random seed: {RANDOM_SEED}")

# sample without loading every link into memory
reservoir = []
seen = 0

for chunk in pd.read_csv(
    POSTINGS_FILE,
    usecols=["job_link"],
    chunksize=CHUNK_SIZE,
    dtype=str,
    encoding="utf-8-sig",
    on_bad_lines="skip"
):

    for link in chunk["job_link"].dropna():

        seen += 1

        if len(reservoir) < SAMPLE_SIZE:
            reservoir.append(link)

        else:
            index = random.randint(0, seen - 1)

            if index < SAMPLE_SIZE:
                reservoir[index] = link

sample_links = set(reservoir)

print(f"Sampled unique job links: {len(sample_links):,}")

# extract matching sample records

print("\n[6/7] Extracting matching sample records...")

def extract_matching_rows(
    input_file,
    output_file,
    table_name
):

    print(f"\nExtracting {table_name}...")

    first_write = True
    extracted = 0

    for chunk in pd.read_csv(
        input_file,
        chunksize=CHUNK_SIZE,
        dtype=str,
        encoding="utf-8-sig",
        low_memory=False,
        on_bad_lines="skip"
    ):

        matched = chunk[
            chunk["job_link"].isin(sample_links)
        ]

        if len(matched) > 0:

            matched.to_csv(
                output_file,
                mode="w" if first_write else "a",
                header=first_write,
                index=False,
                encoding="utf-8-sig"
            )

            first_write = False
            extracted += len(matched)

    print(f"Extracted rows: {extracted:,}")

    return extracted

posting_sample_file = os.path.join(
    SAMPLES_DIR,
    "linkedin_job_postings_sample.csv"
)

skills_sample_file = os.path.join(
    SAMPLES_DIR,
    "job_skills_sample.csv"
)

summary_sample_file = os.path.join(
    SAMPLES_DIR,
    "job_summary_sample.csv"
)

posting_sample_count = extract_matching_rows(
    POSTINGS_FILE,
    posting_sample_file,
    "linkedin_job_postings"
)

skills_sample_count = extract_matching_rows(
    SKILLS_FILE,
    skills_sample_file,
    "job_skills"
)

summary_sample_count = extract_matching_rows(
    SUMMARY_FILE,
    summary_sample_file,
    "job_summary"
)

# basic value frequencies

print("\n[7/7] Calculating useful value frequencies...")

frequency_results = []

# job title frequencies
title_counter = Counter()

for chunk in pd.read_csv(
    POSTINGS_FILE,
    usecols=["job_title"],
    chunksize=CHUNK_SIZE,
    dtype=str,
    encoding="utf-8-sig",
    on_bad_lines="skip"
):

    for value in chunk["job_title"].dropna():
        title_counter[value.strip()] += 1

for value, count in title_counter.most_common(100):

    frequency_results.append({
        "variable": "job_title",
        "value": value,
        "count": count
    })

# job level frequencies
level_counter = Counter()

for chunk in pd.read_csv(
    POSTINGS_FILE,
    usecols=["job_level"],
    chunksize=CHUNK_SIZE,
    dtype=str,
    encoding="utf-8-sig",
    on_bad_lines="skip"
):

    for value in chunk["job_level"].dropna():
        level_counter[value.strip()] += 1

for value, count in level_counter.most_common(100):

    frequency_results.append({
        "variable": "job_level",
        "value": value,
        "count": count
    })

# job type frequencies
type_counter = Counter()

for chunk in pd.read_csv(
    POSTINGS_FILE,
    usecols=["job_type"],
    chunksize=CHUNK_SIZE,
    dtype=str,
    encoding="utf-8-sig",
    on_bad_lines="skip"
):

    for value in chunk["job_type"].dropna():
        type_counter[value.strip()] += 1

for value, count in type_counter.most_common(100):

    frequency_results.append({
        "variable": "job_type",
        "value": value,
        "count": count
    })

frequency_df = pd.DataFrame(frequency_results)

frequency_df.to_csv(
    os.path.join(REPORTS_DIR, "value_frequencies.csv"),
    index=False,
    encoding="utf-8-sig"
)

print("Value frequency report saved.")

# FINISHED

print()
print("Analysis finished.")

print("\nCreated samples:")
print(f"  {posting_sample_file}")
print(f"  {skills_sample_file}")
print(f"  {summary_sample_file}")

print("\nCreated reports:")
for filename in os.listdir(REPORTS_DIR):
    print(f"  {os.path.join(REPORTS_DIR, filename)}")

print()
print("Original files were not modified.")
print("Samples and reports were saved in the output folders.")
