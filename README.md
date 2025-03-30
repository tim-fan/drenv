# DRENV (Docker+Ros development ENVironment)

![a turtle above a whale](./doc/turtle_above_whale.jpg)

Tooling to setup a docker environment for ROS development. Attempts to somewhat emulate a python venv workflow, hence the awkward name.

The idea is to use a persistent docker container to store the development environment. In this way, after creation, packages can be installed, reconfigured etc as needed, and these changes will persist when the same environment is used again in future.

The tool is generally experimental and feedback/discussion is appreciated.

## Features

* persistence - can install tools into the environment, reboot your machine, reactivate, and the tools are still there! 
* comfort - the goal is to include as many tools as needed to make development in the container should be as comfortable/standard as native development. This includes the following (mostly  provided by `rocker`):
  * GUI support (`x11` + rocker `--nvidia` flag)
  * ssh agent forwarding (allows `git clone` from stash via ssh)
  * same user inside the container as outside
  * host network
  * .gitconfig available in container
  * support for hardware hotplug (host `/dev/` is mounted into the container - a nasty hack?)
* local - like `venv`, a `drenv` is contained in a directory of your choosing. You can have a bunch of them for different projects, or use a single one for everything if that works. 

## Install

With pip:

```bash
pip install --upgrade git@github.com:tim-fan/drenv.git
```

See section "Troubleshooting" below if you encounter issues installing or running `drenv`.

## Usage

```text
$ drenv -h
drenv (Docker+Ros development ENVironment)

Setup a docker-based development environment for ROS. 

Resources related to the environment (including the 'activate' script)
are stored under the specified ENV_DIR. The parent directory of ENV_DIR
is mounted into the container's home directory. 

For troubleshooting, see the readme: 
https://github.com/tim-fan/drenv/blob/main/README.md

Supported distros: ['melodic', 'noetic', 'foxy', 'humble', 'iron']
Version: x.x.x
Author: Tim Fanselow

Usage:
  drenv  ROS_DISTRO ENV_DIR [--no-cache] [--no-gpu]
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

```

## Example

To illustrate the general workflow:

### ROS2

In this example we setup an environment for ROS2 humble development, then build and run some example nodes. It is assumed `drenv` is installed as above.

```bash
# Make a workspace for ROS2 packages
mkdir colcon_ws && cd colcon_ws

# Setup an environment for ROS 'humble' development, storing related files under colcon_ws/humble_drenv/.
# This will build the required docker image and container
# The parent directory of the environment (in this case, colcon_ws) will be mounted in the container under $HOME
drenv humble humble_drenv

# Activate the drenv. You will be attached to the drenv container, which will contain ubuntu 22.04 with a ROS2 Humble installation.
# Note the very intentional similarity with python venv usage
. humble_drenv/bin/activate

# Now you are free to develop as usual.

# To continue the example, we'll build and run some example ROS2 nodes
git clone https://github.com/ros2/examples.git src/examples --branch humble
colcon build
source install/setup.bash
ros2 run examples_rclcpp_minimal_publisher publisher_member_function
# expected output:
# [INFO] [1680181848.886018396] [minimal_publisher]: Publishing: 'Hello, world! 0'
# [INFO] [1680181849.386024626] [minimal_publisher]: Publishing: 'Hello, world! 1'
# [INFO] [1680181849.886036341] [minimal_publisher]: Publishing: 'Hello, world! 2'
# ...

# when done developing, exit shell to exit the environment
# CTRL-D
```

## Clean up

When a drenv environment is no longer needed, should be deleted using the cleanup script:

```bash
./my_drenv/bin/cleanup
```

This will ensure the associated image and container are deleted. Failure to clean up in this way will leave you with many unused containers/images taking disk space. TODO: improved clean up process.

## How it works

A brief overview.

* User calls `drenv` (with appropriate arguments)
* `drenv` copies scripts from [drenv/resources/](./drenv/resources/) into appropriate places in the new drenv directory.
* `drenv` calls `build_env` function
* `build_env` builds a [Dockerfile](./drenv/resources/Dockerfile) to create the base image for the environment
* `build_env` then uses `rocker` to start the container with various resources from the host environment (x11 etc)
* `build_env` names the container, and saves this name in the drenv directory, for use when attaching
* `build_env` then calls [_container_setup.sh](./drenv/resources/_container_setup.sh). This script is responsible for any required steps to prepare the container after first launch.
* `build_env` completes and control is returned to the user.
* the user now sources [activate](./drenv/resources/activate), which looks up the container name from the file in the drenv directory, then attaches to that container. The user can now perform development tasks as usual.

## Troubleshooting

Listing issues previously encountered in use:

| Attempted task | Error Message      | Drenv version | Explanation | Workaround |
| ---------------| ----------- |----------- | ----------- | ----------- |
| Creating new `drenv` environment | `drenv: command not found`      | `1.0.7` | The `drenv` binary is installed to `~/.local/bin`. If that directory does not exist it will be created, but not added to path until next login. <br />To confirm this is the issue, look for the following warning from your `pip install` output: <br />`WARNING: The script drenv is installed in '/home/test_user/.local/bin' which is not on PATH.` | Log out and in again       |
|Creating new `drenv` environment |`E: Unable to fetch some archives, maybe run apt-get update or try with --fix-missing?`| `1.1.5`| Apt-cache in one of the docker image layers was out of date | Try again, calling `drenv` with `--no-cache` flag |
| Creating new `drenv` environment | `pkg_resources.ContextualVersionConflict: (urllib3 2.0.1 (/home/nav2_user/.local/lib/python3.8/site-packages), Requirement.parse('urllib3<1.27,>=1.21.1'), {'requests'})`| `1.1.4` | User installed version of `urllib3` was higher than supported version. I'm not sure how the environment got into this state, would have thought pip would prevent this. | Install compatible version of `urllib3`: <br/> `pip install --force-reinstall urllib3==1.26.0`. <br/> The issue could also be resolved by creating a new python `venv`, updating `pip` and reinstalling `drenv` |
| Creating new `drenv` environment  on a machine *without* a gpu |`docker: Error response from daemon: could not select device driver "" with capabilities: [[gpu]]`| `1.0.7` | Trying to run `drenv` on a nuc, which has no gpu. Drenv tries to connect container to gpu and fails. | As of `drenv 1.1.0`, you can use the flag `--no-gpu` to avoid this issue. |
| Using GUI in `drenv` environment | `Error: Can't open display:`| `1.0.9` | In this case the `drenv` was created over an ssh connection, when there was no `DISPLAY` environment variable set. Hence this variable was not set in the container. Subsequently the environment was used in a desktop environment, and GUI applications failed to open because `DISPLAY` was not set. | `export DISPLAY=:0`, or rebuild the drenv from a graphical environment. |
| Activating an existing `drenv` | `nvidia-container-cli: initialization error: nvml error: driver not loaded: unknown`| `1.0.?` | User had apt upgraded and rebooted. On container activate, the above error was displayed. The issue was not fully diagnosed but worked around by creating a new `drenv` | Delete existing `drenv`, create a new one. Not a nice fix, could be investigated further if the issue reoccurs in future. |
| Using a `snap` inside a `drenv` | `/run/snapd.socket: connect: no such file or directory` | `1.2.0` | Looks like it [could be difficult to run snaps in a docker container](https://askubuntu.com/questions/907126/snap-fails-from-inside-docker-container). I don't plan to look into this at this point in time. | No workaround identified |


If you are experiencing an issue not listed above, feel free to reach out to me (Tim Fanselow).

## Development

I make changes to `drenv` as follows:

```bash
git clone git@github.com:tim-fan/drenv.git
cd drenv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
# now make and test changes
```

The tests can then be run for all supported distros:

```bash
# warning! tests currently take about 45 mins to complete (!)
# TODO: speed up (run parallel?)
pip install pytest
pip install -e . # install again to get up-to-date version printed at start of test
python -m pytest --capture=no
```

When changes are committed and pushed, to update the version, push a new tag. Then update the release branch to point to the new tag (this is how users get the latest tagged version).

```bash
# on master:
python -m pytest # ensure tests passing before tagging!
git tag 1.x.x
git push --tags
git rebase master release
git push
git checkout master
```

The idea is that `release` will always point at the latest tagged version, so people can pip install from that branch to get the tagged version. In the meantime master can be updated without changing the version that users will receive.

## ToDo

* [IMPORTANT!] improve cleanup containers/images after use
  * ideally some sort of hook when the env directory is deleted, triggering docker calls to delete the image
  * even better - all data related to the docker image/container is saved in the env dir (instead of `/var/lib/docker`). No trace of images/containers left after deleting the directory
  * also probably acceptable: add verb `drenv clean`, to search for containers/images whose corresponding
    drenv directory is deleted, and delete these containers/images
* feature requests
  * it would be good if the user could configure their own environments.
    * something like:
      * keep user config directories, each env can be named, containing a docker file and container setup script
      * then create with `drenv my_named_env env_dir`
      * but, then how would it work for the ROS envs I want to work by default (e.g. humble, noetic). Detect these as named envs? 
  * implement an option along the lines of `--docker-run-arg "NAME=VALUE"` to pass arbitrary docker run args for starting the container (and/or arbitrary rocker args)
  * better error message when trying to use a drenv that has been moved on the filesystem
  * better error message when drenv container has been deleted
* cleanup when drenv creation failed or aborted (ensure no files left, or associated containers/images)
* track environment creation time in jenkins.
* target much faster env creation by moving as much as possible out of `_container_setup.sh` and into the Dockerfile
* consider usage change to `drenv ENV_DIR --ros-distro=DISTRO`
  * feels a bit closer to `venv`
  * could also make `drenv` module runnable e.g. `python -m drenv ENV_DIR --ros-distro=DISTRO`
* add note to README RE how to attach vscode to running container
* search for a less minimised image to use as base (currently quite a few docker steps are related to undoing minimisation, perhaps it would be more straight forward to install ROS on top of an image already setup for interactive developer use)
* Can I run container without `--privileged`? Can I `--cap-add` something more specific? https://docs.docker.com/engine/reference/run/#runtime-privilege-and-linux-capabilities
* test and document process for cross-platform builds
* Consider improved DDS configuration for ROS2. Currently setting ROS_LOCALHOST_ONLY=1, but would also like to support comms to remote devices
* script to "reboot" the container (not wipe it)
	* have had a couple users confused as zombie processes build up in background (e.g. from not killing things properly). In this case a way to kill everything and start again would have been useful. 
    * from brief testing, it looks like `docker kill $(cat humble_drenv/docker_container_name)` does the job - need to test a bit more, add as a a script under `humble_drenv/bin/`, and document.

## Discussion

Potentially rambling notes regarding this general approach to using docker for dev environments.

* differences from `venv`
  * drenv creates a directory to install files, *and also* picks a directory to mount into the container.
    * need to specify two directories to drenv call?
      * for now default to mount env parent dir

## See also

Similar/related projects:
	* [docker-ros](https://github.com/ika-rwth-aachen/docker-ros/) docker-ros automatically builds minimal container images of ROS applications.
    * [colcon-in-container](https://github.com/canonical/colcon-in-container) colcon verb extension to build and test inside a fresh and isolated ROS environment and transfer the results back to the host.
    * [ADE (Awesome Development Environment)](https://ade-cli.readthedocs.io/) a modular Docker-based tool to ensure that all developers in a project have a common, consistent development environment.


