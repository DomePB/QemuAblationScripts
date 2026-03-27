import time
import subprocess
import csv
import os
import uuid
from pathlib import Path

QEMU_BUILDS = [
    "/home/dome/qemu/QemuOptimizerAblationStudy/build-default/",
    "/home/dome/qemu/QemuOptimizerAblationStudy/build-noOptimization/",
    "/home/dome/qemu/QemuOptimizerAblationStudy/build-OMaskFix/",
    "/home/dome/qemu/QemuOptimizerAblationStudy/build-addPatch"
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
        "flags" : ["-m", "16", "-hda"],
    },
    {
        "name" : "target-631",
        "command" : "qemu-system-riscv64",
        "path"  : "/home/dome/benchmarks-dominik/target-631.deepsjeng_s.0/opensbi_linux_payload.elf",
        "flags" : QEMU_ARGS + ["-bios"],
    }
]

MAX_RETRIES = 3
TIMEOUT_SECONDS = 90 * 60 #Sekunden   also gerade 1,5h

def build_cmd(build_path, benchmark):
    build_path = Path(build_path)
    qemu_bin = build_path / benchmark["command"]

    return ([str(qemu_bin)] + benchmark["flags"] + [benchmark["path"]])

def run_benchmark(build, benchmark):
    run_id = str(uuid.uuid4())
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start = time.perf_counter()
            result = subprocess.run(
                build_cmd(build, benchmark),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=TIMEOUT_SECONDS
            )
            end = time.perf_counter()
            execution_time = end - start

            return {
                "run_id": run_id,
                "build": build,
                "binary": benchmark["name"],
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "attempt": attempt,
            }

        except subprocess.TimeoutExpired:
            print(f"  [Attempt {attempt}/{MAX_RETRIES}] TIMEOUT nach {TIMEOUT_SECONDS}s – {benchmark['name']}")

        if attempt < MAX_RETRIES:
            time.sleep(2)  

    print(f"  FEHLGESCHLAGEN nach {MAX_RETRIES} Versuchen: {benchmark['name']}")
    return {
        "run_id": run_id,
        "build": build,
        "binary": benchmark["name"],
        "execution_time": None,
        "return_code": -1,
        "stdout": "",
        "stderr": f"Failed after {MAX_RETRIES} attempts",
        "attempt": MAX_RETRIES,
    }

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
            for i in range(0,1):
                print(f"Running benchmark: {build} with Binary: {benchmark}")
                results.append(run_benchmark(build, benchmark))

    save_cvs(results, "benchmark_results.csv")
    print(f"CSV saved to: benchmark_results.csv")


main()
