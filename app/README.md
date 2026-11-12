# Cricket Box Android app

A Tauri 2 shell for Android. It opens a small connect screen (`ui/index.html`), checks that the hub on
the Arduino UNO Q answers, and then loads the dashboard the hub serves. The phone therefore always has
the same controls as the web dashboard, and updating the hub updates the app.

Default hub address: `10.42.0.1:8000` (the UNO Q hotspot `SEEv2-Cricket`). The last address that worked
is remembered. The phone's back button returns to the connect screen.

## Build

Needs Node 20+, Rust (via rustup), JDK 17+, and the Android SDK with NDK.

```sh
# Android SDK + NDK (once)
export ANDROID_HOME=$HOME/Android/Sdk
export NDK_HOME=$ANDROID_HOME/ndk/27.2.12479018
sdkmanager --sdk_root=$ANDROID_HOME --licenses
sdkmanager --sdk_root=$ANDROID_HOME "platform-tools" "platforms;android-35" \
  "build-tools;35.0.0" "ndk;27.2.12479018" "cmdline-tools;latest"
rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android

# App
cd app
npm install
npm run android:build        # APK in src-tauri/gen/android/app/build/outputs/apk/
```

`src-tauri/gen/android` is committed, including the cleartext-HTTP setting the hub needs (the hub
serves plain HTTP on the local network). Install the APK with `adb install -r <apk>`.
