###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

__all__ = ['CherryPyStartup']

import os, sys, glob, time
import cherrypy

from pyasm.web.app_server import AppServer

from pyasm.common import Environment, Container, Config
from pyasm.web import WebEnvironment
from pyasm.biz import Project

#from cherrypy_startup import TacticIndex, _cp_on_http_error
from cherrypy_startup import CherryPyStartup as CherryPyStartup20



class Root:
    '''Dummy Root page'''

    def test(self):
        return "OK"
    test.exposed = True

    def index(self):
        return '''<META http-equiv="refresh" content="0;URL=/tactic">'''
    index.exposed = True



class TacticIndex:
    '''Dummy Index file'''
    def index(self):
        # check if this project exists
        response = cherrypy.response
        request = cherrypy.request
        path = request.path_info

        from pyasm.security import Site
        default_project = Site.get().get_default_project()
        if not default_project:
            path = "/"
        else:
            path = path.rstrip("/")
            path = "%s/%s" % (path, default_project)

        return '''<META http-equiv="refresh" content="0;URL=%s">''' % path
    index.exposed = True




class CherryPyStartup(CherryPyStartup20):


    def execute(self):
        #import pprint
        #pprint.pprint( self.config )

        #try:
        #    import setproctitle
        #    setproctitle.setproctitle("TACTIC")
        #except:
        #    pass


        cherrypy.config.update( self.config )

        cherrypy.config.update({'error_page.404': self.error_page})
        cherrypy.config.update({'error_page.403': self.error_page})

        cherrypy.engine.start()
        cherrypy.engine.block()




    def error_page(self, status, message, traceback, version):

        # check if this project exists
        response = cherrypy.response
        request = cherrypy.request
        path = request.path_info

        parts = path.split("/")
        if len(parts) < 3:
            cherrypy.response.body = '<meta http-equiv="refresh" content="0;url=/tactic" />'
            return

        from pyasm.security import Site
        site_obj = Site.get()
        path_info = site_obj.break_up_request_path(path)

        if path_info:
            site = path_info['site']
            project_code = path_info['project_code']
        else:
            project_code = parts[2]
            site = ""


        # sites is already mapped in config for cherrypy
        if site == "plugins":
            return


        has_site = False
        try:
            from pyasm.security import TacticInit
            TacticInit()

            Site.set_site(site)
            if site:
                eval("cherrypy.root.tactic.%s.%s" % (site, project_code))
            else:
                eval("cherrypy.root.tactic.%s" % project_code)
        # if project_code is empty , it raises SyntaxError
        except (AttributeError, SyntaxError), e:
            print("WARNING: ", e)
            has_project = False
            has_site = True
        except Exception as e:
            print("WARNING: ", e)
            has_project = False
        else:
            has_project = True
            has_site = True


        # only set this if there a site ... needed for UploadServerWdg
        if has_site and project_code in ['default']:
            startup = cherrypy.startup
            config = startup.config
            startup.register_project(project_code, config, site=site)

            if path.endswith("/UploadServer/"):
                from pyasm.widget import UploadServerWdg
                try:
                    from pyasm.web import WebContainer
                    from cherrypy30_adapter import CherryPyAdapter

                    # clear the buffer
                    WebContainer.clear_buffer()
                    adapter = CherryPyAdapter()
                    WebContainer.set_web(adapter)

                    widget = UploadServerWdg().get_display()
                except Exception as e:
                    print("ERROR: ", e)
                    widget = e

            else:
                widget = "ERROR 404"


            return widget




        print("WARNING:")
        print("    status: ", status)
        print("    message: ", message)
        print("    site: ", site)
        print("    project_code: ", project_code)




        # if the url does not exist, but the project does, then check to
        # to see if cherrypy knows about it
        project = None
        if has_site:
            try:
                project = Project.get_by_code(project_code)
            except Exception as e:
                print("WARNING: ", e)
                raise


        if not has_project and project and project.get_value("type") != 'resource':

            # register the project
            startup = cherrypy.startup
            config = startup.config
            startup.register_project(project_code, config, site=site)

            # This is an issue ... if the project is not registered, then on a web
            # page, it is simple just to refresh, but on requests like REST, this is not
            # so feasible ... need a way to return the request after registering the
            # project

            # For REST requests, we will send the request again after registering the project.
            # NOTE: cherrypy.request.path_info only gives us the URL without the query string.
            # So path.endswith('/REST') will work both for GET and POST.
            if path.endswith('/REST'):
                import requests
                base_url = 'http://localhost'

                # For CherryPy, the port could be other than 80
                if startup.port:
                    base_url += ':' + str(startup.port)

                # Add the path (e.g. /tactic/xxxx/yyyy/REST) to the base_url.
                url = base_url + str(path)
                print("Sending the request again to URL:" + str(url))
                if request.method == 'POST':
                    r = requests.post(url, data = request.body.params)
                    return r.text
                elif request.method == 'GET':
                    # The query string is in cherrypy.request.params. So we are
                    # sending it as a POST request here without reconstructing the query string
                    # and sending it as GET.
                    r = requests.post(url, data = request.params)
                    return r.text

            """
            # if there is hash, then attempt to get it
            hash = "/rest"
            if hash:
                # clear the buffer
                from pyasm.web import WebContainer
                WebContainer.clear_buffer()
                html = ""
                try:
                    from tactic.ui.panel import HashPanelWdg
                    widget = HashPanelWdg.get_widget_from_hash(hash)
                    if widget:
                        html = widget.get_buffer_display()
                except Exception as e:
                    return "ERROR: %s" % str(e)

                if html:
                    return html
            """


            # either refresh ... (LATER: or recreate the page on the server end)
            # reloading in 3 seconds
            html_response = []
            html_response.append('''<html>''')
            html_response.append('''<body style='color: #000; min-height: 1200px; background: #DDDDDD'><div>Reloading ...</div>''')
            html_response.append('''<script>document.location = "%s";</script>''' % path )
            html_response.append('''</body>''')
            html_response.append('''</html>''')
            html_response = "\n".join(html_response)

            # this response.body is not needed, can be commented out in the future
            response.body = ''
            return html_response



        # return 404 error
        try:

            from pyasm.web import WebContainer, DivWdg
            from pyasm.widget import Error404Wdg
            from cherrypy30_adapter import CherryPyAdapter

            # clear the buffer
            WebContainer.clear_buffer()
            adapter = CherryPyAdapter()
            WebContainer.set_web(adapter)

            top = DivWdg()
            top.add_color("background", "background", -5)
            top.add_color("color", "color")
            #top.add_style("background", "#444")
            top.add_style("height: 300")
            top.add_style("width: 500")
            top.add_style("margin: 150px auto")
            top.add_border()
            #top.add_style("border: solid 1px black")
            #top.add_style("border-radius: 15px")
            #top.add_style("box-shadow: 0px 0px 15px rgba(0,0,0,0.5)")


            widget = Error404Wdg()
            widget.status = status
            widget.message = message


            top.add(widget)

            return top.get_buffer_display()
        except Exception as e:
            print("ERROR: ", e)
            return "ERROR: ", e





    def setup_sites(self):

        context_path = "%s/src/context" % self.install_dir
        doc_dir = "%s/doc" % self.install_dir
        plugin_dir = Environment.get_plugin_dir()
        builtin_plugin_dir = Environment.get_builtin_plugin_dir()
        dist_dir = Environment.get_dist_dir()

        log_dir = "%s/log" % Environment.get_tmp_dir()



        def CORS():
            #cherrypy.response.headers["Access-Control-Allow-Origin"] = "http://192.168.0.15:8100"
            cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
            cherrypy.response.headers["Access-Control-Allow-Headers"] = "Origin, X-Requested-With, Content-Type, Accept"
        cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)


        config = {

            'global': {
                'server.socket_host': '127.0.0.1',
                'server.socket_port': 80,
                'log.screen': False,
                'request.show_tracebacks': True,
                'tools.log_headers.on': True,
                'server.log_file': "%s/tactic_log" % log_dir,
                'server.max_request_body_size': 0,
                #'server.socket_timeout': 60,
                'response.timeout': 3600,

                'tools.encode.on': True,
                'tools.encode.encoding': 'utf-8',
                'tools.decode.on': True,
                'tools.decode.encoding': 'utf-8',
                #'encoding_filter.on': True,
                #'decoding_filter.on': True
                'tools.CORS.on': True

                },
            '/context': {'tools.staticdir.on': True,
                         'tools.staticdir.dir': context_path,
                         # Need to do this because on windows servers, jar files
                         # are served as text/html
                         'tools.staticdir.content_types': {
                             'jar': 'application/java-archive'
                         }
                        },
            '/assets':  {'tools.staticdir.on': True,
                         'tools.staticdir.dir': Environment.get_asset_dir()
                        },
            '/doc':     {'tools.staticdir.on': True,
                         'tools.staticdir.dir': doc_dir,
                         'tools.staticdir.index': "index.html"
                        },
            # NOTE: expose the entire plugins directory
            '/tactic/plugins': {
                         'tools.staticdir.on': True,
                         'tools.staticdir.dir': plugin_dir,
                        },
            '/tactic/builtin_plugins': {
                         'tools.staticdir.on': True,
                         'tools.staticdir.dir': builtin_plugin_dir,
                        },
            '/tactic/dist': {
                        'tools.staticdir.on': True,
                        'tools.staticdir.dir': dist_dir,
                        },
             '/plugins': {
                         'tools.staticdir.on': True,
                         'tools.staticdir.dir': plugin_dir,
                        },
            '/builtin_plugins': {
                         'tools.staticdir.on': True,
                         'tools.staticdir.dir': builtin_plugin_dir,
                        },
            '/dist': {
                        'tools.staticdir.on': True,
                        'tools.staticdir.dir': dist_dir,
                        },




        }


        # set up the root directory
        cherrypy.root = Root()
        cherrypy.tree.mount( cherrypy.root, config=config)



        from pyasm.search import Search
        search = Search("sthpw/project")
        search.add_filter("type", "resource", op="!=")
        projects = search.get_sobjects()


        # find out if one of the projects is the root
        root_initialized = False

        if not root_initialized:
            project_code = Project.get_default_project()
            if not project_code:
                project_code = Config.get_value('install','default_project')
            if project_code and project_code !='default':
                from tactic.ui.app import SitePage
                cherrypy.root.tactic = SitePage(project_code)
                cherrypy.root.projects = SitePage(project_code)
                root_initialized = True


        if not root_initialized:
            # load in the base site at root
            from tactic_sites.default.context.Index import Index
            cherrypy.root.tactic = Index()
            cherrypy.root.projects = Index()

        for project in projects:
            project_code = project.get_code()
            self.register_project(project_code, config)
        self.register_project("default", config)


        from pyasm.security import Site
        site_obj = Site.get()
        site_obj.register_sites(self, config)


        #self.register_project("vfx", config, site="vfx_demo")
        #self.register_project("default", config, site="vfx_demo")
        return config





    def register_project(self, project, config, site=None):

        # if there happend to be . in the project name, convert to _
        project = project.replace(".", "_")

        if project == "template":
            return

        if site:
            print("Registering project ... %s (%s)" % (project, site))
        else:
            print("Registering project ... %s" % project)


        try:
            from tactic.ui.app import SitePage
            if site:
                # make sure the site exists
                try:
                    x = eval("cherrypy.root.tactic.%s" % (site))
                except:
                    exec("cherrypy.root.tactic.%s = TacticIndex()" % (site))
                    exec("cherrypy.root.projects.%s = TacticIndex()" % (site))

                exec("cherrypy.root.tactic.%s.%s = SitePage()" % (site, project))
                exec("cherrypy.root.projects.%s.%s = SitePage()" % (site, project))

            else:
                exec("cherrypy.root.tactic.%s = SitePage()" % project)
                exec("cherrypy.root.projects.%s = SitePage()" % project)



        except ImportError:
            #print("... WARNING: SitePage not found")
            exec("cherrypy.root.tactic.%s = TacticIndex()" % project)
            exec("cherrypy.root.projects.%s = TacticIndex()" % project)
        except SyntaxError, e:
            print(e.__str__())
            print("WARNING: skipping project [%s]" % project)





        # The rest is only ever executed on the "default" project


        # This is to get admin project working
        if project in ['admin', 'default', 'template', 'unittest']:
            base = "tactic_sites"
        else:
            base = "sites"



        # get the contexts:
        if project in ("admin", "default", "template", "unittest"):
            context_dir = Environment.get_install_dir().replace("\\", "/")
            context_dir = "%s/src/tactic_sites/%s/context" % (context_dir, project)
        else:
            context_dir = Environment.get_site_dir().replace("\\", "/")
            context_dir = "%s/sites/%s/context" % (context_dir, project)



        if not os.path.exists(context_dir):
            return

        contexts = []
        for context_dir in os.listdir(context_dir):
            if not context_dir.endswith(".py"):
                continue
            if context_dir == "__init__.py":
                continue
            if context_dir.startswith("."):
                continue
            if os.path.isdir(context_dir):
                continue

            context = context_dir.replace(".py", "")
            contexts.append(context)

        for context in contexts:
            try:

                exec("from %s.%s.context.%s import %s" % (base,project,context,context))
                if site:
                    exec("cherrypy.root.tactic.%s.%s.%s = %s()" % (site,project,context,context) )
                else:
                    exec("cherrypy.root.tactic.%s.%s = %s()" % (project,context,context) )

            except ImportError, e:
                print(str(e))
                print("... failed to import '%s.%s.%s'" % (base, project, context))
                raise
                #return


            path = "/tactic/%s/%s" % (project, context)
            settings = {}
            config[path] = settings

            if context in ["XMLRPC", "Api"]:
                #settings['request.dispatch'] = cherrypy.dispatch.XMLRPCDispatcher(),
                settings['tools.xmlrpc.on'] = True
                settings['tools.xmlrpc.encoding'] = 'utf-8'
                settings['tools.xmlrpc.allow_none'] = True




