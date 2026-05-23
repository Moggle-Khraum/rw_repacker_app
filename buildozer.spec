[app]
title = RWMod Repacker
package.name = rwrepacker
package.domain = org.moggle.rwrepacker
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt
version = 1.0.0
requirements = python3==3.11.6,kivy==2.3.0,android
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.3.0
fullscreen = 0

# Android specific
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21

[buildozer]
log_level = 2
warn_on_root = 1
