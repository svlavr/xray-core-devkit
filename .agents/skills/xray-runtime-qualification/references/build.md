# Selected build, OS, ABI and native compatibility mode

Pin source revision/diff, dependency selection and exact command; record Go and
required generator/tool versions, GOOS/GOARCH, CGO, tags, generated/assembly files,
selected packages and environment constraints. Inspect the actual selection
using scoped `go env` and `go list` when assigned. No startup-wide build matrix
or unrelated platform qualification is implied.

`mu_build_qualifier` diagnoses the first causal failure and separates module
download/authentication, tool/generator mismatch, compile/link errors, fixture
failures and runtime ABI/native-load failures. Preserve the failing command,
exit status and relevant bounded output. Do not hide a child failure behind a
pipeline's exit zero; confirm required test/benchmark cases actually ran.
Main assigns builds and fixes to an authorized worker through the managed runner.
Missing toolchain or target access remains an explicit gate.

For an accepted artifact, record its hash, target/toolchain, exported or binding
symbols and actual consumer API/ABI. A library build, CLI startup, cross-build
and native load/lifecycle are distinct witnesses. Route a real accepted Android
artifact to `xray-fork-android-validation` for its selected build/load/binding/
lifecycle scope. A built library/AAR does not establish JNI, VPN/TUN, application
integration or device success; do not create a competing downstream bridge owner.

In **native/upstream compatibility mode**, upstream research supplies exact
changed APIs/defaults/errors/build selections and dependent consumers. The test
architect and affected specialist define meaningful stock/native and explicitly
selected extension controls; workers run them and the behavior reviewer follows
the actual library/configuration/CLI caller. Protocol/wire seams use
`xray-protocol-compatibility`. Record retained, changed-with-reason, unsupported
and unknown behavior separately. Compile success alone is not trust,
cancellation, semantic compatibility or source-export acceptance.

Return the qualification map, actual commands/results, failure classes and
remaining source/host/artifact/device/release gates. Main retains integration
and any separately authorized publication; a qualifier never publishes binaries.
