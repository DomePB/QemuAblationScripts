import os
import subprocess
from pathlib import Path

#Builds that the script builds with configure flags
BUILDS = {
    "build-default": ["--extra-cflags=-DTCG_OPTIMIZATION"],
    "build-noOptimization": [],
    "build-defaultSMask": ["--extra-cflags=-DSET_SMASK_DEFAULT -DTCG_OPTIMIZATION"],
    "build-informationStudy": ["--extra-cflags=-DPRINT_MASKS"]
}


BASE_DIR = Path("/home/dome/qemu/QemuOptimizerAblationStudy")


def run_cmd(cmd, cwd=None):
    print(f"\n Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)

    if result.returncode != 0:
        raise RuntimeError(f"Command failed with return code {result.returncode}")
    

def build_all():
    for build, config_flags in BUILDS.items():
        print(f"\n Starting build: {build}")

        build_path = BASE_DIR / build

        build_path.mkdir(parents=True, exist_ok=True)

        configure_cmd = ["../configure"] + config_flags

        run_cmd(configure_cmd, cwd= build_path)

        run_cmd("make", cwd= build_path)

        print(f"\n build completed: {build}")


build_all()
