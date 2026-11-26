param([int]$Port=8000,[ValidateSet('pinggy','localhost.run')][string]$Provider='pinggy')
$ErrorActionPreference='Stop'
$scholarRoot=Split-Path -Parent $PSScriptRoot
$scholarRuntime=Join-Path $scholarRoot '.runtime'
$scholarLogs=Join-Path $scholarRuntime 'logs'
$scholarStatePath=Join-Path $scholarRuntime 'public-preview.json'
$scholarKey=Join-Path $scholarRuntime 'preview_ed25519'
$scholarKnownHosts=Join-Path $scholarRuntime 'preview_known_hosts'
$scholarSsh=(Get-Command ssh.exe -ErrorAction Stop).Source
$scholarHealth=Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 5
if($scholarHealth.application -ne 'scholarship-map'){throw 'Start ScholarshipMap first.'}
New-Item -ItemType Directory -Force -Path $scholarLogs|Out-Null
if(-not(Test-Path -LiteralPath $scholarKey)){
    & ssh-keygen.exe -q -t ed25519 -N '' -f $scholarKey *> (Join-Path $scholarLogs 'preview-key.log')
    if($LASTEXITCODE -ne 0){throw 'Could not create the checkout-local tunnel key.'}
}
# This dedicated key and known-hosts file isolate the preview from personal SSH keys/config.
$scholarArgs=@('-T','-F','NUL','-i',('"'+$scholarKey+'"'),'-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','StrictHostKeyChecking=accept-new','-o',('UserKnownHostsFile="'+$scholarKnownHosts+'"'),'-o','ServerAliveInterval=30','-o','ServerAliveCountMax=3','-o','ExitOnForwardFailure=yes','-o','ConnectTimeout=12')
if($Provider -eq 'pinggy'){$scholarArgs+=@('-p','443','-R',"0:127.0.0.1:$Port",'free.pinggy.io')}
else{$scholarArgs+=@('-R',"80:127.0.0.1:$Port",'nokey@localhost.run')}
$scholarState=if(Test-Path -LiteralPath $scholarStatePath){Get-Content -LiteralPath $scholarStatePath -Raw|ConvertFrom-Json -AsHashtable}else{$null}
if($scholarState -and ($scholarState.provider -ne $Provider -or $scholarState.port -ne $Port)){
    & (Join-Path $PSScriptRoot 'Stop-PublicPreview.ps1')
    $scholarState=$null
}
$scholarProcess=if($scholarState -and $scholarState.provider -eq $Provider -and $scholarState.port -eq $Port){Get-Process -Id $scholarState.pid -ErrorAction SilentlyContinue}else{$null}
if(-not $scholarProcess -or $scholarProcess.Path -ne $scholarSsh){
    $scholarProcess=Start-Process -FilePath $scholarSsh -ArgumentList $scholarArgs -WorkingDirectory $scholarRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $scholarLogs 'share-preview.out.log') -RedirectStandardError (Join-Path $scholarLogs 'share-preview.err.log')
    $scholarState=@{pid=$scholarProcess.Id;provider=$Provider;port=$Port;url=$null;started_at=[DateTimeOffset]::UtcNow.ToString('o')}
}
$scholarState|ConvertTo-Json|Set-Content -LiteralPath $scholarStatePath -Encoding utf8
for($scholarAttempt=0;$scholarAttempt -lt 80;$scholarAttempt++){
    $scholarText=(Get-Content -LiteralPath (Join-Path $scholarLogs 'share-preview.out.log') -Raw -ErrorAction SilentlyContinue)+' '+(Get-Content -LiteralPath (Join-Path $scholarLogs 'share-preview.err.log') -Raw -ErrorAction SilentlyContinue)
    $scholarUrlPattern=if($Provider -eq 'pinggy'){'https://[a-z0-9-]+\.(?:(?:a|run)\.)?pinggy(?:-free)?\.(?:link|life)'}else{'https://(?!admin\.)[a-z0-9-]+\.(?:app\.)?(?:lhr\.life|localhost\.run)'}
    $scholarUrls=[regex]::Matches($scholarText,$scholarUrlPattern)
    if($scholarUrls.Count){
        # Free domains rotate while SSH remains connected; the last notice wins.
        $scholarUrl=$scholarUrls[$scholarUrls.Count-1].Value
        try{
            $scholarPublic=Invoke-RestMethod "$scholarUrl/api/health" -UserAgent 'ScholarshipMapPreview/1.0' -TimeoutSec 5
            if($scholarPublic.application -ne 'scholarship-map'){throw 'Public URL is not this app.'}
            $scholarState.url=$scholarUrl
            $scholarState.mode='temporary_local_https_tunnel'
            $scholarState|ConvertTo-Json|Set-Content -LiteralPath $scholarStatePath -Encoding utf8
            Write-Output $scholarUrl
            Write-Output 'Verified public HTTPS preview. Keep the computer, services and SSH process running.'
            return
        }catch{}
    }
    if($scholarProcess.HasExited){throw 'Preview SSH exited; inspect .runtime/logs/share-preview.err.log.'}
    Start-Sleep -Milliseconds 500
}
throw 'No verified public URL yet; inspect the share-preview logs. The owned process ID was retained.'
