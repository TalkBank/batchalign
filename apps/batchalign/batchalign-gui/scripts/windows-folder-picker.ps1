param([Parameter(Mandatory=$true)][string]$Application, [Parameter(Mandatory=$true)][string]$Folder)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$app = @(Get-Process | Where-Object {
    $_.Path -and [String]::Equals($_.Path, $Application, [StringComparison]::OrdinalIgnoreCase)
})
if ($app.Count -ne 1) { throw "Expected one installed app, found $($app.Count)" }
$processCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $app[0].Id)
$classCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty, '#32770')
$condition = New-Object System.Windows.Automation.AndCondition($processCondition, $classCondition)
$main = [System.Windows.Automation.AutomationElement]::FromHandle($app[0].MainWindowHandle)
$dialog = $null
for ($attempt = 0; $attempt -lt 100; $attempt++) {
    $dialog = $main.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
    if ($dialog) { break }
    Start-Sleep -Milliseconds 100
}
if (!$dialog) { throw 'Native folder picker did not open' }
$controls = $dialog.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition)
$edits = @($controls | Where-Object {
    $_.Current.ClassName -eq 'Edit' -and $_.Current.AutomationId -eq '1152'
})
$buttons = @($controls | Where-Object {
    $_.Current.ClassName -eq 'Button' -and
    $_.Current.AutomationId -eq '1'
})
if ($edits.Count -ne 1 -or $buttons.Count -ne 1) {
    $controls | ForEach-Object { "$($_.Current.ControlType.ProgrammaticName) $($_.Current.AutomationId) $($_.Current.Name)" }
    throw 'Could not identify the folder field and Select Folder button'
}
# Some Windows builds expose these Win32 controls as UIA panes without
# Value/Invoke patterns. Address the actual native controls by their HWNDs.
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class BatchalignFolderDialog {
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern IntPtr SendMessage(IntPtr hwnd, uint message, IntPtr wParam, string text);
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool PostMessage(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam);
}
'@
$editHandle = [IntPtr]$edits[0].Current.NativeWindowHandle
$buttonHandle = [IntPtr]$buttons[0].Current.NativeWindowHandle
if ($editHandle -eq [IntPtr]::Zero -or $buttonHandle -eq [IntPtr]::Zero) { throw 'Missing native dialog control handles' }
if ([BatchalignFolderDialog]::SendMessage($editHandle, 0x000C, [IntPtr]::Zero, $Folder) -eq [IntPtr]::Zero) {
    throw 'Could not enter the folder path'
}
if (![BatchalignFolderDialog]::PostMessage($buttonHandle, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)) {
    throw 'Could not click Select Folder'
}
Write-Output "Selected folder through native dialog: $Folder"
