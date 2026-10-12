\# Entorno de pruebas

PS C:\\Users\\jimen\\Documents\\AquaSense-Cassandra-Grupo5> systeminfo | Select-String "Nombre del sistema operativo","Memoria física total"



Nombre del sistema operativo:              Microsoft Windows 11 Home Single Language

Memoria física total:                      7 959 MB





PS C:\\Users\\jimen\\Documents\\AquaSense-Cassandra-Grupo5> Get-CimInstance Win32\_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors



Name                                      NumberOfCores NumberOfLogicalProcessors

\----                                      ------------- -------------------------

Intel(R) Core(TM) i7-1065G7 CPU @ 1.30GHz             4                         8

PS C:\\Users\\jimen\\Documents\\AquaSense-Cassandra-Grupo5> docker version --format "Docker {{.Server.Version}}"

Docker 29.8.1

PS C:\\Users\\jimen\\Documents\\AquaSense-Cassandra-Grupo5> docker info | Select-String "CPUs","Total Memory"



&#x20;CPUs: 8

&#x20;Total Memory: 3.711GiB

PS C:\\Users\\jimen\\Documents\\AquaSense-Cassandra-Grupo5> docker exec cassandra nodetool version

ReleaseVersion: 5.0.9

