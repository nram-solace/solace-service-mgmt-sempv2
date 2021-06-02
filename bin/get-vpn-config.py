#!/usr/local/bin/python3.7
# GetVpnConfig
# Get VPN Configs with SEMPv2 in JSON
# Ramesh Natarajan, Solace PSG
# May 20, 2021

# USAGE:
# python3 bin/get-vpn-config.py --host http://lab-129-78:80 --vpn DallasGlobalProd --user admin --password admin --router lab-129-78 
# python3 bin/create-vpn.py --host https://mr2webh7l7uck.messaging.solace.cloud:943 --datadir data/json/lab-129-78/vpns/DallasGlobalProd --user nram-hbk-test-vpn-admin --password xxxxx --vpn nram-hbk-test-vpn

# REQUIREMENT
# Python 3.6

import sys, os
import getpass
import argparse
import pprint

sys.path.append(os.getcwd()+"/lib")
import SempV2Parser as SP
import Logger as SL

me = "get-vpn-config"
pp = pprint.PrettyPrinter(indent=4)

#------------------------------------------------------------------
# main
#------------------------------------------------------------------
def main(argv):
    config_url = "/SEMP/v2/config/msgVpns/"

    p = argparse.ArgumentParser( prog=me,
   	description='get-vpn-config: \
       Get VPN Config recursivey with SEMPv2 and store JSON output in directly tree',
        formatter_class=argparse.RawDescriptionHelpFormatter)   
    # Required args
    pr = p.add_argument_group("Required")
    pr.add_argument('--host',  action="store", dest='host', required=True, help='Solace router URL')
    pr.add_argument('--vpn', dest="vpn", required=True, help='Solace VPN') 
    # Optional args
    po = p.add_argument_group("Optional")
    po.add_argument('--user', dest="user", default="admin", help='CLI username (default: admin)')
    po.add_argument('--password', dest="password", help='CLI user Password (default: <read from stdin>)') 
    po.add_argument('--outdir', dest="outdir", default="data/json", help='Output dir (default: data/json)') 
    po.add_argument('--router', dest="routername", default="solace", help="Router-name for display/output path (default: solace)")
    po.add_argument('--verbose', '-v', action="count", default=0, help='Verbose mode: -v verbose, -vv debug, -vvv trace')
    po.add_argument('--count', dest="count", default=0, help="Collection query page size. (default: 0 - No paging. Return 10 elements)")


    r = p.parse_args()

    if (not r.password):
          r.password = getpass.getpass("Enter password for "+ r.user + " : ")

    log = SL.Logger(me, r.verbose).SetupLogger()
    log.info(me + ": Starting config query for router {}".format(r.routername))

    semp = SP.SempV2Parser(log, r)
    url="{}{}{}".format(r.host,config_url,r.vpn)
    log.info("Getting JSONs from {}".format(url))

    # Get VPN Config
    json_data = semp.Get(url)
    outdir="{}/{}/vpns/".format(r.outdir, r.routername)
    log.info("Output dir {}/{}".format(outdir, r.vpn))
    semp.WriteJSON(outdir, r.vpn+'/vpn.json', json_data)

    # Process Links from the VPN.
    # and recursivey process all subsequent links
    semp.ProcessLinks(json_data)
    log.info(me + ": done")
    print(me + ": done")

if __name__ == "__main__":
    main(sys.argv[1:])
