# Releasing ElectroScholar

ElectroScholar uses one SemVer version and one changelog for every platform.
`version.txt` is the source of truth consumed by Gradle and maintained by
Release Please.

## Version rules

Commit messages follow Conventional Commits:

| Commit | Version change | Changelog |
|---|---:|---|
| `fix:` | patch | Bug fixes |
| `feat:` | minor | Features |
| `perf:` | patch | Performance |
| `refactor:`, `docs:`, `build:`, `ci:`, `test:` | no bump by itself | Included when a release exists |
| `feat!:` or `BREAKING CHANGE:` | major | Breaking changes |
| `chore:` | no bump | Hidden |

A `Release-As: x.y.z` commit footer may be used for an intentional one-off
version override.

## Automated flow

1. Changes land on `main` with Conventional Commit messages.
2. Release Please creates or updates one release pull request containing
   `CHANGELOG.md`, `version.txt`, and the release manifest.
3. A maintainer reviews and merges that pull request. This is the human release
   gate.
4. Release Please creates a tagged draft release.
5. The packaging workflow repeats data/schema checks and shared-slice tests.
6. macOS, Linux, Windows, Android, and iOS runners build in parallel.
7. The workflow uploads all packages and `SHA256SUMS`, then publishes the draft
   as the latest GitHub Release only when every target succeeds.

If packaging needs to be recovered, run the **Package release** workflow
manually with the existing draft release tag. Uploads are idempotent and replace
artifacts with the same name.

## Platform matrix

| Platform | Artifact/channel | Status | Remaining production requirement |
|---|---|---|---|
| macOS | DMG on GitHub Releases | Automated | Developer ID signing and notarization |
| Linux | DEB on GitHub Releases | Automated | Optional RPM/AppImage formats |
| Windows | MSI on GitHub Releases | Automated | Authenticode signing |
| Android | Debug-signed APK on GitHub Releases | Automated preview | Upload keystore and Play service account for production AAB |
| iOS | Simulator `.app` archive on GitHub Releases | Automated preview | Apple Developer team, certificates and provisioning for device/TestFlight builds |

Android and iOS artifacts are real builds of the shared application, including
the offline database and images. The Android preview is installable but uses a
debug key. The iOS preview runs in Apple Silicon Simulator and is not a signed
device archive. Store lanes will consume the same `version.txt` and release tag
after repository secrets contain the required signing credentials.
