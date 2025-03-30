# syntax=docker/dockerfile:1.3-labs

# Experimental syntax used for RUN --bind option

ARG ROS_DISTRO=noetic

FROM ros:${ROS_DISTRO}


# prep for apt installs
ARG DEBIAN_FRONTEND=noninteractive

# hotfix for key expiration 21/11/23 
# https://github.com/osrf/docker_images/issues/697
# I assume they will update the upstream docker images and I can remove this,
# but at the current point in time it is required
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 4B63CF8FDE49746E98FA01DDAD19BAB3CBF125EA

# keep apt cache (I want tab completion for apt packages!)
RUN rm /etc/apt/apt.conf.d/docker-clean
RUN apt-get update

# Get man pages (handy to have around)
# https://stackoverflow.com/questions/54152906/how-to-install-man-pages-on-an-ubuntu-docker-image
RUN sed -i 's:^path-exclude=/usr/share/man:#path-exclude=/usr/share/man:' \
        /etc/dpkg/dpkg.cfg.d/excludes
RUN apt-get update && \
    apt-get install -y \
        man \
        manpages-posix

# Seems 'unminimize' is required as well to ensure all man pages available
# https://askubuntu.com/questions/1173337/how-to-prevent-system-from-being-minimized
RUN yes| unminimize 

# Avoid apt install errors RE not having apt-utils available
# also command-not-found for package install suggestions
RUN apt-get install -y \
    apt-utils \
    command-not-found


# Update/Upgrade
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get dist-upgrade -y



# ROS dev tools
# specifying per distro, as some packages differ across ros version (e.g. desktop-full not available for foxy)
# looking forward to dropping support for melodic, but a couple interesting
# external packages still use it (quad_sdk, pronto)
# TODO: move to separate file?
RUN <<EOF
if [ ${ROS_DISTRO} = "melodic" ]
then
    apt-get install -y \
        openssh-client \
        ros-${ROS_DISTRO}-desktop-full \
        virtualenv

elif [ ${ROS_DISTRO} = "noetic" ]
then
    apt-get install -y \
        ros-${ROS_DISTRO}-desktop-full

elif [ ${ROS_DISTRO} = "humble" ]
then
    apt-get install -y \
        ros-${ROS_DISTRO}-desktop-full

elif [ ${ROS_DISTRO} = "foxy" ]
then
    # note desktop-full not supported on foxy
    apt-get install -y \
        ros-${ROS_DISTRO}-desktop

elif [ ${ROS_DISTRO} = "iron" ]
then
    apt-get install -y \
        ros-${ROS_DISTRO}-desktop-full

else
    echo "ROS distro '${ROS_DISTRO}' not recognised. Aborting"
    exit 1
fi
EOF

# ROS dev tools which can be installed across all supported distros
RUN apt-get install -y \
    ros-${ROS_DISTRO}-plotjuggler-ros \
    ros-${ROS_DISTRO}-rqt-tf-tree # rqt-tf-tree is included by default desktop package on ROS1, but not in ROS2. Here I ensure it's available for all distros

# Handy (non-ROS) tools, stuff you expect above minimal ubuntu (tmux, htop, vim, ping)
# Maybe list these in a separate file?
# install and setup fzf reverse history search? Too tailored to my preferences?
RUN apt-get install -y \
    bash-completion \
    curl \
    entr \
    evince \
    gdb \
    git \
    git-lfs \
    htop \
    iproute2 \
    iputils-ping \
    less \
    nano \
    net-tools \
    python3-pip \
    python3-venv \
    ristretto \
    software-properties-common \
    stress \
    tmux \
    vim \
    wget \
    x11-apps 

# More handy tools, from pip
RUN python3 -m pip install --upgrade \
    catkin-tools \
    ipython \
    pip

# switch on completion
# Editing default bashrc, so this is in use for new users in the image
RUN echo ". /etc/bash_completion" >> /etc/skel/.bashrc

# Force color prompt (I like it)
RUN sed '/#force_color_prompt=yes/s/^#//g' -i /etc/skel/.bashrc

