$Script:Helper = "https://downloaders.azurewebsites.net/downloaders/mlnx_ofed_downloader/helper.php";

Class OfedVersions : System.Management.Automation.IValidateSetValuesGenerator {
    [string[]] GetValidValues() {
        return (Get-OfedVersions).versions
    }

    [string[]] $versions;
    [string[]] $ga;
    [string] $latest;
}
function Get-OfedVersions {
    [OutputType([OfedVersions])]
    [CmdletBinding()]
    param (
    )

    $versions = Invoke-RestMethod -Uri $Script:helper `
        -Method "POST" `
        -Body @{
        action = 'get_versions'
    }
    [OfedVersions] $versions
}

function Get-OfedDistros {
    [OutputType([string[]])]
    [CmdletBinding()]
    param (
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type Versions } )]
        [string]
        $Version
    )

    $distros = Invoke-RestMethod -Uri $Script:helper `
        -Method "POST" `
        -Body @{
        action  = 'get_distros'
        version = $Version
    }

    [string[]] $distros
}

class OfedDistros: System.Management.Automation.IValidateSetValuesGenerator {
    [string[]] GetValidValues() {
        return (Get-OfedDistros)
    }
}

function Get-OfedOSes {
    [OutputType([string[]])]
    [CmdletBinding()]
    param (
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type Versions } )]
        [string]
        $Version,
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type Distros } )]
        [string]
        $Distro
    )

    $osvers = Invoke-RestMethod -Uri $helper `
        -Method "POST" `
        -Body @{
        action  = 'get_oses'
        version = $Version
        distro  = $Distro
    }    

    $osvers
}

function Get-OfedArches {
    [OutputType([string[]])]
    [CmdletBinding()]
    param (
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type Versions } )]
        [string]
        $Version,
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type Distros } )]
        [string]
        $Distro,
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type OSes } )]
        [string]
        $OS
    )

    $arches = Invoke-RestMethod -Uri $helper `
        -Method "POST" `
        -Body @{
        action  = 'get_arches'
        version = $Version
        distro  = $Distro
        os      = $OS
    }

    $arches
}

function Get-OfedDownloadInfo {
    [OutputType([OfedDownloadInfo[]])]
    [CmdletBinding()]
    param (
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type Versions } )]
        [string]
        $Version,
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type Distros } )]
        [string]
        $Distro,
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type OSes } )]
        [string]
        $OS,
        [Parameter(Mandatory)]
        [ArgumentCompleter( { OfedArgumentCompleter @args -Type Arches } )]
        [string]
        $Arch
    )

    $download_info = Invoke-RestMethod -Uri $helper `
        -Method "POST" `
        -Body @{
        action  = 'get_download_info'
        version = $Version
        distro  = $Distro
        os      = $OS
        arch    = $Arch
    }

    # [OfedDownloadInfo]$download_info
    $download_info
}

class OfedDownloadInfo {
    [OfedDocs[]] $docs;
    [OfedFiles[]] $files;
}

class OfedDocs {
    [string] $desc;
    [Uri] $url;
}

class OfedFiles {
    [string] $file;
    [string] $desc;
    [string] $size;
    [string] $md5sum;
    [string] $sha;
    [string] $note;
    [uri] $url;
}

function OfedArgumentCompleter {
    param ( $commandName,
        $parameterName,
        $wordToComplete,
        $commandAst,
        $fakeBoundParameters,
        [ValidateSet('Distros', 'Versions', 'OSes', 'Arches')]
        $type )
    $wordToComplete = $wordToComplete.TrimStart("'`"")
    switch ($type.ToLower()) {
        'distros' {
            $completions = Get-OfedDistros -Version $fakeBoundParameters.Version
        }
        'versions' {
            $completions = (Get-OfedVersions).versions
        }
        'oses' {
            $completions = Get-OfedOSes -Version $fakeBoundParameters.Version -Distro $fakeBoundParameters.Distro
        }
        'arches' {
            $completions = Get-OfedArches -Version $fakeBoundParameters.Version -Distro $fakeBoundParameters.Distro -OS $fakeBoundParameters.OS
        }
    }

    $resultList = [System.Collections.Generic.List[System.Management.Automation.CompletionResult]]::new()
    $wordToComplete = $wordToComplete.Trim(("'", '"'))
    $completions | ForEach-Object {
        if ($_.StartsWith($wordToComplete, [System.StringComparison]::CurrentCultureIgnoreCase)) {
            $resultList.Add([System.Management.Automation.CompletionResult]::new("'$_'"))
        }
    }
    return $resultList
}

function Get-OfedRealUrl {
    [OutputType([string])]
    [CmdletBinding()]
    param (
        [Parameter(Mandatory, ValueFromPipeline)]
        [string]
        $Url
    )

    $regex = 'mrequest=(?<mrequest>.*?)&mtype=(?<mtype>.*?)&mver=(?<mver>.*?)&mname=(?<mname>.*[^&])'
    $match = [regex]::Match($Url, $regex)
    $url = 'https://content.mellanox.com/' +
    $match.Groups['mtype'].Value + '/' +
    $match.Groups['mver'].Value + '/' +
    $match.Groups['mname'].Value

    return $url
}
