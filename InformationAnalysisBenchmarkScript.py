import os
import subprocess
import re
from collections import Counter
from pathlib import Path
import matplotlib.pyplot as plt

from BenchmarkScript import BENCHMARKS

QEMU_BUILDS = [
    "/home/dome/qemu/QemuOptimizerAblationStudy/build-informationStudy/"
]

QEMU_ARGS = [
    "-machine", "virt",
    "-cpu", "rv64,h=true",
    "-m", "16384M",
    "-display", "none",
    "-serial", "stdio"
]


MASK_RE = re.compile(
    r"fold_masks_zosa_int:\s*"
    r"op:\s*(\S+)\s*"
    r"z:\s*([0-9a-fA-F]+)\s*"
    r"o:\s*([0-9a-fA-F]+)\s*s:\s*([0-9a-fA-F]+)\s*a:\s*([0-9a-fA-F]+)"
)

FINISH_RE = re.compile(
    r"finish_folding:\s*op:\s*(\S+)"
)


Z_DEFAULT = 0xffffffffffffffff
O_DEFAULT = 0x0000000000000000
S_DEFAULT = 0x0000000000000000
A_DEFAULT = 0xffffffffffffffff


def plot_histogram(hist, output_path):
    x = list(range(65))
    y = [hist.get(i, 0) for i in x]

    plt.figure()
    plt.bar(x, y)
    plt.xlabel("Number of Default Bits")
    plt.ylabel("Amount")
    plt.title("Default Bits")
    plt.xticks(range(0, 65, max(1, 64 // 8)))
    plt.tight_layout()
    plt.yscale("log")
    plt.savefig(output_path)
    plt.close()

#Analyzing Bitwise

MASK_64 = (1 << 64)-1

def count_default_bits(z, o):
    default_mask = z & ~o & MASK_64
    return default_mask.bit_count()

#Analyzing any non Default Variable
def analyze_masks(z, o, s, a):

    info_z = z != Z_DEFAULT
    info_o = o != O_DEFAULT
    info_s = s != S_DEFAULT
    info_a = a != A_DEFAULT
       
    return info_z, info_o, info_s, info_a

def build_cmd(build_path, benchmark):
    build_path = Path(build_path)
    qemu_bin = build_path / benchmark["command"]

    return ([str(qemu_bin)] + benchmark["flags"] + [benchmark["path"]])

def run_benchmark(build, benchmark):
    print(f"\n--- Running {build} with binary {benchmark} ---")

    output_dir = Path("results") / Path(build).name / benchmark["name"]
    output_dir.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
       build_cmd(build,benchmark),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    stats = Counter()
    default_hist = Counter()
    op_hist = Counter()
    op_mask_stats = Counter()
    op_mask_count = Counter()
    default_hist_z = Counter()
    default_hist_o = Counter()
    default_hist_s = Counter()
    
    lines = 0

    for line in proc.stdout:
        match = MASK_RE.search(line)
        match_finishfolding = FINISH_RE.search(line)
        if match:
            lines += 1

            op = match.group(1)
            z = int(match.group(2), 16)
            o = int(match.group(3), 16)
            s = int(match.group(4), 16)
            a = int(match.group(5), 16)

            info_z, info_o, info_s, info_a = analyze_masks(z, o, s, a)
            default_bits = count_default_bits(z, o)
            default_hist[default_bits] += 1

            default_bits_z = z.bit_count()
            default_bits_o = (~o & MASK_64).bit_count()
            default_bits_s = (~s & MASK_64).bit_count()

            default_hist_z[default_bits_z] += 1
            default_hist_o[default_bits_o] += 1
            default_hist_s[default_bits_s] += 1

            stats["z"] += info_z
            stats["o"] += info_o
            stats["s"] += info_s
            stats["a"] += info_a
            op_hist[op] += 1
            op_mask_count[op] += 1

            if info_z:
                op_mask_stats[(op, "z")] += 1
            if info_o:
                op_mask_stats[(op, "o")] += 1
            if info_s:
                op_mask_stats[(op, "s")] += 1
            if info_a:
                op_mask_stats[(op, "a")] += 1

        if match_finishfolding:
            lines +=1
            op = match_finishfolding.group(1)
            op_hist[op] += 1

    proc.wait()

    print(f"Done. Parsed mask lines: {lines}")

    if lines > 0:
        print("\n--- Mask Information Summary ---")
        print(f"Lines Count: {lines}")
        print(f"Non Default Z bits: {stats['z']}. Percentage of Z we have Information about: {stats['z'] / lines:.2f} ")
        print(f"Non Default O bits: {stats['o']}. Percentage of O we have Information about: {stats['o'] / lines:.2f}")
        print(f"Non Default S bits: {stats['s']}. Percentage of S we have Information about: {stats['s'] / lines:.2f}")
        print(f"Non Default A bits: {stats['a']}. Percentage of A we have Information about: {stats['a'] / lines:.2f}")
        plot_histogram(default_hist, output_dir / "default_bits.png")
        save_histogram_csv(default_hist, output_dir / "default_bits.csv")
        plot_histogram_defaultbits_mask(default_hist, default_hist_z, default_hist_o, default_hist_s, output_dir / "default_bits_multi.png")
        save_default_bits_multi_csv(default_hist, default_hist_z, default_hist_o, default_hist_s, output_dir / "default_bits_multi.csv")
        plot_operation_histogram(op_hist, output_dir / "operation_hist.png")
        save_operation_histogram_csv(op_hist, output_dir / "operation_hist.csv")
        plot_operation_mask_histogram(op_mask_stats,  op_mask_count, output_dir / "operationMaskCount_hist.png")
        save_operation_mask_exec_csv(op_mask_stats, op_mask_count, output_dir / "operationMaskCount_hist.csv")
    else:
        print("No fold_masks_zosa_int lines found!")

    print("--------------------------------\n")

def save_histogram_csv(hist, filepath):
    filepath = Path(filepath)
    with filepath.open("w") as f:
        f.write("default_bits,count\n")
        for bits in sorted(hist):
            f.write(f"{bits},{hist[bits]}\n")

def plot_operation_histogram(op_hist, output_path):
    ops = list(op_hist.keys())
    counts = [op_hist[op] for op in ops]

    plt.figure(figsize=(10, 5))
    plt.bar(ops, counts)
    plt.xlabel("Operation")
    plt.ylabel("Count")
    plt.title("Operation Frequency")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.yscale("log")
    plt.savefig(output_path)
    plt.close()


def save_operation_histogram_csv(op_hist, filepath):
    filepath = Path(filepath)
    with filepath.open("w") as f:
        f.write("operation,count\n")
        for op, count in op_hist.items():
            f.write(f"{op},{count}\n")

def plot_operation_mask_histogram(op_mask_stats,  op_mask_count, output_path):
    ops = sorted(
        set(op for (op, _) in op_mask_stats) |
        set(op_mask_count.keys())
    )

    z_counts = [op_mask_stats.get((op, "z"), 0) for op in ops]
    o_counts = [op_mask_stats.get((op, "o"), 0) for op in ops]
    s_counts = [op_mask_stats.get((op, "s"), 0) for op in ops]
    a_counts = [op_mask_stats.get((op, "a"), 0) for op in ops]
    op_counts = [op_mask_count.get(op, 0) for op in ops]

    x = range(len(ops))
    width = 0.15

    plt.figure(figsize=(16, 6))
    plt.bar([i - 2*width for i in x], op_counts, width, label="Op Count")
    plt.bar([i - 1*width for i in x], z_counts, width, label="Z")
    plt.bar([i for i in x], o_counts, width, label="O")
    plt.bar([i + 1*width for i in x], s_counts, width, label="S")
    plt.bar([i + 2*width for i in x], a_counts, width, label="A")

    plt.xlabel("Operation")
    plt.ylabel("Non-default count")
    plt.title("Non-default Mask Count per Operation")
    plt.xticks(x, ops, rotation=90)
    plt.yscale("log")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def save_operation_mask_exec_csv(op_mask_stats, op_mask_count, filepath):
    ops = sorted(set(op_mask_count) | {op for op, _ in op_mask_stats})

    filepath = Path(filepath)
    with filepath.open("w") as f:
        f.write("operation,z,o,s,a,exec\n")
        for op in ops:
            f.write(
                f"{op},"
                f"{op_mask_stats.get((op,'z'),0)},"
                f"{op_mask_stats.get((op,'o'),0)},"
                f"{op_mask_stats.get((op,'s'),0)},"
                f"{op_mask_stats.get((op,'a'),0)},"
                f"{op_mask_count.get(op,0)}\n"
            )


def plot_histogram_defaultbits_mask(hist_all, hist_z, hist_o, hist_s, output_path):
    x_vals = list(range(65))

    y_all = [hist_all.get(i, 0) for i in x_vals]
    y_z   = [hist_z.get(i, 0) for i in x_vals]
    y_o   = [hist_o.get(i, 0) for i in x_vals]
    y_s   = [hist_s.get(i, 0) for i in x_vals]

    width = 0.2
    x = range(len(x_vals))

    plt.figure(figsize=(14, 6))

    plt.bar([i - 1.5*width for i in x], y_all, width, label="Combined (Z & ~O)")
    plt.bar([i - 0.5*width for i in x], y_z,   width, label="Z")
    plt.bar([i + 0.5*width for i in x], y_o,   width, label="O")
    plt.bar([i + 1.5*width for i in x], y_s,   width, label="S")

    plt.xlabel("Number of Default Bits")
    plt.ylabel("Count")
    plt.title("Default Bits Histogram (Combined vs Z vs O vs S)")
    plt.xticks(range(0, 65, 8))
    plt.yscale("log")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def save_default_bits_multi_csv(hist_all, hist_z, hist_o, hist_s, filepath):
    filepath = Path(filepath)
    with filepath.open("w") as f:
        f.write("default_bits,combined,z,o,s\n")
        for bits in range(65):
            f.write(
                f"{bits},"
                f"{hist_all.get(bits, 0)},"
                f"{hist_z.get(bits, 0)},"
                f"{hist_o.get(bits, 0)},"
                f"{hist_s.get(bits, 0)}\n"
            )

def main():
    for build in QEMU_BUILDS:
        for benchmark in BENCHMARKS:
            run_benchmark(build, benchmark)


main()
