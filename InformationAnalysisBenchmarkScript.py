import os
import subprocess
import re
from collections import Counter


QEMU_BUILDS = [
    "/home/dome/qemu/QemuOptimizerAblationStudy/build-informationStudy/qemu-system-riscv64"
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

MASK_RE = re.compile(
    r"fold_masks_zosa_int:\s*z:\s*([0-9a-fA-F]+)\s*"
    r"o:\s*([0-9a-fA-F]+)\s*s:\s*([0-9a-fA-F]+)\s*a:\s*([0-9a-fA-F]+)"
)

Z_DEFAULT = 0xffffffffffffffff
O_DEFAULT = 0x0000000000000000
S_DEFAULT = 0x0000000000000000
A_DEFAULT = 0xffffffffffffffff



def analyze_masks(z, o, s, a):

    info_z = z != Z_DEFAULT
    info_o = o != O_DEFAULT
    info_s = s != S_DEFAULT
    info_a = a != A_DEFAULT
       
    return info_z, info_o, info_s, info_a


def run_benchmark(build, binary):
    print(f"\n--- Running {build} with binary {binary} ---")

    proc = subprocess.Popen(
        [build] + QEMU_ARGS + ["-bios", binary],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    stats = Counter()
    lines = 0

    for line in proc.stdout:
        match = MASK_RE.search(line)
        if match:
            lines += 1

            z = int(match.group(1), 16)
            o = int(match.group(2), 16)
            s = int(match.group(3), 16)
            a = int(match.group(4), 16)

            info_z, info_o, info_s, info_a = analyze_masks(z, o, s, a)

            stats["z"] += info_z
            stats["o"] += info_o
            stats["s"] += info_s
            stats["a"] += info_a

    proc.wait()

    print(f"Done. Parsed mask lines: {lines}")

    if lines > 0:
        print("\n--- Mask Information Summary ---")
        print(f"Lines Count: {lines}")
        print(f"Non Default Z bits: {stats['z']}. Percentage of Z we have Information about: {stats['z'] / lines:.2f} ")
        print(f"Non Default O bits: {stats['o']}. Percentage of O we have Information about: {stats['o'] / lines:.2f}")
        print(f"Non Default S bits: {stats['s']}. Percentage of S we have Information about: {stats['s'] / lines:.2f}")
        print(f"Non Default A bits: {stats['a']}. Percentage of A we have Information about: {stats['a'] / lines:.2f}")
    else:
        print("No fold_masks_zosa_int lines found!")

    print("--------------------------------\n")


def main():
    for build in QEMU_BUILDS:
        for binary in BINARIES:
            run_benchmark(os.path.abspath(build), os.path.abspath(binary))


main()