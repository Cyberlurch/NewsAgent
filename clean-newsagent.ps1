<#
.SYNOPSIS
    Safely cleans transcript caches for NewsAgent
.DESCRIPTION
    This script removes only the raw transcript files (*.txt) in:
      • src/cache/
    It preserves:
      • Translation cache
      • Summaries
      • Groq and yt-dlp metadata
    Use this before a new run if you want fresh transcripts from YouTube.
#>

Write-Host "🧹 Cleaning transcript cache in src/cache/ ..."

$cachePath = "src/cache"
if (-Not (Test-Path $cachePath)) {
    Write-Warning "Cache path not found: $cachePath"
    exit
}

# Delete only .txt files directly in src/cache
Get-ChildItem -Path $cachePath -Filter *.txt -File |
    ForEach-Object {
        try {
            Remove-Item $_.FullName -Force
            Write-Host "Deleted:" $_.Name
        } catch {
            Write-Warning "Could not delete $_.Name → $_"
        }
    }

Write-Host "`n✅ Done. Transcript cache cleaned safely."
