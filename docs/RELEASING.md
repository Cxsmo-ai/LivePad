# Releasing LivePad

Releases are tag-driven and reproducible on the Windows GitHub Actions runner.

## Local release checklist

```powershell
.\verify.ps1
.\package.ps1
.\bundle_all.ps1
```

Confirm the bundle contains exactly one `LivePad.exe`, includes the extension
mark and application mark, and contains no `.pak` or `.dfm` files. The build
scripts write SHA-256 files beside each release artifact.

## GitHub release

1. Update `version_info.txt` and the extension version in `manifest.json`.
2. Commit the change and push it to `main`.
3. Create and push an annotated tag, for example:

   ```powershell
   git tag -a v1.3.0 -m "LivePad v1.3.0"
   git push origin main --follow-tags
   ```

4. The `release.yml` workflow builds and publishes the complete ZIP, app
   folder ZIP, extension ZIP, guide, and checksum manifests.

The workflow does not publish hardware smoke results as if they were CI
results. Those remain a local elevated-machine verification step.
