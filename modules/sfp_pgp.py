# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         sfp_pgp
# Purpose:      SpiderFoot plug-in for looking up received e-mails in PGP
#               key servers as well as finding e-mail addresses belonging to
#               your target.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     17/02/2015
# Copyright:   (c) Steve Micallef 2015
# Licence:     GPL
# -------------------------------------------------------------------------------

try:
    import re2 as re
except ImportError as e:
    import re

from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent


class sfp_pgp(SpiderFootPlugin):
    """PGP Key Look-up:Footprint,Investigate,Passive:Public Registries::Look up e-mail addresses in PGP public key servers."""

    results = None

    # Default options
    opts = {
        # options specific to this module
        'keyserver_search1': "https://pgp.key-server.io/pks/lookup?fingerprint=on&op=vindex&search=",
        'keyserver_fetch1': "https://pgp.key-server.io/pks/lookup?op=get&search=",
        'keyserver_search2': "http://the.earth.li:11371/pks/lookup?op=index&search=",
        'keyserver_fetch2': "http://the.earth.li:11371/pks/lookup?op=get&search="
    }

    # Option descriptions
    optdescs = {
        'keyserver_search1': "PGP public key server URL to find e-mail addresses on a domain. Domain will get appended.",
        'keyserver_fetch1': "PGP public key server URL to find the public key for an e-mail address. Email address will get appended.",
        'keyserver_search2': "Backup PGP public key server URL to find e-mail addresses on a domain. Domain will get appended.",
        'keyserver_fetch2': "Backup PGP public key server URL to find the public key for an e-mail address. Email address will get appended."
    }

    def setup(self, sfc, userOpts=dict()):
        self.sf = sfc
        self.__dataSource__ = "PGP Key Servers"
        self.results = self.tempStorage()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ['INTERNET_NAME', "EMAILADDR", "DOMAIN_NAME"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return ["EMAILADDR", "AFFILIATE_EMAILADDR", "PGP_KEY"]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        if eventData in self.results:
            return None
        else:
            self.results[eventData] = True

        self.sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # Get e-mail addresses on this domain
        if eventName == "DOMAIN_NAME":
            res = self.sf.fetchUrl(self.opts['keyserver_search1'] + eventData,
                                   timeout=self.opts['_fetchtimeout'],
                                   useragent=self.opts['_useragent'])

            if res['content'] is None:
                res = self.sf.fetchUrl(self.opts['keyserver_search2'] + eventData,
                                       timeout=self.opts['_fetchtimeout'],
                                       useragent=self.opts['_useragent'])

            if res['content'] is not None:
                emails = self.sf.parseEmails(res['content'])
                for email in emails:
                    evttype = "EMAILADDR"

                    mailDom = email.lower().split('@')[1]
                    if not self.getTarget().matches(mailDom, includeChildren=True, includeParents=True):
                        evttype = "AFFILIATE_EMAILADDR"

                    self.sf.info("Found e-mail address: " + email)
                    evt = SpiderFootEvent(evttype, email, self.__name__, event)
                    self.notifyListeners(evt)

        if eventName == "EMAILADDR":
            res = self.sf.fetchUrl(self.opts['keyserver_fetch1'] + eventData,
                                   timeout=self.opts['_fetchtimeout'],
                                   useragent=self.opts['_useragent'])

            if res['content'] is None:
               res = self.sf.fetchUrl(self.opts['keyserver_fetch2'] + eventData,
                                      timeout=self.opts['_fetchtimeout'],
                                      useragent=self.opts['_useragent'])

            if res['content'] is not None:
                pat = re.compile("(-----BEGIN.*END.*BLOCK-----)", re.MULTILINE | re.DOTALL)
                matches = re.findall(pat, res['content'])
                for match in matches:
                    self.sf.debug("Found public key: " + match)
                    if len(match) < 300:
                        self.sf.debug("Likely invalid public key.")
                        continue

                    evt = SpiderFootEvent("PGP_KEY", match, self.__name__, event)
                    self.notifyListeners(evt)

        return None

# End of sfp_pgp class
