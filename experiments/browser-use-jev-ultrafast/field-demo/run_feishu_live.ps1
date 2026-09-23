param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('A', 'B', 'C')]
  [string]$Scenario,
  [string]$Query = 'project',
  [string]$Prompt = ''
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$key = [Environment]::GetEnvironmentVariable('TYPESAFE_API_KEY', 'User')
if ([string]::IsNullOrWhiteSpace($key)) {
  throw 'TYPESAFE_API_KEY is missing in Windows User scope; browser automation was not started.'
}

# The key exists only in this launcher child and the uv child; it is never printed or written.
$env:TYPESAFE_API_KEY = $key
$args = @(
  'run', '--project', '.tmp/jev-ultrafast', 'python',
  'experiments/browser-use-jev-ultrafast/field-demo/run_feishu_browser.py',
  '--scenario', $Scenario,
  '--query', $Query,
  '--output-root', 'field-recordings'
)
if ($Scenario -eq 'B') { $args += '--allow-visible-data' }
if (-not [string]::IsNullOrWhiteSpace($Prompt)) { $args += @('--prompt', $Prompt) }

Push-Location $repo
try {
  & uv @args
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}
