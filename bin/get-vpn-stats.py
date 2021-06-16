#!/usr/local/bin/python3.7
# get VPN stats with SEMPv2 monitoring API

# USAGE:
# see get-vpn-stats.py -h

# REQUIREMENT
# Python 3.6

import sys, os
import getpass
import argparse
import pprint

sys.path.append(os.getcwd()+"/lib")
import SempV2Parser as SP
import Logger as SL

me = "get-vpn-stats"
pp = pprint.PrettyPrinter(indent=4)

#------------------------------------------------------------------
# main
#------------------------------------------------------------------
def main(argv):
    config_url = "/SEMP/v2/monitor/msgVpns/"

    p = argparse.ArgumentParser( prog=me,
   	description='get-vpn-stats: \
       Get VPN Stats recursivey with SEMPv2 monitoring API and store JSON output in directly tree',
        formatter_class=argparse.RawDescriptionHelpFormatter)   
    # Required args
    pr = p.add_argument_group("Required")
    pr.add_argument('--host',  action="store", dest='host', required=True, help='Solace router URL')
    pr.add_argument('--vpn', dest="vpn", required=True, help='Solace VPN') 
    pr.add_argument('--object', dest="object", required=True, help='Solace Object to query stats', 
      choices = ['vpn', 'clients', 'queues', 'topicEndpoints', 'bridges', 'restDeliveryPoints']) 

    # Optional args
    po = p.add_argument_group("Optional")
    po.add_argument('--user', dest="user", default="admin", help='CLI username (default: admin)')
    po.add_argument('--password', dest="password", help='CLI user Password (default: <read from stdin>)') 
    po.add_argument('--outdir', dest="outdir", default="data/json", help='Output dir (default: data/json)') 
    po.add_argument('--router', dest="routername", default="solace", help="Router-name for display/output path (default: solace)")
    po.add_argument('--verbose', '-v', action="count", default=0, help='Verbose mode: -v verbose, -vv debug, -vvv trace')
    po.add_argument('--count', dest="count", default=100, help="Collection query page size. (default: 100 (max))")


    r = p.parse_args()

    if (not r.password):
          r.password = getpass.getpass("Enter password for "+ r.user + " : ")

    log = SL.Logger(me, r.verbose).SetupLogger()
    log.info(me + ": Starting stats query for router {}".format(r.routername))

    semp = SP.SempV2Parser(log, r)
    if r.object == 'vpn':
        url="{}{}{}".format(r.host,config_url,r.vpn)
    else:
        url="{}{}{}/{}".format(r.host,config_url,r.vpn, r.object)

    log.info("Getting JSONs from {}".format(url))

    # Get VPN Config
    json_data = semp.Get(url)
    outdir="{}/{}/vpns/".format(r.outdir, r.routername)
    outfile='{}/{}.json'.format(r.vpn, r.object)
    log.info("File {} written to Output dir {}".format(outfile, outdir))
    semp.WriteJSON(outdir, outfile, json_data)

    # Process Links from the VPN.
    # and recursivey process all subsequent links
    semp.processLink(url, False, True, False) # url, no-collection, do-paging, don't-follow-url
    #semp.ProcessLinks(json_data)
    log.info(me + ": done")
    print(me + ": done")

if __name__ == "__main__":
    main(sys.argv[1:])
