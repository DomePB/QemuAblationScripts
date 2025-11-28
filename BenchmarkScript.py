import time
import subprocess
import csv
import os
import uuid
from pathlib import Path

QEMU_BUILDS = [
    "/home/dome/qemu/QemuOptimizerAblationStudy/build/qemu-system-riscv64"
]

QEMU_ARGS = [
    "-machine", "virt",
    "-cpu", "rv64,h=true",
    "-m", "16384M",
    "-display", "none",
    "-serial", "stdio"
]

BINARIES = [
    "/home/dome/benchmarks-dominik/opensbi_linux_payload.elf"
]

def run_benchmark(build, binary):
    run_id = str(uuid.uuid4())
    start = time.perf_counter()

    result = subprocess.run([build] + QEMU_ARGS + ["-bios", str(binary)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    end = time.perf_counter()
    execution_time = end - start

    return {"run_id": run_id,
            "build": build,
            "binary": binary,
            "execution_time": execution_time,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr}

def save_cvs(results, path):
    fields = ["run_id", "build", "binary", "execution_time", "return_code"]
    file_path = Path(path).resolve()
    file_exists = file_path.is_file()
    
    with open(path, "a", newline="")as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        
        if not file_exists:
            writer.writeheader()

        for r in results:
            writer.writerow({k: r[k] for k in fields})


def main():
    results = []
    for build in QEMU_BUILDS:
        for binary in BINARIES:
            print(f"Running benchmark: {build} with Binary: {binary}")
            results.append(run_benchmark(os.path.abspath(build), os.path.abspath(binary)))

    save_cvs(results, "benchmark_results.csv")
    print(f"CSV saved to: benchmark_results.csv")


main()