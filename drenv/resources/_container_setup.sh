#!/bin/bash

# script to run in new container
# not intended for user to invoke, will be run automatically when container first built

set -o errexit

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
WORKSPACE_DIR=$(realpath ${SCRIPT_DIR}/../..)

source /opt/ros/${ROS_DISTRO}/setup.bash

# fix ssh auth to stash in jammy
if [ "$(lsb_release -cs)" == "jammy" ]; then
    sudo chown $USER ~/.ssh
    touch ~/.ssh/config
    chmod 600 ~/.ssh/config
    cat << EOF >> ~/.ssh/config
Host *
    PubkeyAcceptedAlgorithms +ssh-rsa
    HostKeyAlgorithms +ssh-rsa
EOF
fi

# workaround for some sort of bug in rocker --git flag
if [  -f /home/None/.gitconfig ]; then
    cp /home/None/.gitconfig ~/
fi

# apt/rosdep update
sudo apt-get update
rosdep update

# source workspace setup scripts (if/when they exist)
if [ "${ROS_VERSION}" == "1" ]; then
    WS_SETUP_SCRIPT=${WORKSPACE_DIR}/devel/setup.bash
else
    WS_SETUP_SCRIPT=${WORKSPACE_DIR}/install/setup.bash
    echo "export ROS_LOCALHOST_ONLY=1" >> ~/.bashrc
fi
echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
echo "if [ -f ${WS_SETUP_SCRIPT} ]; then source ${WS_SETUP_SCRIPT}; fi" >> ~/.bashrc

# modify PS1 prompt
NEW_PS1="\[\033[01;35m\](${ROS_DISTRO}) \[\033[0m\]\$(echo \$PS1 | sed 's/\\\h/docker/g') "
echo "export PS1=\"${NEW_PS1}\"" >> ~/.bashrc


cat << EOF >> ~/.bashrc
# the following are just personal preferences (Tim Fanselow)
# TODO: method to allow users to automatically configure more to their liking
# Copy their bashrc in? Could cause problems if they are sourcing host-specific stuff
bind '\C-f:unix-filename-rubout'
export VISUAL=vim
export EDITOR="$VISUAL"
export HISTSIZE=10000
export HISTFILESIZE=10000
alias tls="tmux list-sessions"
alias tat="tmux attach -t "
EOF

cat << EOF >> ~/.inputrc
# the following are just personal preferences (Tim Fanselow)
# TODO: method to allow users to automatically configure more to their liking

# page up/down for history search
"\e[5~": history-search-backward   
"\e[6~": history-search-forward
EOF


