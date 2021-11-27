# delete cluster if exists

class CycleConfig {
    [pscredential] $Credential;
    [string] $Url;
    [switch] $Insecure = $false;

    CycleConfig (
        [pscredential] $Credential,
        [string] $Url,
        [switch] $Insecure = $false
    ) {
        $this.Credential = $Credential;
        $this.Url = $Url;
        $this.Insecure = $Insecure;
    }
}

function Get-CycleCloudConfig {
    [CmdletBinding()]
    [OutputType([CycleConfig])]
    param (
        [Parameter()]
        [String] $Path = "~/.cycle/cred"
    )
    return (Import-CliXml -Path $Path)
}

function Set-CycleCloudConfig {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory, ParameterSetName = "Split", ValueFromPipelineByPropertyName)]
        [pscredential] $Credential,
        [Parameter(Mandatory, ParameterSetName = "Split", ValueFromPipelineByPropertyName)]
        [string] $Url,
        [Parameter(ParameterSetName = "Split", ValueFromPipelineByPropertyName)]
        [switch] $Insecure = $false,
        [Parameter(Mandatory, ParameterSetName = "Config", ValueFromPipelineByPropertyName)]
        [CycleConfig] $Config,
        [Parameter()]
        [String] $Path = "~/.cycle/cred"
    )

    New-Item -Path (Split-Path $Path) -ItemType Directory -Force

    if (-not $Config) {
        $Config = [CycleConfig]::new($Credential, $Url, $Insecure);
    }
    return ($Config | Export-CliXml -Path $Path)
}

function Invoke-CycleApi {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory)]
        [string] $Url,
        [Parameter(Mandatory)]
        [ValidateSet("Get", "Post", "Put", "Delete")]
        [string] $Method,
        [Parameter()]
        $Body = $null
    )
    if (-not $Script:CycleConfig) {
        $Script:CycleConfig = Get-CycleCloudConfig
    }

    Invoke-RestMethod `
        -Uri ($Script:CycleConfig.Url + '/' + $Url) `
        -Method $Method `
        -Body $Body `
        -AllowUnencryptedAuthentication `
        -SkipCertificateCheck:($Script:CycleConfig.Insecure) `
        -Authentication Basic `
        -Credential ($Script:CycleConfig.Credential)
}

function Get-CycleClusters {
    [CmdletBinding()]
    param (
        [Parameter()]
        [switch] $Detailed
    )
    Invoke-CycleApi `
        -Url 'cloud/clusters' `
        -Method 'Get' `
        -Body @{
            'summary' = (-not $Detailed)
        }
}

function New-CycleCluster {
    [CmdletBinding()]
    param (
        # Cluster name
        [Parameter(Mandatory)]
        [string]
        $Name,
        # Template name
        [Parameter()]
        [string]
        $Template,
        # parameters json
        [Parameter()]
        [string]
        $Parameters
    )

    Invoke-CycleApi `
        -Url "cloud/api/import_cluster/$Name" `
        -Method Post `
        -Body @{
            'template' = $Template;
            'parameters' = $Parameters;
        }
}
