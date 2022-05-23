#!/usr/local/bin/python3.7
# create-vpn
# Create VPN from JSON files
# Ramesh Natarajan, Solace PSG
# May 20, 2021

# USAGE:
# python3 bin/get-vpn-config.py --host http://lab-129-78:80 --vpn MyVpn --user admin --password admin --router lab-129-78
# python3 bin/create-vpn.py --host https://mr2webh7l7uck.messaging.solace.cloud:943 --datadir data/json/lab-129-78/vpns/MyVpn --user nram-hbk-test-vpn-admin --password xxxxx --vpn MyNewVpn

# REQUIREMENT
# Python 3.6


import sys, os
import getpass
import argparse
import pprint

sys.path.append(os.getcwd()+"/lib")
import SempV2Parser as SP
import Logger as SL

me = "create-vpn"
pp = pprint.PrettyPrinter(indent=4)

#------------------------------------------------------------------
# main
#------------------------------------------------------------------
def main(argv):
    config_url = "/SEMP/v2/config/msgVpns"

    p = argparse.ArgumentParser( prog=me,
   	description='create-vpn: \
       Create VPN Config recursivey with SEMPv2 from JSON configs',
        formatter_class=argparse.RawDescriptionHelpFormatter)   
    # Required args
    pr = p.add_argument_group("Required")
    pr.add_argument('--datadir', dest="datadir", required=True, help='dir with json files (eg:  data/json/local-docker/vpns/test-vpn)') 
    pr.add_argument('--host',  action="store", dest='host', required=True, help='Solace router URL (eg: http://localhost:8080)')
    pr.add_argument('--release',  dest='release', required=True, help='Solace release of host (eg: 9.9)')
    pr.add_argument('--tier',  dest='tier', help='Solace Tier for resource limit',
        choices=['100', '1k', '10k', '16k', '100k', '200k'])

    # Optional args
    po = p.add_argument_group("Optional")
    po.add_argument('--outdir', dest="outdir", default="data/json", help='output dir (default: data/json)') 
    po.add_argument('--cfgfile', dest="cfgfile", default="config/config.json", help='config json file (default: config/config.json)') 

    po.add_argument('--user', dest="user", default="admin", help='CLI username (default: admin)')
    po.add_argument('--password', dest="password", help='CLI user Password (default: <read from stdin>)') 
    po.add_argument('--verbose', '-v', action="count", default=0, help='Verbose mode: -v verbose, -vv debug, -vvv trace')
    po.add_argument('--vpn', dest="vpn", help='Target Solace VPN. VPN name from config used otherwise') 


    r = p.parse_args()

    if (not r.password):
          r.password = getpass.getpass("Enter password for "+ r.user + " : ")

    log = SL.Logger(me, r.verbose).SetupLogger()
    log.info(me + ": Starting config update for router {}".format(r.host))

    semp = SP.SempV2Parser(log, r, 1)
    url="{}{}".format(r.host,config_url)
    log.info("Post JSONs to {}".format(url))

    vpn_json_file = "{}/vpn.json". format(r.datadir)
    if not os.path.exists(vpn_json_file):
        log.error("No vpn.json file %s", vpn_json_file)
    
    semp.ReadConfigJSON(r.cfgfile, r.release, r.tier)
    json_data, links, next_page_uri = semp.ReadDataJSON(vpn_json_file);
    if r.vpn :
        vpn_name = r.vpn
        log.info('Using VPN name %s', vpn_name)
        semp.VpnName(vpn_name)
    else:
        vpn_name = json_data['msgVpnName']

    # -------------------------------------------------------------------
    log.info('Creating VPN %s', vpn_name)
    semp.Post(url, vpn_name, r.datadir, json_data, links, next_page_uri)

    print (f'VPN {vpn_name} successfully created on {url}')
    log.info(me + ": done")

if __name__ == "__main__":
    main(sys.argv[1:])