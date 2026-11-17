param(
    [switch]$Clean,
    [string]$MinPythonVersion = "3.11"
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Resolve-PythonCommand {
    param(
        [Version]$MinVersion
    )

    function Get-PythonVersion {
        param(
            [string]$Cmd,
            [string[]]$Args
        )

        try {
            $ver = & $Cmd @($Args + @('-c', 'import sys; v=sys.version_info; print(v[0], v[1], v[2], sep=chr(46))'))
            if ($LASTEXITCODE -ne 0) {
                return $null
            }
            return [Version]($ver.Trim())
        }
        catch {
            return $null
        }
    }

    function Get-PythonExecutable {
        param(
            [string]$Cmd,
            [string[]]$Args
        )

        try {
            $exe = & $Cmd @($Args + @('-c', 'import sys; print(sys.executable)'))
            if ($LASTEXITCODE -ne 0) {
                return $null
            }
            return $exe.Trim()
        }
        catch {
            return $null
        }
    }

    function Test-PythonCandidate {
        param(
            [string]$Cmd,
            [string[]]$Args,
            [Version]$MinVersion
        )

        $v = Get-PythonVersion -Cmd $Cmd -Args $Args
        if (-not $v) {
            return $false
        }
        return ($v -ge $MinVersion)
    }

    $candidates = @(
        @{ Cmd = 'py'; Args = @('-3') },
        @{ Cmd = 'python'; Args = @() },
        @{ Cmd = 'python3'; Args = @() }
    )

    foreach ($c in $candidates) {
        $exists = Get-Command $c.Cmd -ErrorAction SilentlyContinue
        if ($exists -and (Test-PythonCandidate -Cmd $c.Cmd -Args $c.Args -MinVersion $MinVersion)) {
            $detected = Get-PythonVersion -Cmd $c.Cmd -Args $c.Args
            $exe = Get-PythonExecutable -Cmd $c.Cmd -Args $c.Args
            if (-not $exe) {
                continue
            }
            Write-Host "Using Python $detected via '$($c.Cmd) $($c.Args -join ' ')'."
            return @{ Cmd = $c.Cmd; Args = $c.Args; Exe = $exe; Version = $detected }
        }
    }

    throw "Python $MinVersion+ not found. Install Python from https://www.python.org/downloads/windows/ and check 'Add python.exe to PATH'."
}

if ($Clean) {
    if (Test-Path build) { Remove-Item -Recurse -Force build }
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
}

$minVersionObj = [Version]$MinPythonVersion
try {
    $py = Resolve-PythonCommand -MinVersion $minVersionObj
    $bootstrapPython = $py.Exe

    if (-not (Test-Path .venv)) {
        & $bootstrapPython -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment using $bootstrapPython"
        }
    }

    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) {
        throw "Virtual environment python not found at $python"
    }

    & $python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
    & $python -m pip install -e ".[web,build]"
    if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }
    & $python -m PyInstaller --noconfirm --clean packaging/ngfw-appdetector.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

    Write-Host ""
    Write-Host "Build complete."
    Write-Host "Executable folder: dist\ngfw-appdetector\"
    Write-Host "Run command: dist\ngfw-appdetector\ngfw-appdetector.exe serve --no-browser --port 8765"
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
