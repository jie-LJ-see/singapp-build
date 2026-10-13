[app]

title = 唱名练习App
package.name = singapp
package.domain = org.singapp

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,mp3,wav

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.minapi = 21

[buildozer]
log_level = 2
warn_on_root = 0