# ElectroScholar applications

ElectroScholar uses Compose Multiplatform for shared product slices and thin
native hosts for Android, iOS, macOS, Linux, and Windows.

## Requirements

- JDK 21 LTS.
- Android SDK 37 for local Android builds.
- Full Xcode for local iOS builds.
- All Gradle dependencies are resolved by the checked-in wrapper.

## Fast shared-development loop

This loop does not require Android SDK or Xcode:

```bash
./gradlew checkArchitecture checkVersionConsistency \
  :features:question-bank:jvmTest :desktopApp:run
```

The question-bank slice contains its UI, SQL contract, database adapters,
resources, and tests. Changes under `commonMain` are consumed unchanged by all
hosts.

## Platform builds

```bash
# Android debug APK
./gradlew :androidApp:assembleDebug

# Desktop app on the current host
./gradlew :desktopApp:run

# Native desktop installer; choose the task for the current host
./gradlew :desktopApp:packageDmg
./gradlew :desktopApp:packageDeb
./gradlew :desktopApp:packageMsi

# iOS simulator (requires full Xcode)
cd iosApp
xcodebuild -scheme iosApp -configuration Debug \
  -sdk iphonesimulator -arch arm64 CODE_SIGNING_ALLOWED=NO
```

## Refresh the packaged corpus

```bash
cd ..
python3 tools/inspect_legacy_db.py test --export-database analysis/database
python3 tools/compile_question_bank.py analysis/questions \
  --base-database analysis/database/question-bank.sqlite \
  --output analysis/database/question-bank.sqlite
cp analysis/database/question-bank.sqlite \
  kmp-app/features/question-bank/src/commonMain/composeResources/files/database/question_bank.sqlite
```

The 582 source images already live in the slice's shared Compose resources.
Refreshing image resources must be a separate deterministic tool; Gradle builds
do not mutate source files.

Architecture rules, native adapter boundaries, and the Unix-style tool pipeline
are documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
The target learning UX is in
[`docs/PRODUCT_EXPERIENCE.md`](docs/PRODUCT_EXPERIENCE.md), and the planned
simulation contracts are in
[`docs/REALTIME_CIRCUIT_SIMULATION.md`](docs/REALTIME_CIRCUIT_SIMULATION.md).
