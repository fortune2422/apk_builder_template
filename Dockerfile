FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-11-jdk wget unzip git python3 python3-pip build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV ANDROID_SDK_ROOT=/opt/android-sdk
RUN mkdir -p ${ANDROID_SDK_ROOT}/cmdline-tools
WORKDIR /tmp
# NOTE: update the URL to the desired command-line tools version if needed
RUN wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O cmdline-tools.zip \
    && unzip cmdline-tools.zip -d /opt/android-sdk/cmdline-tools \
    && mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest \
    && rm cmdline-tools.zip

ENV PATH=$PATH:${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools
# Accept licenses and install basic packages (platform-tools, build-tools, platforms). May take time.
RUN yes | sdkmanager --sdk_root=${ANDROID_SDK_ROOT} --licenses || true
RUN sdkmanager --sdk_root=${ANDROID_SDK_ROOT} "platform-tools" "build-tools;33.0.2" "platforms;android-33" || true

# Copy repository and install python deps
WORKDIR /home/project
COPY . /home/project
RUN pip3 install --upgrade pip
RUN pip3 install -r backend/requirements.txt || true

EXPOSE 8000
CMD ["sh", "-c", "gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT backend.app:app"]
