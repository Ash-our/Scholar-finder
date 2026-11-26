param([string]$JavaHome = '')
$ErrorActionPreference = 'Stop'
$scholarRoot = Split-Path -Parent $PSScriptRoot
$scholarRuntime = Join-Path $scholarRoot '.runtime'
if (-not $JavaHome) {
    $scholarJavaHomeFile = Join-Path $scholarRuntime 'java-home.txt'
    if (Test-Path -LiteralPath $scholarJavaHomeFile) { $JavaHome = (Get-Content -LiteralPath $scholarJavaHomeFile -Raw).Trim() }
}
if (-not $JavaHome) {
    $scholarCandidates = @($env:JAVA_HOME)
    $JavaHome = $scholarCandidates | Where-Object { $_ -and (Test-Path -LiteralPath (Join-Path $_ 'bin\java.exe')) } | Select-Object -First 1
}
if (-not $JavaHome) { throw 'Java 21 is required. Pass -JavaHome <JDK21 directory>.' }
$scholarJava = Join-Path $JavaHome 'bin\java.exe'
$scholarKafka = Join-Path $scholarRuntime 'kafka_2.13-3.9.1'
$scholarMongo = Get-ChildItem -LiteralPath $scholarRuntime -Directory -Filter 'mongodb-*' | Select-Object -First 1
if (-not $scholarMongo -or -not (Test-Path -LiteralPath $scholarKafka)) { throw 'Run python scripts/fetch-native-runtime.py first.' }
$scholarLogs = Join-Path $scholarRuntime 'logs'
$scholarMongoData = Join-Path $scholarRuntime 'mongo-data'
New-Item -ItemType Directory -Force -Path $scholarLogs,$scholarMongoData | Out-Null
function Test-ScholarPort([int]$Port) {
    $scholarSocket = [System.Net.Sockets.TcpClient]::new()
    try { $scholarSocket.Connect('127.0.0.1',$Port); return $true } catch { return $false } finally { $scholarSocket.Dispose() }
}
$scholarOwnedPath = Join-Path $scholarRuntime 'services.json'
$scholarOwned = @{}
if (Test-Path -LiteralPath $scholarOwnedPath) { $scholarOwned = Get-Content -LiteralPath $scholarOwnedPath -Raw | ConvertFrom-Json -AsHashtable }
if (-not (Test-ScholarPort 27017)) {
    $scholarMongoExe = Join-Path $scholarMongo.FullName 'bin\mongod.exe'
    $scholarMongoArgs = @('--dbpath',('"' + $scholarMongoData + '"'),'--bind_ip','127.0.0.1','--port','27017','--wiredTigerCacheSizeGB','0.25','--logpath',('"' + (Join-Path $scholarLogs 'mongo.log') + '"'),'--logappend')
    $scholarMongoProcess = Start-Process -FilePath $scholarMongoExe -ArgumentList $scholarMongoArgs -WindowStyle Hidden -PassThru
    $scholarOwned['mongo'] = $scholarMongoProcess.Id
}
if (-not (Test-ScholarPort 9092)) {
    $scholarKafkaData = (Join-Path $scholarRuntime 'kafka-data').Replace('\','/')
    $scholarConfig = Join-Path $scholarRuntime 'kafka.properties'
    @"
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@127.0.0.1:9093
listeners=PLAINTEXT://127.0.0.1:9092,CONTROLLER://127.0.0.1:9093
advertised.listeners=PLAINTEXT://127.0.0.1:9092
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT
log.dirs=$scholarKafkaData
num.partitions=3
default.replication.factor=1
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
group.initial.rebalance.delay.ms=0
log.retention.hours=24
"@ | Set-Content -LiteralPath $scholarConfig -Encoding ascii
    $scholarClasspath = Join-Path $scholarKafka 'libs\*'
    if (-not (Test-Path -LiteralPath (Join-Path $scholarRuntime 'kafka-data\meta.properties'))) {
        $scholarClusterId = [Convert]::ToBase64String([guid]::NewGuid().ToByteArray()).TrimEnd('=').Replace('+','-').Replace('/','_')
        & $scholarJava -cp $scholarClasspath kafka.tools.StorageTool format -t $scholarClusterId -c $scholarConfig
        if ($LASTEXITCODE -ne 0) { throw 'Kafka storage format failed.' }
    }
    $scholarKafkaArgs = @('-Xms256m','-Xmx512m','-cp',('"' + $scholarClasspath + '"'),'kafka.Kafka',('"' + $scholarConfig + '"'))
    $scholarKafkaProcess = Start-Process -FilePath $scholarJava -ArgumentList $scholarKafkaArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $scholarLogs 'kafka.out.log') -RedirectStandardError (Join-Path $scholarLogs 'kafka.err.log')
    $scholarOwned['kafka'] = $scholarKafkaProcess.Id
}
$scholarOwned | ConvertTo-Json | Set-Content -LiteralPath $scholarOwnedPath -Encoding utf8
Write-Output ('Service process IDs recorded in ' + $scholarOwnedPath)
Write-Output 'MongoDB: 127.0.0.1:27017; Kafka: 127.0.0.1:9092. Check health before use.'
