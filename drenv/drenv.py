"""drenv (Docker+Ros development ENVironment)

Setup a docker-based development environment for ROS. 

Resources related to the environment (including the 'activate' script)
are stored under the specified ENV_DIR. The parent directory of ENV_DIR
is mounted into the container's home directory. 

For troubleshooting, see the readme: 
https://github.com/tim-fan/drenv/blob/main/README.md

Supported distros: {supported_distros}
Version: {version}
Author: Tim Fanselow

Usage:
  drenv  ROS_DISTRO ENV_DIR [--no-cache] [--no-gpu] [--cuda]
  drenv (-h | --help)
  drenv --version

Arguments:
  ROS_DISTRO      Which ROS distribution to use (e.g. 'noetic', 'humble' etc)
  ENV_DIR         A directory to create the environment in.

Options:
  --no-cache        Build docker image with --no-cache flag
  --no-gpu          Do not give gpu access to container (for platforms without a gpu)
  --cuda            Enable cuda support in the container
  -h --help         Show this screen.
  --version         Show version.

"""
from docopt import docopt
import pkg_resources
from pathlib import Path
import textwrap
import os
import secrets
import shutil
import subprocess
from tabulate import tabulate
from dataclasses import dataclass, fields

# Support python 3.7
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:  # for Python<=3.6.9 (a1 jetson)
    from importlib_metadata import version, PackageNotFoundError

try:
    __version__ = version("drenv")
except PackageNotFoundError:
    # package is not installed
    __version__ = "unversioned"

supported_distros = [
    "melodic",
    "noetic",
    "foxy",
    "humble",
    "iron",
]

# Prevent errors due to oversized tags
# Actual max len = 128
# I'm getting errors because rocker adds prefixes to my tags
# so I'll just restrict my tags to 100 chars, and hope rocker
# doesn't add more than 28 chars to any tag
# https://docs.docker.com/engine/reference/commandline/tag/
MAX_TAG_LEN=100
INTERMEDIATE_IMG_SUFFIX="_tmp_intermediate"

# always exit on error
def run(*args, **kwargs):
    subprocess.run(*args, **kwargs, check=True)


@dataclass
class EnvInfo:
    """
    Paths and other variables related to the environment
    Paths on the host machine are prefixed 'host', paths
    in the container are prefixed 'container'.
    """
    container_name: str
    host_workspace_dir: Path
    host_env_dir: Path
    host_bin_dir: Path
    host_resource_dir: Path
    host_container_name_file: Path
    host_drenv_version_file: Path
    host_docker_file: Path
    host_activate_path: Path
    host_run_cmd_path: Path
    host_ssh_auth_sock: Path
    container_workspace_dir: Path
    container_env_dir: Path
    container_container_setup_path: Path
    container_ssh_auth_sock: Path

    def __repr__(self) -> str:
        table_rows = []
        for f in fields(self):
            table_rows.append([f.name, getattr(self, f.name)])
        return tabulate(table_rows, headers=["field", "value"])


def get_env_info(host_env_dir: Path) -> EnvInfo:
    """
    This function defines and returns paths to various environment resources
    """

    host_env_dir = host_env_dir.resolve()
    host_resource_dir = host_env_dir / "resources"
    host_bin_dir=host_env_dir / "bin"
    host_workspace_dir = host_env_dir.parent
    container_workspace_dir = Path(
        f"/home/{os.environ['USER']}/{host_workspace_dir.stem}")
    container_env_dir = container_workspace_dir / host_env_dir.stem

    info = EnvInfo(
        container_name="unnamed_container",  # overwritten below
        host_env_dir=host_env_dir,
        host_bin_dir=host_bin_dir,
        host_resource_dir=host_resource_dir,
        container_env_dir=container_env_dir,
        host_docker_file=host_resource_dir/ "Dockerfile",
        host_activate_path=host_bin_dir / "activate",
        host_run_cmd_path=host_bin_dir / "run_cmd",
        host_container_name_file=host_env_dir / "docker_container_name",
        host_drenv_version_file=host_resource_dir / "drenv_version.txt",
        host_ssh_auth_sock=host_resource_dir / "ssh_auth_sock",
        container_ssh_auth_sock=Path("/tmp/ssh_auth_sock"),
        host_workspace_dir=host_workspace_dir,
        container_workspace_dir=container_workspace_dir,
        container_container_setup_path=container_env_dir / \
        "resources" / "_container_setup.sh",
    )
    # read container name if it has been set
    if info.host_container_name_file.is_file():
        with open(info.host_container_name_file, "r") as f:
            info.container_name = f.read()

    return info


def write_container_name(env_dir: Path, ros_distro: str):
    """
    Choose a container name and write it into the env directory for later reference
    """
    # choose a random name for the image/container
    # name =  ros distro + random string + drenv dir
    env_info = get_env_info(env_dir)
    container_name = f"{ros_distro}_{secrets.token_hex(12)}{str(env_dir.absolute()).replace('/','_')}"
    
    # prevent errors on over-max-length tags
    container_name = container_name[:MAX_TAG_LEN-len(INTERMEDIATE_IMG_SUFFIX)]
    
    with open(env_info.host_container_name_file, "w") as f:
        f.write(container_name)


def build_env(env_dir: Path, ros_distro: str, no_cache: bool, no_gpu: bool, cuda:bool):
    """
    Build the docker ros environment
    First builds an image for the given distro, then starts the persistent container
    using rocker.
    """

    # Exit if no ssh auth sock (currently _container_setup.sh requires ssh auth)
    assert "SSH_AUTH_SOCK" in os.environ, "Error: Must provide SSH_AUTH_SOCK in environment"

    # set container name
    write_container_name(env_dir, ros_distro)
    env_info = get_env_info(env_dir)
    
    # set name for the image after docker build but before rocker additions
    # this image is deleted after rocker is invoked
    intermdediate_image_build_name = f"drenv:{env_info.container_name}{INTERMEDIATE_IMG_SUFFIX}"

    print(f"Building container: {env_info.container_name}")
    print("Env config:")
    print(env_info)

    print()
    print("DOCKER IMAGE BUILD")
    print()

    # Build the image
    build_args = [
        "-t", intermdediate_image_build_name,
        "--build-arg", f"ROS_DISTRO={ros_distro}",
        "--network=host",
        "--label", f"drenv_dir={env_info.host_env_dir}",
        "--label", f"drenv_version={__version__}",
    ]
    if no_cache:
        build_args += ["--no-cache"]

    #  'cat' the dockerfile into the docker build to build without context
    ps = subprocess.Popen(
        ('cat', env_info.host_docker_file), stdout=subprocess.PIPE)
    run(["docker", "build"] + build_args + ["-"], stdin=ps.stdout)

    # create an ssh_auth_sock file in drenv dir, symlinked to actual auth sock file
    # this allows auth_sock to change (e.g. over reboot) without needing to rebuild container
    os.symlink(os.environ["SSH_AUTH_SOCK"], env_info.host_ssh_auth_sock)

    rocker_flags=[
        '--nocleanup',
        '--user',
        '--git',
        '--privileged',
        '--name', env_info.container_name,
        '--image-name', f'drenv:{env_info.container_name}',
        '--volume', f'{env_info.host_workspace_dir}:{env_info.container_workspace_dir}',
        '--volume', '/dev/',
        '--volume', '/tmp/.X11-unix',
        '--volume', f'{os.environ["HOME"]}/.ssh/known_hosts',
        f'--volume={env_info.host_ssh_auth_sock}:{env_info.container_ssh_auth_sock}',
        '--env', f'SSH_AUTH_SOCK={env_info.container_ssh_auth_sock}',
        '--env=DISPLAY',
        '--env=USER',
        '--network', 'host',
        '--oyr-run-arg', f'''
          --detach 
          --group-add=dialout
          --security-opt apparmor:unconfined 
          --workdir {env_info.container_workspace_dir}
        ''',
    ]

    if cuda:
        rocker_flags.append('--cuda')

    if not no_gpu:
        # prepend rather than append flag
        # because in rocker 0.2.13, if the image
        # name follows the nvidia flag, it is interpreted as an arg value for
        # the nvidia flag, resulting in an error like the following:
        # rocker: error: argument --nvidia: invalid choice: 'drenv:humble_1637660e030170c689ab585b_home_tfanselow_tools_drenv_test_ws_humble_drenv_tmp_intermediate' (choose from 'auto', 'runtime', 'gpus')
        rocker_flags.insert(0, '--nvidia')

    if no_cache:
        rocker_flags += ["--nocache"]

    # start container using rocker
    rocker_call = ['rocker'] + rocker_flags + [
        intermdediate_image_build_name,
        'tail -f /dev/null',
    ]
    print()
    print("DOCKER CONTAINER START")
    print()
    print(
        f"Starting container using rocker with args:\n{' '.join(rocker_call)}")
    print()
    run(rocker_call)

    # delete intermediate image
    run(["docker", "rmi", intermdediate_image_build_name])

    print()
    print("RUN CONTAINER SETUP SCRIPT")
    print()

    # run container setup script inside the container
    run([str(env_info.host_run_cmd_path), str(
        env_info.container_container_setup_path)])


def copy_resources_to_env(env_dir: Path):
    """
    Copy files out of the drenv python package into the chosen
    drenv environment directory
    """

    env_info = get_env_info(env_dir)

    env_info.host_env_dir.mkdir(parents=True)
    env_info.host_bin_dir.mkdir()
    env_info.host_resource_dir.mkdir()

    # tools for user go to bin
    for filepath in [
        "resources/activate",
        "resources/rebuild",
        "resources/run_cmd",
        "resources/cleanup",
        "resources/delete_all_drenv_containers.sh",
        "resources/delete_all_drenv_images.sh",
    ]:
        shutil.copy(pkg_resources.resource_filename(
            "drenv", filepath), env_info.host_bin_dir)

    # non-user-facing resources go to ./resources
    for filepath in [
        "resources/Dockerfile",
        "resources/_container_setup.sh",
    ]:
        shutil.copy(pkg_resources.resource_filename(
            "drenv", filepath), env_info.host_resource_dir)


def main():
    arguments = docopt(__doc__.format(
        supported_distros=supported_distros, version=__version__), version=f'drenv {__version__}')

    ros_distro = arguments["ROS_DISTRO"]
    if not ros_distro in supported_distros:
        print(f"""Error: requested ROS distro '{ros_distro}' not supported.\n"""
              f"""Supported distros: {supported_distros}""")
        exit(1)

    env_dir = Path(arguments["ENV_DIR"])

    copy_resources_to_env(env_dir)

    # write drenv version to drenv dir
    env_info = get_env_info(env_dir)
    with open(env_info.host_drenv_version_file, "w") as f:
        f.write(__version__)

    build_env(
        env_dir,
        ros_distro,
        no_cache=arguments["--no-cache"],
        no_gpu=arguments["--no-gpu"],
        cuda=arguments["--cuda"],
    )

    # done. print additional usage message
    if env_dir.is_absolute():
        source_cmd = f". {env_info.host_activate_path}"
    else:
        source_cmd = f". {env_info.host_activate_path.relative_to(Path.cwd())}"

    print()
    print(textwrap.dedent(f"""
        Build complete, container is ready for use.
        To attach to container, source the activation script:
        {source_cmd}
    """))

if __name__ == '__main__':
    main()
