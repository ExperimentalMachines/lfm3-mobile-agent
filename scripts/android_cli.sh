#!/bin/bash
# Android CLI with the settings that work on this Mac without touching the shared adb server:
# OpenJDK 21 for the background connection process, and an SDK shim whose platform-tools is the same Homebrew adb
# (37.0.1) that already runs the server (a different adb version would restart the server and drop the emulators).
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH=$JAVA_HOME/bin:/opt/homebrew/Caskroom/android-platform-tools/37.0.1/platform-tools:$PATH
exec android --sdk=/Users/alpha/lfm3-android/tools/android-sdk-shim "$@"
