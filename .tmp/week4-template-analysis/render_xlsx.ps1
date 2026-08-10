param(
    [Parameter(Mandatory = $true)] [string] $InputPath,
    [Parameter(Mandatory = $true)] [string] $OutputDir
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$excel = $null
$sourceBook = $null
$renderBook = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.ScreenUpdating = $true
    $sourceBook = $excel.Workbooks.Open($InputPath, 0, $true)
    $renderBook = $excel.Workbooks.Add()
    $canvas = $renderBook.Worksheets.Item(1)

    foreach ($sheet in $sourceBook.Worksheets) {
        $sourceBook.Activate()
        $sheet.Activate()
        $used = $sheet.UsedRange
        $used.CopyPicture(1, 2)

        $renderBook.Activate()
        $canvas.Activate()
        $width = [Math]::Max([double] $used.Width, 100)
        $height = [Math]::Max([double] $used.Height, 100)
        $chartObject = $canvas.ChartObjects().Add(0, 0, $width, $height)
        $chartObject.Chart.Paste() | Out-Null
        $safeName = [regex]::Replace($sheet.Name, '[\\/:*?"<>|]', '_')
        $outFile = Join-Path $OutputDir ($safeName + '.png')
        if (-not $chartObject.Chart.Export($outFile, 'PNG')) {
            throw "Excel failed to export $($sheet.Name)"
        }
        $chartObject.Delete()
        [Runtime.InteropServices.Marshal]::ReleaseComObject($used) | Out-Null
        [Runtime.InteropServices.Marshal]::ReleaseComObject($sheet) | Out-Null
        Write-Output $outFile
    }
}
finally {
    if ($renderBook -ne $null) {
        $renderBook.Close($false)
        [Runtime.InteropServices.Marshal]::ReleaseComObject($renderBook) | Out-Null
    }
    if ($sourceBook -ne $null) {
        $sourceBook.Close($false)
        [Runtime.InteropServices.Marshal]::ReleaseComObject($sourceBook) | Out-Null
    }
    if ($excel -ne $null) {
        $excel.Quit()
        [Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
