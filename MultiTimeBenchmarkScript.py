import subprocess
import csv
import os
import re
from datetime import datetime

def run_multitime_qemuriscv64(run_id, num_runs, bios_path, output_csv="multitime_results.csv"):
    cmd = [
        "multitime",
        "-n", str(num_runs),
        "./qemu-system-riscv64",
        "-machine", "virt",
        "-cpu", "rv64,h=true",
        "-m", "16384M",
        "-display", "none",
        "-serial", "stdio",
        "-bios", bios_path
    ]

    print("running command: ".join(cmd))

    process = subprocess.run(cmd, capture_output=True, text=True)

    if process.returncode != 0:
        print("Error running Cmd")
        print(process.stderr)
        return

    output= process.stdout
    print("Command Finished")

    pattern = re.compile(
        r"^(real|user|sys)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
        re.MULTILINE
    )

    rows = pattern.findall(output)

    if not rows:
        print("Could not find timing table in output.")
        print("Raw Output:")
        print(output)
        return
    
    file_exists = os.path.exists(output_csv)

    
    with open(output_csv, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)

        if not file_exists:
            writer.writerow(["RunID", "Type", "Mean", "StdDev", "Min", "Median", "Max"])

        for r in rows:
            writer.writerow([run_id] + list(r))

    print(f"Results appended to {output_csv}")


run_id = datetime.now()

run_multitime_qemuriscv64(run_id, 5, "/home/dome/benchmarks-dominik/opensbi_linux_payload.elf")