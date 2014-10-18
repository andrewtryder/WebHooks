###
# Copyright (c) 2014, spline
# All rights reserved.
#
#
###
# my libs
import json
import cPickle as pickle
from collections import defaultdict
import base64
import ipaddr
# supybot libs
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
# extra supybot libs
import supybot.conf as conf
import supybot.ircmsgs as ircmsgs
import supybot.world as world
import supybot.log as log
import supybot.httpserver as httpserver
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('WebHooks')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x


########################
# FORMATTING FUNCTIONS #
########################

class Formatting(object):
    """Class for formatting."""
    
    def __init__(self):
        self.log = log.getPluginLogger('WebHooks')
    
    def _r(self, s):
        return ircutils.mircColor(s, 'red')
    
    def _y(self, s):
        """Returns a yellow string."""
        return ircutils.mircColor(s, 'yellow')
    
    def _g(self, s):
        """Returns a green string."""
        return ircutils.mircColor(s, 'green')
    
    def _b(self, s):
        """Returns a blue string."""
        return ircutils.mircColor(s, 'blue')
    
    def _lb(self, s):
        """Returns a light blue string."""
        return ircutils.mircColor(s, 'light blue')
    
    def _o(self, s):
        """Returns an orange string."""
        return ircutils.mircColor(s, 'orange')
    
    def _bold(self, s):
        """Returns a bold string."""
        return ircutils.bold(s)
    
    def _ul(self, s):
        """Returns an underline string."""
        return ircutils.underline(s)
    
    def _bu(self, s):
        """Returns a bold/underline string."""
        return ircutils.bold(ircutils.underline(s))

    def flatten_subdicts(self, dicts, flat=None):
        """Change dict of dicts into a dict of strings/integers. Useful for
        using in string formatting."""
        if flat is None:
            # Instanciate the dictionnary when the function is run and now when it
            # is declared; otherwise the same dictionnary instance will be kept and
            # it will have side effects (memory exhaustion, ...)
            flat = {}
        if isinstance(dicts, list):
            return self.flatten_subdicts(dict(enumerate(dicts)))
        elif isinstance(dicts, dict):
            for key, value in dicts.items():
                if isinstance(value, dict):
                    value = dict(self.flatten_subdicts(value))
                    for subkey, subvalue in value.items():
                        flat['%s__%s' % (key, subkey)] = subvalue
                else:
                    flat[key] = value
            return flat
        else:
            return dicts

    def format_push(self, d):
        """Format a GitHub push for IRC."""
        
        try:
            # [GitPull] reticulatingspline pushed 1 commit to master [+0/-0/1] http://git.io/n4lbSQ
            # [GitPull] spline e2070d1 - Fix initial test as I forgot it might actually update.
            #repoowner = d['repository__owner__name']
            reponame = d['repository__name']
            commit_msg = d['head_commit__message']
            committer = self._r(d['commits'][0]['committer']['name'])
            numofc = self._bold(len(d['commits']))
            branch = self._o(d['repository__master_branch'])
            compare = d['compare']
            m = "[{0}] {1} pushed {2} commit(s) to {3} {4} {5}".format(self._b(reponame),\
                                                                       committer,\
                                                                       numofc,\
                                                                       branch,\
                                                                       commit_msg,\
                                                                       compare)
            return (reponame, m)
        except Exception as e:
            self.log.info("_format_push :: ERROR :: {0}".format(e))
            return None

    def format_status(self, d):
        """Format GitHub status messages like from Travis-CI."""
        
        try:
            # [Assorted] Travis CI - build #73 passed. (master @ 3c4572b) http://git.io/OhYANw
            # [Assorted] Details: https://travis-ci.org/reticulatingspline/Assorted/builds/38050581
            reponame = d['repository__name']
            branch = d['branches'][0]['name']  # branch.
            sha = d['branches'][0]['commit']['sha'][0:7]  # first 7 of the sha.
            desc = self._bold(d['description'])  # "state": "pending"
            target_url = d['target_url']
            m = "[{0}] {1} - ({2}@{3}) {4}".format(self._b(reponame), desc, branch, sha, target_url)
            return (reponame, m)
        except Exception as e:
            self.log.info("format_status :: ERROR :: {0} :: {1}".format(e, d))
            return None
    
    def format_bitbucket_push(self, d):
        """Format Bitbucket push messages."""
        # https://confluence.atlassian.com/display/BITBUCKET/POST+hook+management

        try:
            reponame = d['repository__slug']
            commit_msg = d['commits'][0]['message'].strip()
            committer = d['commits'][0]['author']
            #numofc = self._bold(len(d['commits']))
            #branch = self._o(d['commits'][0]['branch'])
            m = "[{0}] {1} pushed {2} commit(s)".format(reponame, committer, commit_msg)
            return (reponame, m)
        except Exception as e:
            self.log.info("_format_bitbucket_push :: ERROR :: {0} :: {1}".format(e, d))
            return None

class WebHooksServiceCallback(httpserver.SupyHTTPServerCallback):
    """
    https://developer.github.com/webhooks/
    """

    name = "WebHooksService"
    defaultResponse = """This plugin handles only POST request, please don't use other requests."""
    
    def __init__(self):
        self.log = log.getPluginLogger('WebHooks')
        self.callbacks = callbacks
        
    def doPost(self, handler, path, form):
        # before we do anything, make sure its authenticated.
        # have to handle different hooks here.
        self.log.info("HEADERS: {0}".format(dict(self.headers)))
        self.log.info("PATH: {0}".format(path))
        self.log.info("FORM: {0}".format(form))
        ip = handler.address_string()  # source ip.
        headers = dict(self.headers)
        # make sure auth header is present.
        if 'authorization' not in headers:
            self.log.warning("""'%s' tried to act as a web hook""" % ip)
            self.send_response(403)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('ERROR')
        else:  # we have auth, lets go.
            ah = headers['authorization']
            # grab user and password from config.
            user = self.callbacks.registryValue('username')
            pw = self.callbacks.registryValue('password')
            # make our string to compare against.
            base64string = base64.encodestring('%s:%s' % (user, pw))[:-1]
            authstring = "Basic {0}".format(base64string)
            # now lets compare.
            if ah != authstring:  # different string. bail.
                self.log.warning("ERROR: {0} sent a bad auth string: {1}".format(ip, ah))
                return
        # if we're here, it was auth'd. lets work with different hooks.
        if ip.endswith('.bitbucket.org'):  # bitbucket.
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("OK")
            # payload
            json_payload = form.getvalue('payload')  # take from the form.
            payload = json.loads(json_payload)  # json -> dict.
            d = Formatting().flatten_subdicts(payload)  # flatten it out.
            s = Formatting().format_bitbucket_push(d)
            if s:
                self.plugin.announce_webhook(s[0], s[1])
        elif ipaddr.IPv4Address(ip) in ipaddr.IPv4Network('192.30.252.0/22'): # github
        # in the future, this needs to check for ipv6 (2620:112:3000::/44)
        # 86e6927206b44a699afc73d3bcb68b3b3dfd6cb1
        # https://help.github.com/articles/what-ip-addresses-does-github-use-that-i-should-whitelist/
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("OK")
            headers = dict(self.headers)
            # sanity/security check.
            if 'user-agent' not in headers and 'x-github-event' not in headers:
                log.info("ERROR: user-agent or x-github-event not in headers :: {0}".format(headers))
                return
            # only handle two types of events.
            if headers['x-github-event'] not in ('push', 'status'):
                log.info("ERROR: x-github-event not push or status :: {0}".format(headers))
                return
            # good payload so lets process it.
            json_payload = form.getvalue('payload')  # take from the form.
            payload = json.loads(json_payload)  # json -> dict.
            d = Formatting().flatten_subdicts(payload)  # flatten it out.
            #self._log.info("doPost: {0}".format(d))  # log the message.
            #self.log.info("doPost: {0}".format(d))  # log the message.
            # lets figure out how to handle each type of notification here.
            # https://developer.github.com/webhooks/
            if headers['x-github-event'] == 'push':  # push event.
                s = Formatting().format_push(d)
                if s:  # send if we get it back.
                    self.log.info("Should be sending push.")
                    self.plugin.announce_webhook(s[0], s[1])
            elif headers['x-github-event'] == 'status':
                s = Formatting().format_status(d)
                if s:  # send if we get it back.
                    self.log.info("Should be sending status.")
                    self.plugin.announce_webhook(s[0], s[1])
        else:
            self.log.warning("""'%s' tried to act as a web hook""" % ip)
            self.send_response(403)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('ERROR')


class WebHooks(callbacks.Plugin):
    """Add the help for "@plugin help WebHooks" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(WebHooks, self)
        self.__parent.__init__(irc)
        # webhook.
        callback = WebHooksServiceCallback()
        callback.plugin = self
        httpserver.hook('webhooks', callback)
        # db.
        self._webhooks = defaultdict(set)
        self._loadpickle() # load saved data.

    def die(self):
        httpserver.unhook('webhooks')
        self.__parent.die()

    #####################
    # INTERNAL DATABASE #
    #####################

    def _loadpickle(self):
        """Load channel data from pickle."""

        try:
            datafile = open(conf.supybot.directories.data.dirize(self.name()+".pickle"), 'rb')
            try:
                dataset = pickle.load(datafile)
            finally:
                datafile.close()
        except IOError:
            return False
        # restore.
        self._webhooks = dataset["webhooks"]
        return True

    def _savepickle(self):
        """Save channel data to pickle."""

        data = {"webhooks": self._webhooks}
        try:
            datafile = open(conf.supybot.directories.data.dirize(self.name()+".pickle"), 'wb')
            try:
                pickle.dump(data, datafile)
            finally:
                datafile.close()
        except IOError:
            return False
        return True

    #######################
    # WEB HOOK ANNOUNCING #
    #######################

    def announce_webhook(self, repo, message):
        """Internal function to announce webhooks."""
        
        #self.log.info("Trying to announce: {0} {1}".format(repo, message))
        # lower it first.
        repo = repo.lower()
        # only work if present
        if repo in self._webhooks:  # if represent present.
            #self.log.info("{0} is in webhooks".format(repo))
            for c in self._webhooks[repo]:  # for each chan in it.
                #self.log.info("{0} is in {1}".format(c, self._webhooks[repo]))
                for irc in world.ircs:  # all networks.
                    if c in irc.state.channels:  # if channel matches.
                        #self.log.info("{0} matched".format(c))
                        irc.queueMsg(ircmsgs.privmsg(c, message))  # post.

    ############################
    # PUBLIC DATABASE COMMANDS #
    ############################
    
    def addwebhook(self, irc, msg, args, optrepo, optchannel):
        """<repository name> [#channel]
        
        Add announcing of repository webhooks to channel.
        """
        
        # first check for channel.
        chan = msg.args[0]
        if not irc.isChannel(ircutils.toLower(chan)):  # we're NOT run in a channel.
            if not optchannel:
                irc.reply("ERROR: You must specify a channel or run from a channel in order to add.")
                return
            else:  # set chan as what the user wants.
                chan = optchannel
        # lower both
        chan = chan.lower()
        optrepo = optrepo.lower()
        # now lets try and add the repo. sanity check if present first.
        if optrepo in self._webhooks:  # channel already in the webhooks.
            if chan in self._webhooks[optrepo]:  # channel already there.
                irc.reply("ERROR: {0} is already being announced on {1}".format(optrepo, chan))
                return
        # last check is to see if we're on the channel.
        if chan not in irc.state.channels:
            irc.reply("ERROR: I must be present on a channel ({0}) you're trying to add.".format(chan))
            return
        # otherwise, we're good. lets use the _addHook.
        try:
            self._webhooks[optrepo].add(chan)
            self._savepickle() # save.
            irc.replySuccess()
        except Exception as e:
            irc.reply("ERROR: I could not add {0} to {1} :: {2}".format(optrepo, chan, e))
    
    addwebhook = wrap(addwebhook, [('checkCapability', 'owner'), ('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])

    def listwebhooks(self, irc, msg, args):
        """
        List active webhooks.
        """
    
        w = len(self._webhooks)
        if w == 0:
            irc.reply("ERROR: I have no webhooks listed. Use addwebhook to add some.")
            return
        # we have them so lets print.
        irc.reply("+--------------------------+------------------------------------------------------+")
        irc.reply("| REPOSITORY NAME          | CHANNELS                                             |")
        irc.reply("+--------------------------+------------------------------------------------------+")
        for (k, v) in self._webhooks.items():
            irc.reply("| {0:<24} | {1:<52} |".format(k, " | ".join([i for i in v])))
        irc.reply("+--------------------------+------------------------------------------------------+")
    
    listwebhooks = wrap(listwebhooks, [('checkCapability', 'owner')])

    def delwebhook(self, irc, msg, args, optrepo, optchannel):
        """<repo> <channel>
        
        Delete announcement of repository from channel.
        """
        
        # first check for channel.
        chan = msg.args[0]
        if not irc.isChannel(ircutils.toLower(chan)):  # we're NOT run in a channel.
            if not optchannel:
                irc.reply("ERROR: You must specify a channel or run from a channel in order to add.")
                return
            else:  # set chan as what the user wants.
                chan = optchannel
        # lower both
        chan = chan.lower()
        optrepo = optrepo.lower()
        # make sure repo is valid.
        if optrepo not in self._webhooks:  # channel already in the webhooks.
            irc.reply("ERROR: {0} repository is invalid. Valid choices: {0}".format(self._webhooks.keys()))
            return
        # if repo is valid, make sure channel is in there.
        if chan not in self._webhooks[optrepo]:  # channel already there.
            irc.reply("ERROR: {0} is an invalid channel for repository: {1}. Repos being announced: {2}".format(chan, optrepo, self._webhooks[optrepo]))
            return
        # we're here if all is good. lets try to delete.
        try:
            self._webhooks[optrepo].remove(chan)  # delete.
            # now lets check if the channel is empty and remove if it is.
            if len(self._webhooks[optrepo]) == 0:
                del self._webhooks[optrepo]
            irc.replySuccess()
        except Exception as e:
            irc.reply("ERROR: I could not delete channel {0} for {1} :: {2}".format(chan, optrepo, e))
            
    delwebhook = wrap(delwebhook, [('checkCapability', 'owner'), ('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])

Class = WebHooks


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
