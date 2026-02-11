ARG VARIANT=3-bullseye
ARG packagemanager=apt
ARG InstallArg=install
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}
ENV PYTHONUNBUFFERED 1
COPY requirements.txt /tmp/pip-tmp/

RUN {packagemanager} {InstallArg} --no-cache git python3 nodejs py3-pip py3-pip-bash-completion
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt && rm -rf /tmp/pip-tmp