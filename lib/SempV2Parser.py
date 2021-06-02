# SempV2Parser
# Yet Another SEMPv2 Parser
# SEMPv2 REST POST, JSON processing & kitchen sink of other stuff
#    Supports processing Links recursively and gets data for all Link'ed objects
#    Supports NextPageUri (cursor paging) and pulls contents (as well as link contents) from cursor URLs
#    Supports getting N number of objects for collection objects with ?count query param
#    NOTE: SEMPv2 places a limit of 100 / call. You won't get more than 100 even if URL?count=100000
# Ramesh Natarajan, Solace PSG
# May 20, 2021

import sys, os
import string, re

import requests
import json
#from importlib_resources import read_text
import logging, inspect
import urllib, pathlib

import pprint
pp = pprint.PrettyPrinter(indent=4)

# used in get_unique_fname()
objmap = {}

class SempV2Parser:
    'Solace SEMP V2 REST connection implementation & util functions'

    #--------------------------------------------------------------
    # Constructor
    #--------------------------------------------------------------
    def __init__(self, log, r, op = 0 ):
        #self.logger = logging.getLogger(me)
        log.enter ("%s::%s : %s %s %s (verbose: %d)", __name__, inspect.stack()[0][3], r.host, r.user, r.host, r.verbose)

        self.cliuser = r.user
        self.passwd = r.password
        self.logfile = "log/POS2Parser.log"
        self.verbose = r.verbose
        self.log = log
        if op == 0 : # create - skip some env
            self.count = r.count
            self.outdir="{}/{}/vpns/".format(r.outdir, r.routername)

        # collections that doesn't support paging
        self.nopaging = ['tlsTrustedCommonNames', 'remoteMsgVpns'] 
        # vpn name override
        self.is_vpnname_set = False
        self.vpname = ''

    # Get
    def Get(self, url, collections=False, json_data=None):
        verb='get'
        log = self.log
        log.enter ("%s::%s url = %s", __name__, inspect.stack()[0][3], url)

        if collections:
            paging = True
            if int(self.count) == 0:
                paging = False
            # some elements throw 400 not supported if page count is sent
            if os.path.split(url)[1] in self.nopaging:
                paging = False
                log.info ("Skipping paging for element {}".format(os.path.split(url)[1]))
            if paging :
                log.debug("== Get collection URL {} (page count: {})".format(url, self.count))
                req = getattr(requests, verb)(url, 
                   headers={"content-type": "application/json"},
                   auth=(self.cliuser, self.passwd),
                   params={'count':self.count},
                   data=(json.dumps(json_data) if json_data != None else None))
            else:
                log.debug("== Get collection URL {} (no paging)".format(url))
                req = getattr(requests, verb)(url, 
                   headers={"content-type": "application/json"},
                   auth=(self.cliuser, self.passwd),
                   data=(json.dumps(json_data) if json_data != None else None))
        else:
            log.debug("-- Get object URL {}".format(url))
            req = getattr(requests, verb)(url, 
                headers={"content-type": "application/json"},
                auth=(self.cliuser, self.passwd),
                data=(json.dumps(json_data) if json_data != None else None))
        #print("Get: req.json()")
        #pp.pprint(req.json())
        if (req.status_code != 200):
            log.info(req.text)
            raise RuntimeError
        else:
            return req.json()

    def postit(self, url, json_data):
        verb = 'post'
        log = self.log
        log.enter ("%s::%s url = %s", __name__, inspect.stack()[0][3], url)

       # check if obj should be ignored
        my_keys = set(json_data.keys())
        ignore_keys = self.config['ignore-tags'].keys()
        s = my_keys.intersection(ignore_keys)
        if (len(s) > 0):
            t = s.pop()
            v = json_data[t]
            if v in self.config['ignore-tags'][t] :
                log.info ('Skipping %s : %s ', t, v)
                resp = requests.models.Response()
                resp.status_code = 100 
                #rs = f'{t} : {v} being skipped. See ignore_list'
                #resp.text =  rs # unable to set text
                #print ('skip returning :', resp)
                return resp
            log.info ('Processing %s : %s ', t, v)

        # vpn name override
        if self.is_vpnname_set:
            if 'msgVpnName' in json_data:
                json_data['msgVpnName'] = self.vpname
        if self.tier in self.config['max-limits']:
            for k, v in self.config['max-limits'][self.tier].items():
                if k in json_data:
                    json_data[k] = v
                    log.info('Setting %s : %s', k, v)
        if self.release in self.config['drop-tags']:
            for k in self.config['drop-tags'][self.release]:
                if k in json_data:
                    del json_data[k]
                    log.debug('Dropping %s', k)

            #print ('------------ JSON to post ----------------'); pp.pprint(json_data)
            #_,urlp = os.path.split(url)
            #print ('URL ', url, urlp)

        log.debug('Posting to URL: %s', url)
        log.trace('posting json-data:\n%s', json.dumps(json_data, indent=4, sort_keys=True))

        resp = getattr(requests, verb)(url, 
            headers={"content-type": "application/json"},
            auth=(self.cliuser, self.passwd),
            data=(json.dumps(json_data) if json_data != None else None))

        log.debug ('proc returning : <%s> %s', type(resp), resp)
        return resp

    def postLinks(self, base_url, base_obj, base_path,links):
        log = self.log
        log.enter ("%s::%s url = %s obj = %s path = %s", __name__, inspect.stack()[0][3], base_url, base_obj, base_path)
        # debug
        #pp.pprint(links)

        for _, value in links.items():
            log.debug('Posting link: %s', value)
            op,obj = os.path.split(value)
            if obj in self.config['ignore-objects']:
                log.info('Skip object: %s', obj)
                continue
            path="{}/{}".format(base_path, obj)
            json_file = urllib.parse.unquote("{}/{}.json".format(path, obj))
            url = "{}/{}/{}".format(base_url,base_obj,obj)

            json_files = list(pathlib.Path(path).glob(f'{obj}*.json'))
            log.debug('%d %s json_files in %s: %s', len(json_files), obj, path, json_files)


            if len(json_files) == 0 :
                log.debug("No %s JSON files found in %s. Try another level", obj, path)
                _,od = os.path.split(op)
                url = "{}/{}/{}".format(base_url, od, obj)
                path="{}/{}/{}".format(base_path, od, obj)
                json_files = list(pathlib.Path(path).glob(f'{obj}*.json'))
                log.debug('%d %s json_files-1 in %s: %s', len(json_files), obj, path, json_files)

            # log.trace('base_url: %s\nbase_obj: %s\nobj: %s\nurl: %s', base_url, base_obj, obj, url)
            # log.debug('url: %s', url)
            # if not os.path.exists(json_file):
            #     log.debug("JSON file %s not found. Try another level", json_file)
            #     _,od = os.path.split(op)
            #     path="{}/{}/{}".format(base_path, od, obj)
            #     json_file = urllib.parse.unquote("{}/{}.json".format(path, obj))
            #     log.debug('new json_file: %s', json_file)
            #     log.trace('od: %s\npath: %s', od, path)
            #     url = "{}/{}/{}".format(base_url, od, obj)
            #     log.debug('new url: %s', url)

            #log.debug("value: %s\n url: %s\n json_file: %s\n path: %s\n obj: %s", value, url, json_file, path, obj)

            for json_file in json_files:
                log.info('Reading JSON file %s', json_file)
                json_data, links, next_uri = self.ReadDataJSON(json_file)
                if len(json_data) == 0 and len(links) == 0:
                    log.debug("No data or links in %s", json_file)
                    continue
                self.Post(url, base_obj, path, json_data, links, next_uri)
            #else:
            #    log.info("No JSON file %s", json_file)

    def Post(self, url, obj, path, json_data=None, links=None, next_page_uri=None) :
        log = self.log
        log.enter ("%s::%s url = %s obj = %s path = %s", __name__, inspect.stack()[0][3], url, obj, path)

        if type(json_data) is list:
            log.trace('json_data is list')
            for json_data_e in json_data:
                resp = self.postit(url, json_data_e)
                log.trace('list post returned %s', resp.status_code)
                if (not (resp.status_code == 200 or resp.status_code == 100 )):
                    rs, rd = self.response_status(resp)                    
                    if rs in self.config['ignore-status'] :
                        log.info('%s (%s) <ignored>', rd, rs)
                    else :
                        log.error('%s (%s) <exiting>', rd, rs)
                        raise RuntimeError
        else:
            log.trace('json_data is obj')
            resp = self.postit(url, json_data)
            log.trace('obj post returned %s', resp.status_code)
            if (not (resp.status_code == 200 or resp.status_code == 100 )):
                    rs, rd = self.response_status(resp)                    
                    if rs in self.config['ignore-status'] :
                        log.info('%s (%s) <ignored>', rd, rs)
                    else :
                        log.error('%s (%s) <exiting>', rd, rs)
                        raise RuntimeError

        # We are done posting with json_data
        # loop thru link and Post recursively
        if links:
            log.trace("Processing Links %s", links)
            if type(links) is list:
                for link in links:
                    self.postLinks(url, obj,path, link)
            else:
                self.postLinks(url, obj, path, links)

        log.trace('response: <%s> %s', type(resp), resp)
        log.trace('response json: %s', resp.json())
        return resp.json()

    # ProcessLinks:
    # recursively proces links
    # This does bulk of the processing. 
    # For each link, get the JSON content and write to file.
    # and recurse until none left.
    def ProcessLinks(self, json_data):
        #print ('YAS2P::ProcessLinks  ', json_data)
        log = self.log 
        if 'links' not in json_data:
            log.debug ("No Links")
            return
        if type(json_data['links']) is list:
            for link_list in json_data['links']:
                link_keys = list(link_list.keys())
                #print ("   got {:d} link-lists: {:s}". format(len(lkeys), lkeys))
                if 'uri' in link_keys:
                    link_keys.remove('uri') 
                if len(link_keys) == 0 :
                    #print ("No non-uri links")
                    return       
                #print ("   processing {:d} links: {:s}".format(len(lkeys), lkeys))
                for l in link_keys:
                    lurl = link_list[l]
                    link_json_data = self.processLink(lurl, True)
                    self.ProcessLinks(link_json_data)
        else:
            link_keys = list(json_data['links'].keys())
            #print ("   got {:d} links: {:s}". format(len(lkeys), lkeys))
            if 'uri' in link_keys:
                link_keys.remove('uri') 
            if len(link_keys) == 0 :
                #print ("No non-uri links")
                return       
            #print ("   processing {:d} links: {:s}".format(len(lkeys), lkeys))
            for link_key in link_keys:
                link_url = json_data['links'][link_key]
                link_json = self.processLink(link_url, True)
                self.ProcessLinks(link_json)

    # get_unique_fname
    # generate unique name for filename
    # first call is returned as is : eg: "queues"
    # subsequent calls will get a numeric index: "queues-1", "queues-2", etc.
    def get_unique_fname (self,path,obj):
        obj1=urllib.parse.unquote(obj)
        key=path+"/"+obj1
        if key not in objmap:
            objmap[key] = 0
            return "{}.json".format(obj1)
        objmap[key] = objmap[key]+1
        return ("{}-{}.json".format(obj1,objmap[key]))

    # processLink
    def processLink(self, url, collection):
        log = self.log
        log.enter ("%s::%s url = %s", __name__, inspect.stack()[0][3], url)
        #ph,obj = os.path.split(url)
        path=url[url.find('/msgVpns/')+8:]
        if path.rfind('?')>0:
            path=path[:path.rfind('?')]
        _,obj = os.path.split(path)
        #path=urllib.unquote(path) # 2.X syntax
        path=urllib.parse.unquote(path)

        #-- Process link
        log.debug ("Processing link {}".format(url))  
        json_data = self.Get(url, collection)

        # Write data to file

        fname = self.get_unique_fname(path, obj)
        log.debug("Write to Dir: %s Path: %s File: %s", self.outdir, path, fname)
        self.WriteJSON(self.outdir+path, fname, json_data )

        # Process meta - look for cursor/paging
        meta_data = json_data['meta']
        if 'paging' in meta_data:
            log.trace ("paging : %s", meta_data['paging'])
            next_page_uri = meta_data['paging']['nextPageUri']
            log.debug ("Processig Next Page URI : %s", next_page_uri)
            # process nextPageUri - recursively
            self.processLink(next_page_uri, False) # don't use collection for nextPage
            # process the links from nextPageUri returned page. This is deep recursion!
            self.ProcessLinks(json_data) 
            
        return json_data

    # WriteJSON
    def WriteJSON(self, odir, fname, json_data):
        log = self.log
        log.enter ("%s::%s dir: %s file: %s", __name__, inspect.stack()[0][3], odir, fname)

        outfile=odir+"/"+fname
        if os.path.exists(outfile):
            log.info("File %s exists. Not overwriting", outfile)
            print("File exists: "+ outfile)
            return
        path,fname = os.path.split(outfile)
        if not os.path.exists(path):
            log.debug ("makedir: %s",path)
            os.makedirs(path)
        log.info ("Writing to %s",outfile)
        #print("Writing to "+ outfile)
        #pp.pprint(json_data)
        with open(outfile, 'w') as fp:
            json.dump(json_data, fp, indent=4, sort_keys=True)

    def ReadDataJSON (self, json_file) :
        log = self.log
        log.enter ("%s::%s JSON file: %s", __name__, inspect.stack()[0][3], json_file) 
        #json_fname = "{}/{}".format(path, fname)
        with open(json_file, "r") as fp:
            json_payload = json.load(fp)  
        json_data = json_payload['data']

        links = None
        if 'links' in json_payload:
            links = json_payload['links']

        next_page_uri = None
        meta_data = json_payload['meta']
        if 'paging' in meta_data:
            next_page_uri = meta_data['paging']['nextPageUri']
        log.trace ('JSON DATA: %s', json_data)
        log.trace ('LINKS : %s', links)
        log.trace ('NEXT_PAGE_URI: %s', next_page_uri)
        return (json_data, links, next_page_uri)

    def VpnName(self, vpn) :
        log = self.log
        log.enter ("%s::%s vpn name: %s", __name__, inspect.stack()[0][3], vpn) 
        self.is_vpnname_set = True
        self.vpname = vpn

    def ReadConfigJSON (self, cfgfile, release, tier) :
        log = self.log
        log.enter ("%s::%s Config JSON file: %s", __name__, inspect.stack()[0][3], cfgfile) 
        log.info('Reading config file %s', cfgfile)
        self.release = release
        self.tier = tier
        with open(cfgfile, "r") as fp:
            self.config = json.load(fp)  
            log.trace('config json:\n%s', json.dumps(self.config, indent=4, sort_keys=True))
        log.debug('Got release: %s tier: %s', release, tier)
        if self.tier in self.config['max-limits']:
            log.trace('Limits: %s', self.config['max-limits'][self.tier])
        else:
            log.error('Tier %s not in config.max-limits', tier)
            log.info('Valid tiers : %s', self.config['max-limits'].keys())
            raise RuntimeError
        if self.release in self.config['drop-tags']:
            log.trace('Drop tags: %s', self.config['drop-tags'][self.release])
        else:
            log.error('Release %s not in config.drop-tags', release)
            log.info('Valid release : %s', self.config['drop-tags'].keys())
            raise RuntimeError


    def response_status(self, resp):
        rd = 'Problem with POST'
        rs = 'UNKNOWN_ERROR'
        resp_json = json.loads(resp.text)
        if 'meta' in resp_json:
            if 'error' in resp_json['meta']:
                if 'status' in resp_json['meta']['error'] :
                    rs =  resp_json['meta']['error']['status']
                if 'description' in resp_json['meta']['error'] :
                    rd =  resp_json['meta']['error']['description']
        return rs, rd