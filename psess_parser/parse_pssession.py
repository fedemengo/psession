#!/usr/bin/env python3
"""
Parser for PalmSens .pssession files to convert to pandas DataFrame.
Handles UTF-16 encoded JSON-like data format.
"""

import json
import pandas as pd
import argparse
from pathlib import Path


def parse_pssession_file(file_path):
    """
    Parse a .pssession file and convert to pandas DataFrame.

    Args:
        file_path (str): Path to the .pssession file

    Returns:
        pd.DataFrame: Parsed data as DataFrame
    """
    # Read the UTF-16 encoded file
    try:
        with open(file_path, "r", encoding="utf-16") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try UTF-16-LE if UTF-16 fails
        with open(file_path, "r", encoding="utf-16-le") as f:
            content = f.read()

    # Parse JSON content - handle potential extra data at the end
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        # Try to find the JSON end and parse only the valid part
        try:
            # Find the last closing brace that completes the JSON
            brace_count = 0
            json_end = -1
            for i, char in enumerate(content):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

            if json_end > 0:
                json_content = content[:json_end]
                data = json.loads(json_content)
            else:
                print(f"Could not find valid JSON structure: {e}")
                return None
        except json.JSONDecodeError as e2:
            print(f"Error parsing JSON even after truncation: {e2}")
            return None

    # Extract measurement data
    if "Measurements" not in data or not data["Measurements"]:
        print("No measurements found in the file")
        return None

    print(f"Found {len(data['Measurements'])} measurements in the file")

    # Process all measurements
    all_dataframes = []

    for measurement_idx, measurement in enumerate(data["Measurements"]):
        print(
            f"Processing measurement {measurement_idx}: {measurement.get('Title', 'Unknown')}"
        )

        dataset = measurement.get("DataSet", {})
        values = dataset.get("Values", [])

        # Convert to DataFrame
        df_data = {}

        for value_array in values:
            description = value_array.get("Description", "Unknown")
            array_type = value_array.get("ArrayType", 0)
            unit = value_array.get("Unit", {})
            unit_symbol = unit.get("S", "")
            unit_quantity = unit.get("Q", "")
            data_values = value_array.get("DataValues", [])

            # Extract values based on data structure
            if data_values:
                # Check if it's a simple value or complex structure
                first_value = data_values[0]
                if isinstance(first_value, dict):
                    if "V" in first_value:
                        # Extract 'V' values (voltage/current/impedance data)
                        column_name = (
                            f"{description} ({unit_symbol})"
                            if unit_symbol
                            else description
                        )
                        df_data[column_name] = [val.get("V", 0) for val in data_values]

                        # Also extract other fields if they exist
                        if "C" in first_value:
                            df_data[f"{description}_Range"] = [
                                val.get("C", 0) for val in data_values
                            ]
                        if "S" in first_value:
                            df_data[f"{description}_Status"] = [
                                val.get("S", 0) for val in data_values
                            ]
                        if "R" in first_value:
                            df_data[f"{description}_R"] = [
                                val.get("R", 0) for val in data_values
                            ]
                        if "T" in first_value:
                            df_data[f"{description}_Text"] = [
                                val.get("T", "") for val in data_values
                            ]
                else:
                    # Simple list of values
                    column_name = (
                        f"{description} ({unit_symbol})" if unit_symbol else description
                    )
                    df_data[column_name] = data_values

        # Create DataFrame for this measurement
        if df_data:
            df = pd.DataFrame(df_data)

            # Add metadata as attributes
            df.attrs["measurement_index"] = measurement_idx
            df.attrs["title"] = measurement.get("Title", "Unknown")
            df.attrs["timestamp"] = measurement.get("TimeStamp", "")
            df.attrs["device_used"] = measurement.get("DeviceUsed", "")
            df.attrs["device_serial"] = measurement.get("DeviceSerial", "")
            df.attrs["device_fw"] = measurement.get("DeviceFW", "")

            all_dataframes.append(df)
            print(f"  -> Extracted {df.shape[0]} data points, {df.shape[1]} columns")
        else:
            print(f"  -> No data could be extracted from measurement {measurement_idx}")

    # Return all dataframes
    if len(all_dataframes) == 1:
        return all_dataframes[0]
    elif len(all_dataframes) > 1:
        return all_dataframes
    else:
        print("No data could be extracted from any measurement")
        return None


def main():
    """Main function to parse command line arguments and run the parser."""
    parser = argparse.ArgumentParser(
        description="Parse PalmSens .pssession files to pandas DataFrame"
    )
    parser.add_argument("input_file", help="Path to the .pssession file")
    parser.add_argument("-o", "--output", help="Output CSV file path (optional)")
    parser.add_argument(
        "--info", action="store_true", help="Show DataFrame info and preview"
    )
    parser.add_argument(
        "-m",
        "--measurement",
        type=int,
        help="Select specific measurement index (0-based)",
    )
    parser.add_argument(
        "--list-measurements",
        action="store_true",
        help="List all measurements and exit",
    )

    args = parser.parse_args()

    # Parse the file
    result = parse_pssession_file(args.input_file)

    if result is not None:
        print(f"Successfully parsed {args.input_file}")

        # Handle multiple measurements
        if isinstance(result, list):
            dataframes = result
            print(f"Found {len(dataframes)} measurements")

            if args.list_measurements:
                print("\nAvailable measurements:")
                for i, df in enumerate(dataframes):
                    print(
                        f"  {i}: {df.attrs['title']} ({df.shape[0]} points, {df.shape[1]} columns)"
                    )
                return dataframes

            # Select specific measurement or use first one
            if args.measurement is not None:
                if 0 <= args.measurement < len(dataframes):
                    df = dataframes[args.measurement]
                    print(
                        f"Selected measurement {args.measurement}: {df.attrs['title']}"
                    )
                else:
                    print(
                        f"Error: measurement index {args.measurement} out of range (0-{len(dataframes) - 1})"
                    )
                    return None
            else:
                df = dataframes[0]
                print(f"Using first measurement: {df.attrs['title']}")
                print("(Use --list-measurements to see all available measurements)")
        else:
            df = result

        print(f"DataFrame shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")

        if args.info:
            print("\nDataFrame Info:")
            print(df.info())
            print("\nFirst few rows:")
            print(df.head())
            print("\nMetadata:")
            for key, value in df.attrs.items():
                print(f"  {key}: {value}")

        if args.output:
            df.to_csv(args.output, index=False)
            print(f"Saved to {args.output}")

        return df if not isinstance(result, list) else result
    else:
        print("Failed to parse the file")
        return None


if __name__ == "__main__":
    main()
