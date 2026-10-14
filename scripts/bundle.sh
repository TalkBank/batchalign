#!/usr/bin/env bash
# Build or reuse a CI DMG, then sign and notarize the ARM64 app and final DMG.
# One-time notarization credential setup (prompts securely for an app-specific
# password generated at account.apple.com; this is separate from the signing key):
#   xcrun notarytool store-credentials batchalign-notary \
#     --apple-id YOUR_APPLE_ID --team-id YOUR_APPLE_DEVELOPER_TEAM_ID
# Find the signing certificate fingerprint: security find-identity -v -p codesigning
# Then run: ./scripts/bundle.sh --identity SHA1 --profile batchalign-notary --output DIR
# Add --dmg PATH to reuse a CI build: mount read-only, copy the app, and detach.
# The copied app is signed/notarized/stapled before creating a new signed/notarized DMG.
# Building requires native Apple Silicon; both modes require a Developer ID private key.
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: ./scripts/bundle.sh [--dmg PATH] --identity SHA1 --profile NAME --output DIR

  --dmg       Reuse an existing CI DMG instead of building from source.
  --identity  Developer ID Application certificate's 40-character SHA-1 fingerprint.
  --profile   Existing notarytool Keychain credential profile.
  --output    New directory in an existing parent; retains artifacts and Apple logs.

By default, builds through just batchalign gui build using the Python version.
With --dmg, mounts the input read-only, copies Batchalign.app out, and detaches.
The input DMG is preserved; a new DMG contains the stapled app and Applications link.
The script signs a copy, notarizes/staples the app, then creates, signs, notarizes,
and staples a DMG. Both executables must be ARM64 and the version must match Python.

One-time Keychain credential setup (securely prompts for an app-specific password
generated at account.apple.com, not your regular Apple account password):
  xcrun notarytool store-credentials batchalign-notary \
    --apple-id YOUR_APPLE_ID --team-id YOUR_APPLE_DEVELOPER_TEAM_ID

Example:
  ./scripts/bundle.sh \
    --identity YOUR_CERTIFICATE_SHA1 --profile batchalign-notary \
    --output /tmp/batchalign-notarized-0.10.4-arm64

Submission IDs are saved before waiting for Apple. If interrupted, inspect the
output's logs and query/wait on that ID; do not submit the archive again blindly.
This script refuses to overwrite an existing output directory.
USAGE
}

die() {
    printf 'bundle: %s\n' "$*" >&2
    exit 1
}

validate_app() {
    local bundle="$1" expected_version="$2" version executable architectures
    [[ -d "$bundle" && ! -L "$bundle" ]] || die "expected an app directory: $bundle"
    [[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$bundle/Contents/Info.plist")" == org.talkbank.batchalign ]] \
        || die 'bundle identifier must be org.talkbank.batchalign'
    version="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$bundle/Contents/Info.plist")"
    [[ "$version" == "$expected_version" ]] \
        || die "desktop version $version differs from Python $expected_version; rebuild with matching versions"
    [[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$bundle/Contents/Info.plist")" == Batchalign ]] \
        || die 'expected the Batchalign main executable'
    for executable in "$bundle/Contents/MacOS/Batchalign" "$bundle/Contents/MacOS/sidecar"; do
        [[ -f "$executable" && ! -L "$executable" ]] || die "missing executable: $executable"
        architectures="$(lipo -archs "$executable")"
        [[ "$architectures" == arm64 ]] || die "ARM64 only: $executable contains $architectures"
    done
    # This release layout contains two Mach-O files. Additional native components
    # need an explicit signing policy, including any framework bundle resources.
    while IFS= read -r -d '' executable; do
        if [[ "$(file -b "$executable")" == *Mach-O* ]]; then
            case "$executable" in
                "$bundle/Contents/MacOS/Batchalign"|"$bundle/Contents/MacOS/sidecar") ;;
                *) die "unhandled native component: $executable" ;;
            esac
        fi
    done < <(find "$bundle" -type f -print0)
}

notarize_archive() {
    local archive="$1" label="$2" submission_id status
    xcrun notarytool submit "$archive" --keychain-profile "$profile" --output-format plist \
        > "$output/logs/$label-submission.plist"
    submission_id="$(/usr/libexec/PlistBuddy -c 'Print :id' "$output/logs/$label-submission.plist")"
    printf 'Apple %s submission: %s\n' "$label" "$submission_id"
    # A failed/interrupted wait must not cause a second submission. Always retain
    # the ID above and ask Apple for the current status of that same submission.
    xcrun notarytool wait "$submission_id" --keychain-profile "$profile" --output-format plist \
        > "$output/logs/$label-wait.plist" || true
    xcrun notarytool info "$submission_id" --keychain-profile "$profile" --output-format plist \
        > "$output/logs/$label-status.plist"
    status="$(/usr/libexec/PlistBuddy -c 'Print :status' "$output/logs/$label-status.plist")"
    case "$status" in
        Accepted|Invalid)
            xcrun notarytool log "$submission_id" --keychain-profile "$profile" \
                "$output/logs/$label-notary.json"
            ;;
    esac
    [[ "$status" == Accepted ]] \
        || die "Apple status is $status for $submission_id; inspect $output/logs before continuing"
}

input_dmg='' identity='' profile='' output=''
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --dmg|--identity|--profile|--output)
            [[ $# -ge 2 && -n "$2" ]] || die "missing value for $1"
            case "$1" in
                --dmg) input_dmg="$2" ;;
                --identity) identity="$2" ;;
                --profile) profile="$2" ;;
                --output) output="$2" ;;
            esac
            shift 2
            ;;
        *) die "unknown argument: $1 (see --help)" ;;
    esac
done
if [[ -z "$identity" || -z "$profile" || -z "$output" ]]; then
    usage >&2
    die 'all three arguments are required'
fi
[[ "$(uname -s)" == Darwin ]] || die 'macOS is required'
[[ "$identity" =~ ^[[:xdigit:]]{40}$ ]] || die 'identity must be a certificate SHA-1 fingerprint'
identity="$(printf '%s' "$identity" | tr '[:lower:]' '[:upper:]')"
for tool in git security codesign openssl python3 lipo file ditto hdiutil xcrun spctl shasum; do
    command -v "$tool" >/dev/null || die "required tool is missing: $tool"
done
if [[ -z "$input_dmg" ]]; then
    [[ "$(uname -m)" == arm64 ]] || die 'build on a native Apple Silicon Mac (without Rosetta)'
    command -v just >/dev/null || die 'required tool is missing: just'
    command -v rustc >/dev/null || die 'required tool is missing: rustc'
    [[ "$(rustc -vV | awk '/^host:/ { print $2 }')" == aarch64-apple-darwin ]] \
        || die 'the build requires an aarch64-apple-darwin Rust host toolchain'
else
    [[ -f "$input_dmg" ]] || die "input DMG does not exist: $input_dmg"
    input_dmg="$(cd "$(dirname "$input_dmg")" && pwd -P)/$(basename "$input_dmg")"
fi
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
expected_version="$(awk -F'"' '
    /^\[project\]$/ { project = 1; next }
    project && /^\[/ { exit }
    project && /^version[[:space:]]*=/ { print $2; exit }
' "$repo_root/python/pyproject.toml")"
[[ -n "$expected_version" ]] || die 'could not read the Python package version'
[[ ! -e "$output" && ! -L "$output" ]] || die "output already exists: $output"
[[ -d "$(dirname "$output")" ]] || die 'output parent directory must exist'
output="$(cd "$(dirname "$output")" && pwd -P)/$(basename "$output")"
app="$repo_root/target/aarch64-apple-darwin/release/bundle/macos/Batchalign.app"
case "$output/" in "$app/"*) die 'output must be outside the build app' ;; esac

# Preflight uses public certificates only; never export the private signing key.
scratch="$(mktemp -d "${TMPDIR:-/tmp}/batchalign-bundle.XXXXXX")"
mounted=''
trap 'if [[ -n "$mounted" ]]; then
    hdiutil detach "$mounted" || { printf "Could not detach %s; temporary files retained.\n" "$mounted" >&2; exit 1; }
fi
rm -rf "$scratch"' EXIT
security find-identity -v -p codesigning | awk -v fingerprint="$identity" '
    $2 == fingerprint { found = 1 }
    END { exit !found }
' || die 'signing identity/private key is unavailable or invalid'
security find-certificate -a -c 'Developer ID Application' -p > "$scratch/certificates.pem"
python3 - "$scratch/certificates.pem" "$identity" "$scratch/signer.pem" <<'PY'
import pathlib
import re
import subprocess
import sys

certificates, fingerprint, destination = sys.argv[1:]
for certificate in re.findall(
    rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',
    pathlib.Path(certificates).read_bytes(),
    re.S,
):
    result = subprocess.check_output(
        ['openssl', 'x509', '-noout', '-fingerprint', '-sha1'], input=certificate
    ).decode()
    if result.strip().split('=', 1)[1].replace(':', '') == fingerprint:
        pathlib.Path(destination).write_bytes(certificate + b'\n')
        break
else:
    raise SystemExit('Could not find the public Developer ID certificate for this fingerprint')
PY
openssl x509 -in "$scratch/signer.pem" -noout -subject -issuer -dates
openssl x509 -in "$scratch/signer.pem" -noout -checkend 0 || die 'signing certificate has expired'
security verify-cert -c "$scratch/signer.pem" -p codeSign
xcrun notarytool history --keychain-profile "$profile" --output-format plist \
    > "$scratch/credential-check.plist"

# Credential checks precede processing. Keep source provenance and Apple responses together.
mkdir "$output"
mkdir "$output/logs"
cp "$scratch/signer.pem" "$output/logs/signer.pem"
git -C "$repo_root" rev-parse HEAD > "$output/logs/operator-checkout.txt"
git -C "$repo_root" status --porcelain > "$output/logs/operator-worktree.txt"
if [[ -n "$input_dmg" ]]; then
    printf 'Extracting app from %s\n' "$input_dmg"
    shasum -a 256 "$input_dmg" > "$output/logs/input-dmg-sha256.txt"
    hdiutil verify "$input_dmg"
    mkdir "$scratch/mounted" "$scratch/extracted"
    hdiutil attach -readonly -nobrowse -mountpoint "$scratch/mounted" "$input_dmg" \
        > "$output/logs/input-mount.txt"
    mounted="$scratch/mounted"
    validate_app "$mounted/Batchalign.app" "$expected_version"
    app="$scratch/extracted/Batchalign.app"
    ditto "$mounted/Batchalign.app" "$app"
    hdiutil detach "$mounted"
    mounted=''
else
    python3 - "$expected_version" "$output/logs/tauri-version.json" <<'PY'
import json
import pathlib
import sys

pathlib.Path(sys.argv[2]).write_text(json.dumps({'version': sys.argv[1]}) + '\n')
PY
    printf 'Building ARM64 Batchalign %s\n' "$expected_version"
    (
        cd "$repo_root"
        # Keep Apple's upload/signing stage owned by this script. Tauri creates only
        # the app here; the final DMG must contain the already-stapled app.
        unset APPLE_ID APPLE_PASSWORD APPLE_TEAM_ID APPLE_API_KEY APPLE_API_ISSUER \
            APPLE_API_KEY_PATH APPLE_CERTIFICATE APPLE_CERTIFICATE_PASSWORD
        CARGO_TARGET_DIR="$repo_root/target" APPLE_SIGNING_IDENTITY=- \
            just batchalign gui build release --target aarch64-apple-darwin --bundles app \
            --config "$output/logs/tauri-version.json"
    ) 2>&1 | tee "$output/logs/build.log"
fi
validate_app "$app" "$expected_version"
printf 'version=%s\narchitecture=arm64\nidentity=%s\nsource_app=%s\nsource_dmg=%s\n' \
    "$expected_version" "$identity" "$app" "$input_dmg" > "$output/logs/release.txt"
shasum -a 256 "$app/Contents/Info.plist" "$app/Contents/MacOS/Batchalign" \
    "$app/Contents/MacOS/sidecar" > "$output/logs/source-sha256.txt"
xcrun notarytool --version > "$output/logs/notarytool-version.txt"
working_app="$output/Batchalign.app"
ditto "$app" "$working_app"
chmod u+x "$working_app/Contents/MacOS/Batchalign" "$working_app/Contents/MacOS/sidecar"
validate_app "$working_app" "$expected_version"

# Sign nested executable first, then seal the application bundle. No blanket entitlements.
codesign --force --sign "$identity" --timestamp --options runtime \
    --identifier org.talkbank.batchalign.sidecar "$working_app/Contents/MacOS/sidecar"
codesign --force --sign "$identity" --timestamp --options runtime "$working_app"
codesign --verify --deep --strict --verbose=2 "$working_app"
ditto -c -k --keepParent "$working_app" "$output/logs/app-upload.zip"
notarize_archive "$output/logs/app-upload.zip" app
xcrun stapler staple "$working_app"
xcrun stapler validate "$working_app"
spctl --assess --type execute --verbose=2 "$working_app" 2> "$output/logs/app-gatekeeper.txt"
ditto -c -k --keepParent "$working_app" "$output/Batchalign_${expected_version}_aarch64.app.zip"

# Package the stapled app, then give the outer disk image its own signature/ticket.
mkdir "$scratch/dmg-root"
ditto "$working_app" "$scratch/dmg-root/Batchalign.app"
ln -s /Applications "$scratch/dmg-root/Applications"
dmg="$output/Batchalign_${expected_version}_aarch64.dmg"
hdiutil create -volname Batchalign -srcfolder "$scratch/dmg-root" -fs HFS+ -format UDZO "$dmg"
codesign --sign "$identity" --timestamp "$dmg"
codesign --verify --strict --verbose=2 "$dmg"
notarize_archive "$dmg" dmg
xcrun stapler staple "$dmg"
xcrun stapler validate "$dmg"
hdiutil verify "$dmg"
spctl --assess --type open --context context:primary-signature --verbose=2 "$dmg" \
    2> "$output/logs/dmg-gatekeeper.txt"
(
    cd "$output"
    shasum -a 256 "Batchalign_${expected_version}_aarch64.app.zip" "Batchalign_${expected_version}_aarch64.dmg" \
        > SHA256SUMS
)
printf 'Verified ARM64 app and DMG: %s\n' "$output"
