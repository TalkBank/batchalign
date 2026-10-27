// Keep the homepage to three choices. Older stable releases fill any gaps;
// other architectures and package formats stay on the GitHub releases page.
const isX64 = asset => /x86_64|amd64|x64/i.test(asset.name);
const choices = {
  macos: asset => /\.dmg$/i.test(asset.name),
  windows: asset => isX64(asset) && /\.(exe|msi)$/i.test(asset.name),
  deb: asset => isX64(asset) && /\.deb$/i.test(asset.name),
  rpm: asset => isX64(asset) && /\.rpm$/i.test(asset.name),
};

function installerRank(key, asset) {
  if (key === 'windows') return /\.exe$/i.test(asset.name) ? 0 : 1;
  if (key === 'macos') return /universal/i.test(asset.name) ? 0 : /aarch64|arm64/i.test(asset.name) ? 1 : 2;
  return 0;
}

function showDownload(platform, installer, complete) {
  const link = document.getElementById(`download-${platform}`);
  const version = document.getElementById(`version-${platform}`);
  if (installer) {
    link.href = installer.asset.browser_download_url;
    version.textContent = installer.release.tag_name;
    link.title = `${installer.asset.name} (${installer.release.tag_name})`;
  } else {
    version.textContent = complete ? 'Not yet published' : 'All releases';
  }
}

async function loadDownloads() {
  const status = document.getElementById('download-status');
  if (!status) return;
  const found = {};
  let complete = false;
  try {
    for (let page = 1; ; page++) {
      const response = await fetch(`https://api.github.com/repos/TalkBank/batchalign/releases?per_page=100&page=${page}`, {
        headers: { Accept: 'application/vnd.github+json' },
        signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw new Error(`GitHub returned ${response.status}`);
      const releases = await response.json();
      for (const release of releases) {
        if (release.draft || release.prerelease) continue;
        for (const [key, matches] of Object.entries(choices)) {
          if (found[key]) continue;
          const asset = release.assets.filter(matches).sort((a, b) => installerRank(key, a) - installerRank(key, b))[0];
          if (asset) found[key] = { asset, release };
        }
      }
      if (Object.keys(found).length === 4 || releases.length < 100) { complete = true; break; }
    }
  } catch { /* The ordinary releases links remain usable without API access. */ }

  showDownload('macos', found.macos, complete);
  showDownload('windows', found.windows, complete);
  const linux = found.deb || found.rpm;
  showDownload('linux', linux, complete);
  if (found.macos) {
    const name = found.macos.asset.name;
    document.getElementById('detail-macos').textContent = /universal/i.test(name) ? 'Universal · DMG'
      : /aarch64|arm64/i.test(name) ? 'Apple silicon · DMG' : 'Intel · DMG';
  }
  for (const format of ['deb', 'rpm']) {
    const installer = found[format];
    if (!installer) continue;
    const link = document.getElementById(`download-${format}`);
    link.parentElement.hidden = false;
    link.href = installer.asset.browser_download_url;
    link.title = installer.release.tag_name;
    if (installer.release.tag_name !== linux.release.tag_name) link.textContent += ` (${installer.release.tag_name})`;
  }
  status.hidden = complete;
  if (!complete) status.textContent = 'See all releases if a download is unavailable.';
}

loadDownloads();
