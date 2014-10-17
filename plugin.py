###
# Copyright (c) 2014, spline
# All rights reserved.
#
#
###
# my libs
import json
import cgi
# supybot libs
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
# extra supybot libs
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


####################
# HELPER FUNCTIONS #
####################

def _r(s):
    return ircutils.mircColor(s, 'red')

def _y(s):
    """Returns a yellow string."""
    return ircutils.mircColor(s, 'yellow')

def _g(s):
    """Returns a green string."""
    return ircutils.mircColor(s, 'green')

def _b(s):
    """Returns a blue string."""
    return ircutils.mircColor(s, 'blue')

def _lb(s):
    """Returns a light blue string."""
    return ircutils.mircColor(s, 'light blue')

def _o(s):
    """Returns an orange string."""
    return ircutils.mircColor(s, 'orange')

def _bold(s):
    """Returns a bold string."""
    return ircutils.bold(s)

def _ul(s):
    """Returns an underline string."""
    return ircutils.underline(s)

def _bu(s):
    """Returns a bold/underline string."""
    return ircutils.bold(ircutils.underline(s))

def flatten_subdicts(dicts, flat=None):
    """Change dict of dicts into a dict of strings/integers. Useful for
    using in string formatting."""
    if flat is None:
        # Instanciate the dictionnary when the function is run and now when it
        # is declared; otherwise the same dictionnary instance will be kept and
        # it will have side effects (memory exhaustion, ...)
        flat = {}
    if isinstance(dicts, list):
        return flatten_subdicts(dict(enumerate(dicts)))
    elif isinstance(dicts, dict):
        for key, value in dicts.items():
            if isinstance(value, dict):
                value = dict(flatten_subdicts(value))
                for subkey, subvalue in value.items():
                    flat['%s__%s' % (key, subkey)] = subvalue
            else:
                flat[key] = value
        return flat
    else:
        return dicts
    
##############
# FORMATTING #
##############

def format_push(d):
    """Format a push for IRC."""
    
    try:
        # [GitPull] reticulatingspline pushed 1 commit to master [+0/-0/1] http://git.io/n4lbSQ
        # [GitPull] spline e2070d1 - Fix initial test as I forgot it might actually update.
        #repoowner = d['repository__owner__name']
        reponame = d['repository__name']
        commit_msg = d['head_commit__message']
        committer = d['commits'][0]['committer']['name']
        numofc = len(d['commits'])
        branch = d['repository__master_branch']
        compare = d['compare']
        m = "[{0}] {2} pushed {3} commit(s) to {4} {5} {6}".format(_b(reponame),\
                                                                   _r(committer),\
                                                                   _bold(numofc),\
                                                                   _o(branch),\
                                                                   commit_msg,\
                                                                   compare)
        return m
    except Exception as e:
        log.info("_format_push :: ERROR :: {0}".format(e))
        return None

def format_status(d):
    """Format."""
    try:
        # [Assorted] Travis CI - build #73 passed. (master @ 3c4572b) http://git.io/OhYANw
        # [Assorted] Details: https://travis-ci.org/reticulatingspline/Assorted/builds/38050581
        reponame = d['repository__name']
        desc = d['description']  # "state": "pending"
        target_url = d['target_url']
        m = "[{0}] {1} - {2}".format(_b(reponame), _bold(desc), target_url)
        return m
    except Exception as e:
        log.info("format_status :: ERROR :: {0}".format(e))
        return None

class WebHooksServiceCallback(httpserver.SupyHTTPServerCallback):
    name = "WebHooksService"
    defaultResponse = """This plugin handles only POST request, please don't use other requests."""

    def doPost(self, handler, path, form):
        if not handler.address_string().endswith('.rs.github.com') and \
                not handler.address_string().endswith('.cloud-ips.com') and \
                not handler.address_string() == 'localhost' and \
                not handler.address_string().startswith('127.0.0.') and \
                not handler.address_string().startswith('192.30.252.') and \
                not handler.address_string().startswith('204.232.175.'):
            log.warning("""'%s' tried to act as a web hook for Github,
            but is not GitHub.""" % handler.address_string())
            self.send_response(403)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b('Error: you are not a GitHub server.'))
        else:  # send OK back.
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
            d = flatten_subdicts(payload)  # flatten it out.
            log.info("doPost: {0}".format(d))  # log.
            # lets figure out how to handle each type of notification here.
            if headers['x-github-event'] == 'push':  # push event.
                s = format_push(d)
                if s:  # send if we get it back.
                    self.plugin._announce_webhook(s)
            elif headers['x-github-event'] == 'status':
                s = format_status(d)
                if s:  # send if we get it back.
                    self.plugin._announce_webhook(s)

class WebHooks(callbacks.Plugin):
    """Add the help for "@plugin help WebHooks" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(WebHooks, self)
        self.__parent.__init__(irc)
        callback = WebHooksServiceCallback()
        callback.plugin = self
        httpserver.hook('webhooks', callback)

    def die(self):
        self.__parent.die()
        httpserver.unhook('webhooks')

    def _announce_webhook(self, m):
        for (server, channel) in (('efnet', '#supybot'),):
            m = "{0}".format(m)
            world.getIrc(server).sendMsg(ircmsgs.privmsg(channel, m))

Class = WebHooks


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
