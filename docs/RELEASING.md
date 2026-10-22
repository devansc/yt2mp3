# Releasing

Releases are built and published by GitHub Actions
(`.github/workflows/release.yml`). Each release has two DMGs attached:
`yt2mp3-AppleSilicon.dmg` and `yt2mp3-Intel.dmg`.

## When to release

- After changing the app.
- **When downloads start failing.** The app bundles yt-dlp and can't update it,
  and YouTube changes often enough that an old build eventually stops working.
  Every build installs the newest yt-dlp, so publishing a new release (even
  with no code changes) is the fix.

## How to release

Pushes to `main` do **not** build anything. A release is made by either:

**Pushing a version tag**

```bash
git tag v1.0.1
git push origin v1.0.1
```

**Or from GitHub:** Actions tab → **Release** → **Run workflow** → enter a
version like `v1.0.1`. The tag is created on the latest commit of `main`.

Use a new version number each time (`v1.0.1`, `v1.1.0`, …). The build takes
about 5–10 minutes. Progress is under the Actions tab, and the result shows up
under Releases.

## What the workflow does

1. **build** (two jobs in parallel), each on a GitHub-hosted Mac of the matching
   chip type:
   - `macos-15` (Apple Silicon) runs `./build_mac.sh arm`
   - `macos-15-intel` (Intel) runs `./build_mac.sh intel`

   Each uploads its DMG as a workflow artifact.
2. **release** collects both DMGs and runs `gh release create <tag>` with
   auto-generated release notes (a list of commits since the last release).

If a build job fails, no release is created. Fix the problem and push a new tag.
To retry the same version, delete its tag first
(`git push --delete origin v1.0.1 && git tag -d v1.0.1`).

## Download links

These URLs always point to the newest release, so links to them never need
updating:

```
https://github.com/devansc/yt2mp3/releases/latest/download/yt2mp3-AppleSilicon.dmg
https://github.com/devansc/yt2mp3/releases/latest/download/yt2mp3-Intel.dmg
```

They're used by the README and by the yt2mp3 page on
[devan-carlson.com](https://www.devan-carlson.com/yt2mp3) (in the
`devancarlson-website` repo). Don't rename the DMG files in `build_mac.sh`
without updating those links.

The repository must stay **public**. Release files in a private repo can only be
downloaded by people with access to it.

## Building a release by hand

If Actions is unavailable, build locally and upload:

```bash
./build_mac.sh all
gh release create v1.0.1 dist/yt2mp3-AppleSilicon.dmg dist/yt2mp3-Intel.dmg --generate-notes
```
