import tempfile
import subprocess
from pathlib import Path
import os
from drenv.drenv import supported_distros
import time
import pytest


# always exit on error
def run(*args, **kwargs):
    return subprocess.run(*args, **kwargs, check=True)

def seconds_to_min_sec_str(seconds:float) -> str:
    """
    For pretty printing test durations
    """
    minutes, seconds = divmod(seconds, 60)
    seconds = int(seconds)
    minutes = int(minutes)

    if minutes == 0:
        return f"{seconds} seconds"
    elif seconds == 0:
        return f"{minutes} minutes"
    else:
        return f"{minutes} minutes, {seconds} seconds"


@pytest.mark.parametrize("distro", supported_distros)
def test_build_and_run(distro: str):
    # build and run for given distro
    # does not use cache - quite a slow test!
    # TODO: pytest option to use cache, when testing the tests

    # confirm drenv version invoked by shell is the version we want to run
    drenv_version = run(["drenv", "--version"],
                        capture_output=True, encoding='utf-8').stdout.strip()
    print(
        f"Building for distro '{distro}' with drenv version '{drenv_version}'")
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        drenv_dir = Path(tmpdir)/"drenv"

        # confirm can build drenv
        drenv_cmd = ["drenv", distro, drenv_dir]
        # run with no-cache to avoid apt install errors (ensures apt cache always up to date)
        drenv_cmd.append("--no-cache")
        run(drenv_cmd)

        # confirm can run a command
        run([drenv_dir/"bin/run_cmd", "echo", "success"])

        # confirm access to ssh key in container
        run([drenv_dir/"bin/run_cmd", "ssh-add", "-l"])

        # confirm same user inside and outside container
        p = run([drenv_dir/"bin/run_cmd", "whoami"],
                stdout=subprocess.PIPE, encoding='utf-8')
        assert p.stdout.strip() == os.environ["USER"]

        # confirm access to x server
        # X TEST DISABLED!
        # Test didn't work on jenkins, I haven't had time to setup jenkins
        # with virtual x server support
        # run([drenv_dir/"bin/run_cmd", "xprop", "-root"], capture_output=True)

        # confirm gpu support enabled
        run([drenv_dir/"bin/run_cmd", "nvidia-smi"], capture_output=True)

        # confirm can clean up
        run([drenv_dir/"bin/cleanup", "-y"])


def test_disable_gpu():
    """
    Checking --no-gpu flag works as expected
    """

    # just check on one distro with cache - should be enough to test the feature, don't want to spend ages
    # testing every distro
    with tempfile.TemporaryDirectory() as tmpdir:
        drenv_dir = Path(tmpdir)/"drenv"
        distro = "humble"
        drenv_cmd = ["drenv", distro, drenv_dir]
        drenv_cmd.append("--no-gpu")

        # build env
        run(drenv_cmd)

        # confirm no gpu
        with pytest.raises(subprocess.CalledProcessError):
            run([drenv_dir/"bin/run_cmd", "nvidia-smi"], capture_output=True)

        # cleanup
        # TODO: currently only cleans up on test pass - should also clean up on test fail
        run([drenv_dir/"bin/cleanup", "-y"])


def test_cuda():
    """
    Checking --cuda flag works as expected
    """

    # just check on one distro with cache - should be enough to test the feature, don't want to spend ages
    # testing every distro
    with tempfile.TemporaryDirectory() as tmpdir:
        drenv_dir = Path(tmpdir)/"drenv"
        distro = "humble"
        drenv_cmd = ["drenv", distro, drenv_dir]
        drenv_cmd.append("--cuda")

        # build env
        run(drenv_cmd)

        # confirm nvcc available
        # https://xcat-docs.readthedocs.io/en/stable/advanced/gpu/nvidia/verify_cuda_install.html
        run([drenv_dir/"bin/run_cmd", "nvcc", "--version"], capture_output=True)

        # cleanup
        # TODO: currently only cleans up on test pass - should also clean up on test fail
        run([drenv_dir/"bin/cleanup", "-y"])

def test_creation_duration():
    """
    Ensure it doesn't take too long to create an environment
    """

    # At time of writing, without cache takes 9 min 9 sec, with takes 21 sec
    # Setting thresholds a little above that so tests don't fail due to random load variations
    MAX_DURATION_WITHOUT_CACHE_S = 15*60 # allow 15 min for env build when not using cache
    MAX_DURATION_WITH_CACHE_S = 1*60 # allow 1 min for env build when using cache

    # just checking a single distro, assuming creation times are similar across distros, not worth extra test duration to check all distros
    distro = "humble"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        drenv_dir = Path(tmpdir)/"drenv"
        drenv_cmd_without_cache = ["drenv", distro, drenv_dir, "--no-cache"]

        # build env (no cache)
        without_cache_start_time = time.time()
        run(drenv_cmd_without_cache)
        without_cache_duration_s = time.time() - without_cache_start_time
        assert without_cache_duration_s <= MAX_DURATION_WITHOUT_CACHE_S, f"Time taken to create environment without cache ({seconds_to_min_sec_str(without_cache_duration_s)}) larger than maximum allowable duration ({seconds_to_min_sec_str(MAX_DURATION_WITHOUT_CACHE_S)})"

        # cleanup
        # TODO: currently only cleans up on test pass - should also clean up on test fail
        run([drenv_dir/"bin/cleanup", "-y"])
        
    with tempfile.TemporaryDirectory() as tmpdir:
        drenv_dir = Path(tmpdir)/"drenv"
        drenv_cmd_with_cache = ["drenv", distro, drenv_dir]

        # build env again, this time using cache, should be much quicker
        with_cache_start_time = time.time()
        run(drenv_cmd_with_cache)
        with_cache_duration_s = time.time() - with_cache_start_time
        assert with_cache_duration_s <= MAX_DURATION_WITH_CACHE_S, f"Time taken to create environment with cache ({seconds_to_min_sec_str(with_cache_duration_s)}) larger than maximum allowable duration ({seconds_to_min_sec_str(MAX_DURATION_WITH_CACHE_S)})"

        # cleanup
        # TODO: currently only cleans up on test pass - should also clean up on test fail
        run([drenv_dir/"bin/cleanup", "-y"])

