# Solace service Management with SEMPv2

## About

## Commands

### import from lab

python3 bin/get-vpn-config.py --host http://lab-129-78:80 --vpn atg-poc --user admin --password admin --router lab-129-78 -v

### export to lab

python3 bin/create-vpn.py --host http://lab-128-27:80 --datadir data/json/lab-129-78/vpns//atg-poc ---user admin --password admin -v

### export to local docker

 python3 bin/create-vpn.py --host http://localhost:8080 --datadir data/json/lab-129-78/vpns//atg-poc --user admin --password admin --version soltr9.6 --tier tier1k -v

### Export to cloud

python3 bin/create-vpn.py --host https://mr2webh7l7uck.messaging.solace.cloud:943 --datadir data/json/lab-129-78/vpns/DallasGlobalProd --user nram-hbk-test-vpn-admin --password xxxxx --vpn nram-hbk-test-vpn