import time
import subprocess
import csv
import os
import uuid
from pathlib import Path

QEMU_BUILDS = [
    "/home/dome/qemu/QemuOptimizerAblationStudy/build-default/",
    "/home/dome/qemu/QemuOptimizerAblationStudy/build-noOptimization/",
    "/home/dome/qemu/QemuOptimizerAblationStudy/build-defaultSMask/"
]

QEMU_ARGS = [
    "-machine", "virt",
    "-cpu", "rv64,h=true",
    "-m", "16384M",
    "-display", "none",
    "-serial", "stdio"
]

BENCHMARKS = [
    {
        "name" : "opensbi_linux_payload.elf",
        "command" : "qemu-system-riscv64",
        "path" : "/home/dome/benchmarks-dominik/opensbi_linux_payload.elf",
        "flags" : QEMU_ARGS + ["-bios"],
    },
    {
        "name" : "dos-benchmark",
        "command" : "qemu-system-i386",
        "path" : "/home/dome/qemu/Qemu-Images/freedos.img",
        "flags" : ["-m", "16", "-enable-kvm", "-hda"],
    }
]

def build_cmd(build_path, benchmark):
    build_path = Path(build_path)
    qemu_bin = build_path / benchmark["command"]

    return ([str(qemu_bin)] + benchmark["flags"] + [benchmark["path"]])

def run_benchmark(build, benchmark):
    run_id = str(uuid.uuid4())
    start = time.perf_counter()

    result = subprocess.run(build_cmd(build, benchmark), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    end = time.perf_counter()
    execution_time = end - start

    return {"run_id": run_id,
            "build": build,
            "binary": benchmark["name"],
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
    for benchmark in BENCHMARKS:
        for build in QEMU_BUILDS:
            print(f"Running benchmark: {build} with Binary: {benchmark}")
            results.append(run_benchmark(build, benchmark))

    save_cvs(results, "benchmark_results.csv")
    print(f"CSV saved to: benchmark_results.csv")


main()
