#!/usr/bin/env python
#mintUpdateCLI.py (c) 2015 Jan Andrejkovic, based on mintUpdate 4.8.1 (c) Clement Lefebvre & Chris Hodapp, License: GNU GPL v3

try:
    import os
    import commands
    import codecs
    import sys
    import string
    #import gtk
    #import gtk.glade
    #import gobject
    import tempfile
    #import threading
    #import time
    import gettext
    import fnmatch
    #import urllib2
    import re
    from user import home
    from sets import Set
    #import proxygsettings
    #sys.path.append('/usr/lib/linuxmint/common')
    from configobj import ConfigObj

    #TOFU:
    import argparse
    #from collections import OrderedDict

    #TOFU: debug - disable:
    from pprint import pprint

except Exception, detail:
    print detail
    #pass

"""
try:
    import pygtk
    pygtk.require("2.0")
except Exception, detail:
    print detail
    pass
"""

from subprocess import Popen, PIPE, STDOUT

"""
#TODO: Check this:
try:
    numMintUpdate = commands.getoutput("ps -A | grep mintUpdate | wc -l")
    if (numMintUpdate != "0"):
        os.system("killall mintUpdate")
except Exception, detail:
    print detail

"""

"""
architecture = commands.getoutput("uname -a")
if (architecture.find("x86_64") >= 0):
    import ctypes
    libc = ctypes.CDLL('libc.so.6')
    libc.prctl(15, 'mintUpdate', 0, 0, 0)
else:
    import dl
    if os.path.exists('/lib/libc.so.6'):
        libc = dl.open('/lib/libc.so.6')
        libc.call('prctl', 15, 'mintUpdate', 0, 0, 0)
    elif os.path.exists('/lib/i386-linux-gnu/libc.so.6'):
        libc = dl.open('/lib/i386-linux-gnu/libc.so.6')
        libc.call('prctl', 15, 'mintUpdate', 0, 0, 0)

"""

# i18n
gettext.install("mintupdate", "/usr/share/linuxmint/locale")

CONFIG_DIR = "%s/.config/linuxmint" % home

package_short_descriptions = {}
package_descriptions = {}

(UPDATE_CHECKED, UPDATE_NAME, UPDATE_LEVEL_PIX, UPDATE_OLD_VERSION, UPDATE_NEW_VERSION, UPDATE_LEVEL_STR, UPDATE_SIZE, UPDATE_SIZE_STR, UPDATE_TYPE_PIX, UPDATE_TYPE, UPDATE_TOOLTIP, UPDATE_SORT_STR, UPDATE_OBJ) = range(13)

#TOFU:
#http://stackoverflow.com/questions/903130/hasattr-vs-try-except-block-to-deal-with-non-existent-attributes/16186050#16186050
def hasATTR(obj, attr):
    return getattr(obj, attr, None) is not None

def getATTR(obj, attr):
    return getattr(obj, attr, None)


class PackageUpdate():
    def __init__(self, source_package_name, level, oldVersion, newVersion, extraInfo, warning, update_type, tooltip):
        self.name = source_package_name
        self.description = ""
        self.short_description = ""
        self.level = level
        self.oldVersion = oldVersion
        self.newVersion = newVersion
        self.size = 0
        self.extraInfo = extraInfo
        self.warning = warning
        self.type = update_type
        self.tooltip = tooltip      #TOFU: not needed for CLI, but leaving for compatibility with GUI
        self.packages = []

    def add_package(self, package, size, short_description, description):
        self.packages.append(package)
        self.description = description
        self.short_description = short_description
        self.size += size

class ChangelogRetriever():     #class ChangelogRetriever(threading.Thread):
    def __init__(self, source_package, level, version, wTree):
        #threading.Thread.__init__(self)
        self.source_package = source_package
        self.level = level
        self.version = version
        self.wTree = wTree
        # get the proxy settings from gsettings
        self.ps = proxygsettings.get_proxy_settings()


        # Remove the epoch if present in the version
        if ":" in self.version:
            self.version = self.version.split(":")[-1]

    def run(self):
        #gtk.gdk.threads_enter()
        #self.wTree.get_widget("textview_changes").get_buffer().set_text(_("Downloading changelog..."))
        #gtk.gdk.threads_leave()

        changelog_sources = []
        if (self.source_package.startswith("lib")):
            changelog_sources.append("http://changelogs.ubuntu.com/changelogs/pool/main/%s/%s/%s_%s/changelog" % (self.source_package[0:4], self.source_package, self.source_package, self.version))
            changelog_sources.append("http://changelogs.ubuntu.com/changelogs/pool/multiverse/%s/%s/%s_%s/changelog" % (self.source_package[0:4], self.source_package, self.source_package, self.version))
            changelog_sources.append("http://changelogs.ubuntu.com/changelogs/pool/universe/%s/%s/%s_%s/changelog" % (self.source_package[0:4], self.source_package, self.source_package, self.version))
            changelog_sources.append("http://changelogs.ubuntu.com/changelogs/pool/restricted/%s/%s/%s_%s/changelog" % (self.source_package[0:4], self.source_package, self.source_package, self.version))
        else:
            changelog_sources.append("http://changelogs.ubuntu.com/changelogs/pool/main/%s/%s/%s_%s/changelog" % (self.source_package[0], self.source_package, self.source_package, self.version))
            changelog_sources.append("http://changelogs.ubuntu.com/changelogs/pool/multiverse/%s/%s/%s_%s/changelog" % (self.source_package[0], self.source_package, self.source_package, self.version))
            changelog_sources.append("http://changelogs.ubuntu.com/changelogs/pool/universe/%s/%s/%s_%s/changelog" % (self.source_package[0], self.source_package, self.source_package, self.version))
            changelog_sources.append("http://changelogs.ubuntu.com/changelogs/pool/restricted/%s/%s/%s_%s/changelog" % (self.source_package[0], self.source_package, self.source_package, self.version))
        changelog_sources.append("http://packages.linuxmint.com/dev/" + self.source_package + "_" + self.version + "_amd64.changes")
        changelog_sources.append("http://packages.linuxmint.com/dev/" + self.source_package + "_" + self.version + "_i386.changes")

        changelog = _("No changelog available")

        if self.ps == {}:
            # use default urllib2 proxy mechanisms (possibly *_proxy environment vars)
            proxy = urllib2.ProxyHandler()
        else:
            # use proxy settings retrieved from gsettings
            proxy = urllib2.ProxyHandler(self.ps)

        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)

        for changelog_source in changelog_sources:
            try:
                print "Trying to fetch the changelog from: %s" % changelog_source
                url = urllib2.urlopen(changelog_source, None, 10)
                source = url.read()
                url.close()

                changelog = ""
                if "linuxmint.com" in changelog_source:
                    changes = source.split("\n")
                    for change in changes:
                        change = change.strip()
                        if change.startswith("*"):
                            changelog = changelog + change + "\n"
                else:
                    changelog = source
                break
            except:
                pass

        #gtk.gdk.threads_enter()
        #self.wTree.get_widget("textview_changes").get_buffer().set_text(changelog)
        #gtk.gdk.threads_leave()

#TOFU:
class InstallKernelThread():    #class InstallKernelThread(threading.Thread):

    def __init__(self, version, remove=False):    #def __init__(self, version, wTree, remove=False):
        #threading.Thread.__init__(self)
        self.version = version
        #self.wTree = wTree
        self.remove = remove

    #TOFU:
    def set_args(self, args):
        self.args=args

    #TOFU:
    def run(self):
        """
        cmd = ["pkexec", "/usr/sbin/synaptic", "--hide-main-window",  \
                "--non-interactive", "--parent-window-id", "%s" % self.wTree.get_widget("window5").window.xid]
        cmd.append("-o")
        cmd.append("Synaptic::closeZvt=true")
        cmd.append("--progress-str")
        cmd.append("\"" + _("Please wait, this can take some time") + "\"")
        cmd.append("--finish-str")
        if self.remove:
            cmd.append("\"" + _("The %s kernel was removed") % self.version + "\"")
        else:
            cmd.append("\"" + _("The %s kernel was installed") % self.version + "\"")
        f = tempfile.NamedTemporaryFile()

        for pkg in ['linux-headers-%s' % self.version, 'linux-headers-%s-generic' % self.version, 'linux-image-%s-generic' % self.version, 'linux-image-extra-%s-generic' % self.version]:
            if self.remove:
                f.write("%s\tdeinstall\n" % pkg)
            else:
                f.write("%s\tinstall\n" % pkg)
        cmd.append("--set-selections-file")
        cmd.append("%s" % f.name)
        f.flush()
        comnd = Popen(' '.join(cmd), stdout=log, stderr=log, shell=True)
        returnCode = comnd.wait()
        f.close()
        #sts = os.waitpid(comnd.pid, 0)
        """

        packagesA=['linux-headers-%s' % self.version, 'linux-headers-%s-generic' % self.version, 'linux-image-%s-generic' % self.version, 'linux-image-extra-%s-generic' % self.version]
        action=("install","remove")[self.remove]

        log.writelines("++ Ready to launch apt-get "+action+"\n")
        log.flush()

        #cmd = ["pkexec", "/usr/bin/apt-get", "-s", "install" ]
        cmd = ["sudo", "/usr/bin/apt-get"]
        if (self.args.simulate):
            cmd += ["-s"]
        cmd += [ "--show-progress", action ]
        cmd += packagesA
        if (self.args.debug): print ' '.join(cmd)

        #comnd = Popen(' '.join(cmd), stdout=log, stderr=log, shell=True)
        returnCode = exec_log(' '.join(cmd), log) 
        if (self.args.debug): print "Return code: "+str(returnCode)
        log.writelines("++ Return code:" + str(returnCode) + "\n")
        log.writelines("++ "+action+" finished\n")
        log.flush()
        

class InstallThread():      #class InstallThread(threading.Thread):
    #global icon_busy
    #global icon_up2date
    #global icon_updates
    #global icon_error
    #global icon_unknown
    #global icon_apply

    def __init__(self):    #def __init__(self, treeView, statusIcon, wTree):
        #threading.Thread.__init__(self)
        #self.treeView = treeView
        #self.statusIcon = statusIcon
        #self.wTree = wTree
        #TOFU:
        self.args=type('', (), {})()    #empty object
        self.packageA=[]

    #TOFU:
    #def start(self, packagesA, args):
    #    return self.run(packagesA, args)

    #TOFU:
    def set_args(self, args):
        self.args=args

    def set_packages(self, packagesA):
        self.packagesA=packagesA

    #TOFU:
    def run(self):
        global log
        try:
            log.writelines("++ Install requested by user\n")
            log.flush()
            #gtk.gdk.threads_enter()
            #self.wTree.get_widget("window1").window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
            #self.wTree.get_widget("window1").set_sensitive(False)
            installNeeded = False
            #packages = []
            #model = self.treeView.get_model()
            #gtk.gdk.threads_leave()

            #iter = model.get_iter_first()
            #while (iter != None):
            #    checked = model.get_value(iter, UPDATE_CHECKED)
            #    if (checked == "true"):
            #        installNeeded = True
            #        package_update = model.get_value(iter, UPDATE_OBJ)
            #        for package in package_update.packages:
            #            packages.append(package)
            #            log.writelines("++ Will install " + str(package) + "\n")
            #            log.flush()
            #    iter = model.iter_next(iter)

            #TOFU:
            packages = self.packagesA
            if (len(packages)>0):
                installNeeded = True

            if (installNeeded == True):

                proceed = True
                try:
                    pkgs = ' '.join(str(pkg) for pkg in packages)
                    warnings = commands.getoutput("/usr/lib/linuxmint/mintUpdate/checkWarnings.py %s" % pkgs)
                    #print ("/usr/lib/linuxmint/mintUpdate/checkWarnings.py %s" % pkgs)
                    warnings = warnings.split("###")
                    if len(warnings) == 2:
                        installations = warnings[0].split()
                        removals = warnings[1].split()
                        if len(installations) > 0 or len(removals) > 0:
                            #gtk.gdk.threads_enter()
                            try:
                                """
                                dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK_CANCEL, None)
                                dialog.set_title("")
                                dialog.set_markup("<b>" + _("This upgrade will trigger additional changes") + "</b>")
                                #dialog.format_secondary_markup("<i>" + _("All available upgrades for this package will be ignored.") + "</i>")                                
                                dialog.set_icon_from_file("/usr/lib/linuxmint/mintUpdate/icons/base.svg")
                                dialog.set_default_size(320, 400)
                                dialog.set_resizable(True)
                                """

                                if len(removals) > 0:
                                    # Removals
                                    label = gtk.Label()
                                    if len(removals) == 1:
                                        #label.set_text(_("The following package will be removed:"))
                                        log.writelines("The following package will be removed:\n")
                                        log.flush()
                                    else:
                                        #label.set_text(_("The following %d packages will be removed:") % len(removals))
                                        log.writelines("The following %d packages will be removed:" % len(removals) )
                                        log.flush()

                                    """
                                    label.set_alignment(0, 0.5)
                                    scrolledWindow = gtk.ScrolledWindow()
                                    scrolledWindow.set_shadow_type(gtk.SHADOW_IN)
                                    scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                                    treeview = gtk.TreeView()
                                    column1 = gtk.TreeViewColumn("", gtk.CellRendererText(), text=0)
                                    column1.set_sort_column_id(0)
                                    column1.set_resizable(True)
                                    treeview.append_column(column1)
                                    treeview.set_headers_clickable(False)
                                    treeview.set_reorderable(False)
                                    treeview.set_headers_visible(False)
                                    model = gtk.TreeStore(str)
                                    """
                                    removals.sort()
                                    """
                                    for pkg in removals:
                                        iter = model.insert_before(None, None)
                                        model.set_value(iter, 0, pkg)
                                    treeview.set_model(model)
                                    treeview.show()
                                    scrolledWindow.add(treeview)
                                    dialog.vbox.pack_start(label, False, False, 0)
                                    dialog.vbox.pack_start(scrolledWindow, True, True, 0)
                                    """

                                if len(installations) > 0:
                                    # Installations
                                    label = gtk.Label()
                                    if len(installations) == 1:
                                        #label.set_text(_("The following package will be installed:"))
                                        log.writelines("The following package will be installed:\n")
                                        log.flush()
                                    else:
                                        #label.set_text(_("The following %d packages will be installed:") % len(installations))
                                        log.writelines("The following %d packages will be installed:" % len(installations) )
                                        log.flush()
                                    """
                                    label.set_alignment(0, 0.5)
                                    scrolledWindow = gtk.ScrolledWindow()
                                    scrolledWindow.set_shadow_type(gtk.SHADOW_IN)
                                    scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                                    treeview = gtk.TreeView()
                                    column1 = gtk.TreeViewColumn("", gtk.CellRendererText(), text=0)
                                    column1.set_sort_column_id(0)
                                    column1.set_resizable(True)
                                    treeview.append_column(column1)
                                    treeview.set_headers_clickable(False)
                                    treeview.set_reorderable(False)
                                    treeview.set_headers_visible(False)
                                    model = gtk.TreeStore(str)
                                    """
                                    installations.sort()
                                    """
                                    for pkg in installations:
                                        iter = model.insert_before(None, None)
                                        model.set_value(iter, 0, pkg)
                                    treeview.set_model(model)
                                    treeview.show()
                                    scrolledWindow.add(treeview)
                                    dialog.vbox.pack_start(label, False, False, 0)
                                    dialog.vbox.pack_start(scrolledWindow, True, True, 0)
                                    """

                                """
                                dialog.show_all()
                                if dialog.run() == gtk.RESPONSE_OK:
                                    proceed = True
                                else:
                                    proceed = False
                                dialog.destroy()
                                """
                            except Exception, detail:
                                print detail
                            #gtk.gdk.threads_leave()
                        else:
                            proceed = True
                except Exception, details:
                    print details

                if proceed:
                    #gtk.gdk.threads_enter()
                    #self.statusIcon.set_from_file(icon_apply)
                    #self.statusIcon.set_tooltip(_("Installing updates"))
                    #gtk.gdk.threads_leave()
                    
                    #TOFU: replace synaptic by apt-get:
                    #/usr/sbin/synaptic --hide-main-window --non-interactive --parent-window-id 46137375 -o Synaptic::closeZvt=true
                    # --progress-str Please wait, this can take some time --finish-str Update is complete --set-selections-file /tmp/tmp2mxEso

                    """
                    log.writelines("++ Ready to launch synaptic\n")
                    log.flush()
                    cmd = ["pkexec", "/usr/sbin/synaptic", "--hide-main-window",  \
                            "--non-interactive", "--parent-window-id", "%s" % self.wTree.get_widget("window1").window.xid]
                    cmd.append("-o")
                    cmd.append("Synaptic::closeZvt=true")
                    cmd.append("--progress-str")
                    cmd.append("\"" + _("Please wait, this can take some time") + "\"")
                    cmd.append("--finish-str")
                    cmd.append("\"" + _("Update is complete") + "\"")
                    f = tempfile.NamedTemporaryFile()

                    for pkg in packages:
                        f.write("%s\tinstall\n" % pkg)
                    cmd.append("--set-selections-file")
                    cmd.append("%s" % f.name)
                    f.flush()
                    comnd = Popen(' '.join(cmd), stdout=log, stderr=log, shell=True)
                    returnCode = comnd.wait()
                    log.writelines("++ Return code:" + str(returnCode) + "\n")
                    #sts = os.waitpid(comnd.pid, 0)
                    f.close()
                    log.writelines("++ Install finished\n")
                    log.flush()
                    """

                    log.writelines("++ Ready to launch apt-get\n")
                    log.flush()
                    #cmd = ["pkexec", "/usr/bin/apt-get", "-s", "install" ]
                    cmd = ["sudo", "/usr/bin/apt-get"]
                    if (self.args.simulate):
                        cmd += ["-s"]
                    cmd += ["--show-progress", "install"]
                    cmd += packages
                    if (self.args.debug): print ' '.join(cmd)

                    #comnd = Popen(' '.join(cmd), stdout=log, stderr=log, shell=True)
                    returnCode = exec_log(' '.join(cmd), log)
                    if (self.args.debug): print "Return code: "+str(returnCode)
                    log.writelines("++ Return code:" + str(returnCode) + "\n")
                    log.writelines("++ Install finished\n")
                    log.flush()


                    if "mintupdate" in packages:
                        # Restart                        
                        try:
                            log.writelines("++ Mintupdate was updated, restarting it...\n")
                            log.flush()
                            log.close()
                        except:
                            pass #cause we might have closed it already

                        command = "/usr/lib/linuxmint/mintUpdate/mintUpdate.py show &"
                        os.system(command)

                    else:
                        # Refresh
                        #gtk.gdk.threads_enter()
                        #self.statusIcon.set_from_file(icon_busy)
                        #self.statusIcon.set_tooltip(_("Checking for updates"))
                        #self.wTree.get_widget("window1").window.set_cursor(None)
                        #self.wTree.get_widget("window1").set_sensitive(True)
                        #gtk.gdk.threads_leave()
                        #refresh = RefreshThread(self.treeView, self.statusIcon, self.wTree)
                        #refresh.start()
                        pass
                else:
                    # Stop the blinking but don't refresh
                    #gtk.gdk.threads_enter()
                    #self.wTree.get_widget("window1").window.set_cursor(None)
                    #self.wTree.get_widget("window1").set_sensitive(True)
                    #gtk.gdk.threads_leave()
                    pass
            else:
                # Stop the blinking but don't refresh
                #gtk.gdk.threads_enter()
                #self.wTree.get_widget("window1").window.set_cursor(None)
                #self.wTree.get_widget("window1").set_sensitive(True)
                #gtk.gdk.threads_leave()
                pass

        except Exception, detail:
            log.writelines("-- Exception occured in the install thread: " + str(detail) + "\n")
            log.flush()
            #gtk.gdk.threads_enter()
            #self.statusIcon.set_from_file(icon_error)
            #self.statusIcon.set_tooltip(_("Could not install the security updates"))
            log.writelines("-- Could not install security updates\n")
            log.flush()
            #self.statusIcon.set_blinking(False)
            #self.wTree.get_widget("window1").window.set_cursor(None)
            #self.wTree.get_widget("window1").set_sensitive(True)
            #gtk.gdk.threads_leave()

def print_formatted(pkgFrmAD, pkgValD):

    output=''
    #for pFrmKey in pkgFrmA:
    #    output+=pkgFrmOD[pFrmKey].format(pkgValOD[pFrmKey])
    #for i, pkgFrm in enumerate(pkgFrmA):
    #    output+=pkgFrm.format(pkgValA[i])

    #for idx, val in enumerate(ints):
    #for i, pFrmKeyD in enumerate(pkgFrmAD):
    for pFrmKeyD in pkgFrmAD:
        key=pFrmKeyD.keys()[0]
        #output+=pFrmKeyD[key].format(pkgValAD[i][key])
        if key in pkgValD:
            output+=pFrmKeyD[key].format(pkgValD[key])
        else:
            print "print_formatted error: "+key+" not found in pkgValD"

    print output

def print_formatted_multiline(pkgFrmAD, pkgValD):

    splitItemsD={}
    splitItemCounter=0
    output=''
    while True:
        for pFrmKeyD in pkgFrmAD:
            key=pFrmKeyD.keys()[0]
            #print "KEY: "+key

            if (not key in pkgValD):
                print "print_formatted_multiline error: "+key+" not found in pkgValD"
                break           #break for loop, not while

            if (type(pFrmKeyD[key]) is str):
                if (key in splitItemsD and splitItemsD[key]==None):
                    unformatted_output=''
                else:
                    unformatted_output=pkgValD[key]

                output+=pFrmKeyD[key].format(unformatted_output)
                splitItemsD[key]=None

            elif (type(pFrmKeyD[key]) is list):
                maxV=pFrmKeyD[key][0]
                frmV=pFrmKeyD[key][1]

                if (key in splitItemsD and splitItemsD[key]==None):
                    unformatted_output=''
                else:

                    if (not key in splitItemsD):
                        splitItemsD[key]=pkgValD[key].split(' ')
                        splitItemCounter += 1

                    if (len(splitItemsD[key]) > 0):
                        unformatted_output=''
                        while (len(splitItemsD[key]) > 0):
                            if ( (len(splitItemsD[key][0])  + 1 ) > maxV):
                                #print "Error: single word bigger than limiti",  cut can happen here as well
                                unformatted_output+=splitItemsD[key].pop(0)+' '
                                break
                            elif ( (len(unformatted_output) + len(splitItemsD[key][0]) + 1 ) <= maxV ):
                                unformatted_output+=splitItemsD[key].pop(0)+' '
                            else:
                                break

                        if (len(splitItemsD[key]) == 0):
                            splitItemCounter -= 1
                            splitItemsD[key]=None

                output+=frmV.format(unformatted_output)

            else:
                print "Error 273464: unknown type"

        if (splitItemCounter==0):
            break   #while end
        else:
            output+="\n"

    print(output)

class RefreshThread():      #class RefreshThread(threading.Thread):
    #global icon_busy
    #global icon_up2date
    #global icon_updates
    #global icon_error
    #global statusbar
    #global context_id

    def __init__(self, root_mode=False):  #def __init__(self, treeview_update, statusIcon, wTree, root_mode=False):
        #threading.Thread.__init__(self)
        #self.treeview_update = treeview_update
        #self.statusIcon = statusIcon
        #self.wTree = wTree
        self.root_mode = root_mode
        #TOFU:
        self.args=type('', (), {})()    #empty object

    #TOFU:
    #def start(self, args):
    #    return self.run(args)      ##return self.run()

    #TOFU:
    def set_args(self, args):
        self.args=args

    #TOFU:
    def print_package(self, pkgFrmAD, pkgValD):
        print_formatted(pkgFrmAD, pkgValD)


    def fetch_l10n_descriptions(self, package_names):
        if os.path.exists("/var/lib/apt/lists"):
            try:
                super_buffer = []
                for file in os.listdir("/var/lib/apt/lists"):
                    if ("i18n_Translation") in file and not file.endswith("Translation-en"):
                        fd = codecs.open(os.path.join("/var/lib/apt/lists", file), "r", "utf-8")
                        super_buffer += fd.readlines()

                i = 0
                while i < len(super_buffer):
                    line = super_buffer[i].strip()
                    if line.startswith("Package: "):
                        try:
                            pkgname = line.replace("Package: ", "")
                            short_description = ""
                            description = ""
                            j = 2 # skip md5 line after package name line
                            while True:
                                if (i+j >= len(super_buffer)):
                                    break
                                line = super_buffer[i+j].strip()
                                if line.startswith("Package: "):
                                    break
                                if j==2:
                                    short_description = line
                                else:
                                    description += "\n" + line
                                j += 1
                            if pkgname in package_names:
                                if not package_descriptions.has_key(pkgname):
                                    package_short_descriptions[pkgname] = short_description
                                    package_descriptions[pkgname] = description
                        except Exception, detail:
                            print "a %s" % detail
                    i += 1
                del super_buffer
            except Exception, detail:
                print "Could not fetch l10n descriptions.."
                print detail

    def run(self):
        global log
        #global app_hidden
        #gtk.gdk.threads_enter()
        #vpaned_position = wTree.get_widget("vpaned1").get_position()
        #gtk.gdk.threads_leave()
        try:
            log.writelines("++ Starting refresh\n")
            log.flush()
            """
            gtk.gdk.threads_enter()
            statusbar.push(context_id, _("Starting refresh..."))
            self.wTree.get_widget("window1").window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
            self.wTree.get_widget("window1").set_sensitive(False)
            self.wTree.get_widget("label_error_detail").set_text("")
            self.wTree.get_widget("hbox_error").hide()
            self.wTree.get_widget("scrolledwindow1").hide()
            self.wTree.get_widget("viewport1").hide()
            self.wTree.get_widget("label_error_detail").hide()
            self.wTree.get_widget("image_error").hide()
            # Starts the blinking
            self.statusIcon.set_from_file(icon_busy)
            self.statusIcon.set_tooltip(_("Checking for updates"))
            wTree.get_widget("vpaned1").set_position(vpaned_position)
            #self.statusIcon.set_blinking(True)
            gtk.gdk.threads_leave()

            model = gtk.TreeStore(str, str, gtk.gdk.Pixbuf, str, str, str, int, str, gtk.gdk.Pixbuf, str, str, str, object)
            # UPDATE_CHECKED, UPDATE_NAME, UPDATE_LEVEL_PIX, UPDATE_OLD_VERSION, UPDATE_NEW_VERSION, UPDATE_LEVEL_STR,
            # UPDATE_SIZE, UPDATE_SIZE_STR, UPDATE_TYPE_PIX, UPDATE_TYPE, UPDATE_TOOLTIP, UPDATE_SORT_STR, UPDATE_OBJ

            model.set_sort_column_id( UPDATE_SORT_STR, gtk.SORT_ASCENDING )
            """

            prefs = read_configuration()

            # Check to see if no other APT process is running
            if self.root_mode:
                p1 = Popen(['ps', '-U', 'root', '-o', 'comm'], stdout=PIPE)
                p = p1.communicate()[0]
                running = False
                pslist = p.split('\n')
                for process in pslist:
                    if process.strip() in ["dpkg", "apt-get","synaptic","update-manager", "adept", "adept-notifier"]:
                        running = True
                        break
                if (running == True):
                    #gtk.gdk.threads_enter()
                    #self.statusIcon.set_from_file(icon_unknown)
                    #self.statusIcon.set_tooltip(_("Another application is using APT"))
                    #statusbar.push(context_id, _("Another application is using APT"))
                    log.writelines("-- Another application is using APT\n")
                    log.flush()
                    #self.statusIcon.set_blinking(False)
                    #self.wTree.get_widget("window1").window.set_cursor(None)
                    #self.wTree.get_widget("window1").set_sensitive(True)
                    #gtk.gdk.threads_leave()
                    return False
 
            #gtk.gdk.threads_enter()
            #statusbar.push(context_id, _("Finding the list of updates..."))
            log.writelines("-- Finding the list of updates...\n")
            log.flush()
            #wTree.get_widget("vpaned1").set_position(vpaned_position)
            #gtk.gdk.threads_leave()
            #if app_hidden:
            refresh_command = "/usr/lib/linuxmint/mintUpdate/checkAPT.py 2>/dev/null"
            #else:
            #    refresh_command = "/usr/lib/linuxmint/mintUpdate/checkAPT.py --use-synaptic %s 2>/dev/null" % self.wTree.get_widget("window1").window.xid
            if self.root_mode:
                refresh_command = "sudo %s" % refresh_command
            updates =  commands.getoutput(refresh_command)

            # Look for mintupdate
            if ("UPDATE###mintupdate###" in updates):
                new_mintupdate = True
            else:
                new_mintupdate = False

            updates = string.split(updates, "---EOL---")

            # Look at the updates one by one
            package_updates = {}
            package_names = Set()

            #TOFU:
            visible_package_namesS = Set()

            num_visible = 0
            num_safe = 0
            download_size = 0
            num_ignored = 0
    
            #TOFU:
            ignored_list = get_ignore_list()
            """
            if os.path.exists("%s/mintupdate.ignored" % CONFIG_DIR):
                blacklist_file = open("%s/mintupdate.ignored" % CONFIG_DIR, "r")
                for blacklist_line in blacklist_file:
                    ignored_list.append(blacklist_line.strip())
                blacklist_file.close()
            """

            if (len(updates) == None):
                #self.statusIcon.set_from_file(icon_up2date)
                #self.statusIcon.set_tooltip(_("Your system is up to date"))
                #statusbar.push(context_id, _("Your system is up to date"))
                print (_("Your system is up to date"))
                log.writelines("++ System is up to date\n")
                log.flush()
            else:
                for pkg in updates:
                    values = string.split(pkg, "###")
                    if len(values) == 9:
                        status = values[0]
                        if (status == "ERROR"):
                            try:
                                error_msg = updates[1]
                            except:
                                error_msg = ""

                            #gtk.gdk.threads_enter()
                            #self.statusIcon.set_from_file(icon_error)
                            #self.statusIcon.set_tooltip("%s\n\n%s" % (_("Could not refresh the list of updates"), error_msg))
                            #statusbar.push(context_id, _("Could not refresh the list of updates"))
                            log.writelines("-- Error in checkAPT.py, could not refresh the list of updates\n")
                            log.flush()
                            """
                            self.wTree.get_widget("label_error_detail").set_text(error_msg)
                            self.wTree.get_widget("label_error_detail").show()
                            self.wTree.get_widget("viewport1").show()
                            self.wTree.get_widget("scrolledwindow1").show()
                            self.wTree.get_widget("image_error").show()
                            self.wTree.get_widget("hbox_error").show()
                            #self.statusIcon.set_blinking(False)
                            self.wTree.get_widget("window1").window.set_cursor(None)
                            self.wTree.get_widget("window1").set_sensitive(True)
                            #statusbar.push(context_id, _(""))
                            gtk.gdk.threads_leave()
                            """
                            return False

                        package = values[1]
                        #TOFU:
                        #print package+" "+values[0]+"\n"
                        newVersion = values[2]
                        oldVersion = values[3]
                        size = int(values[4])
                        source_package = values[5]
                        update_type = values[6]
                        short_description = values[7]
                        description = values[8]

                        package_names.add(package.replace(":i386", "").replace(":amd64", ""))

                        if not package_updates.has_key(source_package):
                            updateIsBlacklisted = False
                            for blacklist in ignored_list:
                                if fnmatch.fnmatch(source_package, blacklist):
                                    num_ignored = num_ignored + 1
                                    updateIsBlacklisted = True
                                    break

                            if updateIsBlacklisted:
                                continue

                            is_a_mint_package = False
                            if (update_type == "linuxmint"):
                                update_type = "package"
                                is_a_mint_package = True

                            security_update = (update_type == "security")

                            """
                            if update_type == "security":
                                tooltip = _("Security update")
                            elif update_type == "backport":
                                tooltip = _("Software backport. Be careful when upgrading. New versions of sofware can introduce regressions.")
                            elif update_type == "unstable":
                                tooltip = _("Unstable software. Only apply this update to help developers beta-test new software.")
                            else:
                                tooltip = _("Software update")
                            """

                            extraInfo = ""
                            warning = ""
                            if is_a_mint_package:
                                level = 1 # Level 1 by default
                            else:
                                level = 3 # Level 3 by default
                            rulesFile = open("/usr/lib/linuxmint/mintUpdate/rules","r")
                            rules = rulesFile.readlines()
                            goOn = True
                            foundPackageRule = False # whether we found a rule with the exact package name or not
                            for rule in rules:
                                if (goOn == True):
                                    rule_fields = rule.split("|")
                                    if (len(rule_fields) == 5):
                                        rule_package = rule_fields[0]
                                        rule_version = rule_fields[1]
                                        rule_level = rule_fields[2]
                                        rule_extraInfo = rule_fields[3]
                                        rule_warning = rule_fields[4]
                                        if (rule_package == source_package):
                                            foundPackageRule = True
                                            if (rule_version == newVersion):
                                                level = rule_level
                                                extraInfo = rule_extraInfo
                                                warning = rule_warning
                                                goOn = False # We found a rule with the exact package name and version, no need to look elsewhere
                                            else:
                                                if (rule_version == "*"):
                                                    level = rule_level
                                                    extraInfo = rule_extraInfo
                                                    warning = rule_warning
                                        else:
                                            if (rule_package.startswith("*")):
                                                keyword = rule_package.replace("*", "")
                                                index = source_package.find(keyword)
                                                if (index > -1 and foundPackageRule == False):
                                                    level = rule_level
                                                    extraInfo = rule_extraInfo
                                                    warning = rule_warning
                            rulesFile.close()
                            level = int(level)

                            # Create a new Update
                            update = PackageUpdate(source_package, level, oldVersion, newVersion, extraInfo, warning, update_type, None) #TOFU: Tooltip is not defined in CLI
                            update.add_package(package, size, short_description, description)
                            package_updates[source_package] = update
                        else:
                            # Add the package to the Update
                            update = package_updates[source_package]
                            update.add_package(package, size, short_description, description)

                        #TOFU: 
                        #pprint (vars(update))
                        #print "\n"

                self.fetch_l10n_descriptions(package_names)

                #TOFU:
                visible_package_groupsA=[]
                
                if (self.args.debug):
                    pprint (package_updates)
                    print "\n"
                    pprint (package_names)
                    print "\n"

                #TOFU:
                selected_package_groupsA=package_updates.keys() #selected=all available
               
                #pprint (vars(self.args))
                #sys.exit(-222)
                #if (getATTR(self.args, 'command')=='add-ignored'):
                    #print self.args.ignoreA
                    #print selected_package_groupsA


                if (hasATTR(self.args, 'groupsA')):
                    if (len(self.args.groupsA) != len(set(self.args.groupsA))):
                        duplicates = "'"+"', '".join(set([x for x in self.args.groupsA if self.args.groupsA.count(x) > 1]))+"'"
                        print (_("Error: Duplicate package groups specified: ") + duplicates)
                        sys.exit(-1)
                        
                    not_subsetS = set(self.args.groupsA) - set(selected_package_groupsA)
                    if (len(not_subsetS)):
                        print (_("Error: Unknown package group(s) specified: '") + "', '".join(not_subsetS)+"'")
                        sys.exit(-2)

                    selected_package_groupsA=self.args.groupsA  #selected=only specified

                #for source_package in package_updates.keys():
                for source_package in selected_package_groupsA:

                    package_update = package_updates[source_package]


                    if (new_mintupdate and package_update.name != "mintupdate"):
                        continue

                    # l10n descriptions
                    l10n_descriptions(package_update)
                    package_update.short_description = clean_l10n_short_description(package_update.short_description)
                    package_update.description = clean_l10n_description(package_update.description)

                    security_update = (package_update.type == "security")

                    if ((prefs["level" + str(package_update.level) + "_visible"]) or (security_update and prefs['security_visible'])):
                        #iter = model.insert_before(None, None)
                        if (security_update and prefs['security_visible'] and prefs['security_safe']):
                            #model.set_value(iter, UPDATE_CHECKED, "true")
                            num_safe = num_safe + 1
                            download_size = download_size + package_update.size
                        elif (prefs["level" + str(package_update.level) + "_safe"]):
                            #model.set_value(iter, UPDATE_CHECKED, "true")
                            num_safe = num_safe + 1
                            download_size = download_size + package_update.size
                        #else:
                            #model.set_value(iter, UPDATE_CHECKED, "false")

                        #model.row_changed(model.get_path(iter), iter)

                        shortdesc = package_update.short_description
                        if len(shortdesc) > 100:
                            shortdesc = shortdesc[:100] + "..."

                        """
                        if (prefs["descriptions_visible"]):
                            model.set_value(iter, UPDATE_NAME, package_update.name + "\n<small><span foreground='#5C5C5C'>%s</span></small>" % shortdesc)
                        else:
                            model.set_value(iter, UPDATE_NAME, package_update.name)
                        model.set_value(iter, UPDATE_LEVEL_PIX, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintUpdate/icons/level" + str(package_update.level) + ".png"))
                        model.set_value(iter, UPDATE_OLD_VERSION, package_update.oldVersion)
                        model.set_value(iter, UPDATE_NEW_VERSION, package_update.newVersion)
                        model.set_value(iter, UPDATE_LEVEL_STR, str(package_update.level))
                        model.set_value(iter, UPDATE_SIZE, package_update.size)
                        model.set_value(iter, UPDATE_SIZE_STR, size_to_string(package_update.size))
                        model.set_value(iter, UPDATE_TYPE_PIX, gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintUpdate/icons/update-type-%s.png" % package_update.type))
                        model.set_value(iter, UPDATE_TYPE, package_update.type)
                        model.set_value(iter, UPDATE_TOOLTIP, package_update.tooltip)
                        model.set_value(iter, UPDATE_SORT_STR, "%s%s" % (str(package_update.level), package_update.name))
                        model.set_value(iter, UPDATE_OBJ, package_update)
                        """

                        #TOFU:
                        visible_package_groupsA.append(package_update.name)
                        #visible_package_namesS.add(package_update.packages)    #TypeError: list objects are unhashable
                        visible_package_namesS = visible_package_namesS.union(package_update.packages)  #list added to Set
                        num_visible = num_visible + 1

                #TOFU:
                if (self.args.debug):
                    print "----"+str(len(visible_package_namesS))+"-----\n"
                    print (visible_package_namesS)
                    print "------\n"

                if (len(visible_package_groupsA) and not(getATTR(self.args, 'supressRefreshDisplay'))):
                    #        type    level      name            size       old ver            new ver
                    #pkgFrmA=["{:s}", " [{:s}]", " {:<23s}",     " {:>5s}", " {:>30s}",        " {:>30s}"]
                    #pkgValA=[" ",    "L",       "Package group", "Size",    "Current version", "New version"]
                    #self.print_package(pkgFrmA, pkgValA)

                    #for visiblePkgA in visible_package_groupsAA:
                    #    self.print_package(pkgFrmA, visiblePkgA)
                    #    print package_updates[visiblePkgA[2]].packages


                    pkgValD={
                        'type':     " ",                    #type
                        'level':    "L",                    #level
                        'name':     "Package group (#)",    #package name
                        'size':     "Size",                 #size
                        'oldVer':   "Current version",      #current version of package
                        'newVer':   "New version"           #new version of package
                    }


                    pkgMaxLenD={
                        'name':         len(pkgValD['name']),
                        'oldVer':       len(pkgValD['oldVer']),
                        'newVer':       len(pkgValD['newVer'])
                    }    
    
                    for visiblePkg in visible_package_groupsA:
                        pkgMaxLenD['name']=max(pkgMaxLenD['name'], len(package_updates[visiblePkg].name) + len(" ("+str(len(package_updates[visiblePkg].packages))+")"))
                        pkgMaxLenD['oldVer']=max(pkgMaxLenD['oldVer'], len(package_updates[visiblePkg].oldVersion))
                        pkgMaxLenD['newVer']=max(pkgMaxLenD['newVer'], len(package_updates[visiblePkg].newVersion))


                    pkgFrmAD=[
                        {'type':     "{:s}"},                                  #type
                        {'level':    " [{:s}]"},                               #level
                        {'name':     " {:<"+str(pkgMaxLenD['name'])+"s}"},     #package name
                        {'size':     " {:>5s}"},                               #size
                        {'oldVer':   " {:>"+str(pkgMaxLenD['oldVer'])+"s}"},   #current version of package
                        {'newVer':   " {:>"+str(pkgMaxLenD['newVer'])+"s}"}    #new version of package  
                    ] 

                    self.print_package(pkgFrmAD, pkgValD)
                    if (self.args.verbosity >= 1):
                        print "\n"

                    """
                    pkgFrmAD=[ 
                        {'type':     '!' if (package_update.type == 'security') else ' '},    #type (via ternary operator)
                        {'level':    str(package_update.level)},             #level
                        {'name':     package_update.name},                   #package name
                        {'size':     size_to_string(package_update.size)},   #size
                        {'oldVer':   package_update.oldVersion},             #current version of package
                        {'newVer':   package_update.newVersion}              #new version of package 
                    ]
                    """

                    #for visiblePkg in sorted(visible_package_groupsA):
                    for visiblePkg in sorted(visible_package_groupsA, key=lambda x:(package_updates[x].level, x)):  #sorting based on level (External) and name
                        pkgValD={
                            'type':     '!' if (package_updates[visiblePkg].type == 'security') else ' ',    #type (via ternary operator)
                            'level':    str(package_updates[visiblePkg].level),             #level
                            'name':     package_updates[visiblePkg].name+" ("+str(len(package_updates[visiblePkg].packages))+")",  #package name (number)
                            'size':     size_to_string(package_updates[visiblePkg].size),   #size
                            'oldVer':   package_updates[visiblePkg].oldVersion,             #current version of package 
                            'newVer':   package_updates[visiblePkg].newVersion              #new version of package
                        }
                        self.print_package(pkgFrmAD, pkgValD)
                        if (self.args.verbosity >= 1):
                            print "  Packages: "+", ".join(package_updates[visiblePkg].packages)  #+"\n"

                    print (_("!=security update, [L]=package level, (#)=number of packages in group"))

                #gtk.gdk.threads_enter()
                if (new_mintupdate):
                    #self.statusString = _("A new version of the update manager is available")
                    #self.statusIcon.set_from_file(icon_updates)
                    #self.statusIcon.set_tooltip(self.statusString)
                    #statusbar.push(context_id, self.statusString)
                    log.writelines("++ Found a new version of mintupdate\n")
                    log.flush()
                else:
 
                    if (num_safe > 0):
                        """
                        if (num_safe == 1):
                            if (num_ignored == 0):
                                self.statusString = _("1 recommended update available (%(size)s)") % {'size':size_to_string(download_size)}
                            elif (num_ignored == 1):
                                self.statusString = _("1 recommended update available (%(size)s), 1 ignored") % {'size':size_to_string(download_size)}
                            elif (num_ignored > 1):
                                self.statusString = _("1 recommended update available (%(size)s), %(ignored)d ignored") % {'size':size_to_string(download_size), 'ignored':num_ignored}
                        else:
                            if (num_ignored == 0):
                                self.statusString = _("%(recommended)d recommended updates available (%(size)s)") % {'recommended':num_safe, 'size':size_to_string(download_size)}
                            elif (num_ignored == 1):
                                self.statusString = _("%(recommended)d recommended updates available (%(size)s), 1 ignored") % {'recommended':num_safe, 'size':size_to_string(download_size)}                   
                            elif (num_ignored > 0):
                                self.statusString = _("%(recommended)d recommended updates available (%(size)s), %(ignored)d ignored") % {'recommended':num_safe, 'size':size_to_string(download_size), 'ignored':num_ignored}
                        """

                        #TOFU:  (above reworked + number of ignored groups added)
                        self.statusString = str(num_safe) + " " +_("recommended") + " " + (_("update"), _("updates"))[ num_safe > 1 ] + " available ("    #Ternary 2
                        self.statusString += str(len(visible_package_namesS)) + " " + (_("package"), _("packages"))[ len(visible_package_namesS) > 1 ] + ", "
                        self.statusString += size_to_string(download_size)  + ")"
                        if (num_ignored > 0 ):
                            self.statusString += ", " + str(len(ignored_list)) + " " + (_("group"), _("groups"))[ len(ignored_list)  > 1 ] + " " + _("ignored")
                            self.statusString += " (" + str(num_ignored) + " " + (_("package"), _("packages"))[ num_ignored > 1 ]  + " ignored)"

                        #self.statusIcon.set_from_file(icon_updates)
                        #self.statusIcon.set_tooltip(self.statusString)
                        #statusbar.push(context_id, self.statusString)

                        #TOFU:
                        if not getATTR(self.args, 'supressRefreshDisplay'):
                            print "\n" + self.statusString + "\n"

                        log.writelines(self.statusString + "\n")
                        log.writelines("++ Found " + str(num_safe) + " recommended software updates\n")
                        log.flush()
                    else:
                        #self.statusIcon.set_from_file(icon_up2date)
                        #self.statusIcon.set_tooltip(_("Your system is up to date"))
                        #statusbar.push(context_id, _("Your system is up to date"))
                        print (_("Your system is up to date"))
                        log.writelines("++ System is up to date\n")
                        log.flush()

            log.writelines("++ Refresh finished\n")
            log.flush()
            """
            # Stop the blinking
            self.statusIon.set_blinking(False)
            self.wTree.get_widget("notebook_details").set_current_page(0)
            self.wTree.get_widget("window1").window.set_cursor(None)
            self.treeview_update.set_model(model)
            del model
            self.wTree.get_widget("window1").set_sensitive(True)
            wTree.get_widget("vpaned1").set_position(vpaned_position)
            gtk.gdk.threads_leave()
            """
            #return ['asdf', 'asdf']
            if (getATTR(self.args, 'command')=='add-ignored'):
                return visible_package_groupsA
            else:
                return visible_package_namesS

        except Exception, detail:
            print "-- Exception occured in the refresh thread: " + str(detail)
            log.writelines("-- Exception occured in the refresh thread: " + str(detail) + "\n")
            log.flush()
            """
            gtk.gdk.threads_enter()
            self.statusIcon.set_from_file(icon_error)
            self.statusIcon.set_tooltip(_("Could not refresh the list of updates"))
            self.statusIcon.set_blinking(False)
            self.wTree.get_widget("window1").window.set_cursor(None)
            self.wTree.get_widget("window1").set_sensitive(True)
            statusbar.push(context_id, _("Could not refresh the list of updates"))
            wTree.get_widget("vpaned1").set_position(vpaned_position)
            gtk.gdk.threads_leave()
            """

    def checkDependencies(self, changes, cache):
        foundSomething = False
        for pkg in changes:
            for dep in pkg.candidateDependencies:
                for o in dep.or_dependencies:
                    try:
                        if cache[o.name].isUpgradable:
                            pkgFound = False
                            for pkg2 in changes:
                                if o.name == pkg2.name:
                                    pkgFound = True
                            if pkgFound == False:
                                newPkg = cache[o.name]
                                changes.append(newPkg)
                                foundSomething = True
                    except Exception, detail:
                        pass # don't know why we get these..
        if (foundSomething):
            changes = self.checkDependencies(changes, cache)
        return changes

#def force_refresh():         #def force_refresh(widget, treeview, statusIcon, wTree):
#    refresh = RefreshThread(root_mode=True)
#    refresh.start()

#def clear(widget, treeView, statusbar, context_id):
#def select_all(widget, treeView, statusbar, context_id):

#def install():
#    install = InstallThread()
#    install.start()

#def change_icon(widget, button, prefs_tree, treeview, statusIcon, wTree):

#TOFU:
def pref_apply_CLI(prefs):        #def pref_apply(widget, prefs_tree, treeview, statusIcon, wTree):
    """
    global icon_busy
    global icon_up2date
    global icon_updates
    global icon_error
    global icon_unknown
    global icon_apply
    """

    config = ConfigObj("%s/mintUpdate.conf" % CONFIG_DIR)

    #Write level config
    config['levels'] = {}
    config['levels']['level1_visible'] = prefs['level1_visible']
    config['levels']['level2_visible'] = prefs['level2_visible']
    config['levels']['level3_visible'] = prefs['level3_visible']
    config['levels']['level4_visible'] = prefs['level4_visible']
    config['levels']['level5_visible'] = prefs['level5_visible']
    config['levels']['level1_safe'] = prefs['level1_safe']
    config['levels']['level2_safe'] = prefs['level2_safe']
    config['levels']['level3_safe'] = prefs['level3_safe']
    config['levels']['level4_safe'] = prefs['level4_safe']
    config['levels']['level5_safe'] = prefs['level5_safe']
    config['levels']['security_visible'] = prefs['security_visible']
    config['levels']['security_safe'] = prefs['security_safe']

    #Write update config
    config['update'] = {}
    config['update']['dist_upgrade'] = prefs['dist_upgrade']

    """
    config['levels']['level1_visible'] = prefs_tree.get_widget("visible1").get_active()
    config['levels']['level2_visible'] = prefs_tree.get_widget("visible2").get_active()
    config['levels']['level3_visible'] = prefs_tree.get_widget("visible3").get_active()
    config['levels']['level4_visible'] = prefs_tree.get_widget("visible4").get_active()
    config['levels']['level5_visible'] = prefs_tree.get_widget("visible5").get_active()
    config['levels']['level1_safe'] = prefs_tree.get_widget("safe1").get_active()
    config['levels']['level2_safe'] = prefs_tree.get_widget("safe2").get_active()
    config['levels']['level3_safe'] = prefs_tree.get_widget("safe3").get_active()
    config['levels']['level4_safe'] = prefs_tree.get_widget("safe4").get_active()
    config['levels']['level5_safe'] = prefs_tree.get_widget("safe5").get_active()
    config['levels']['security_visible'] = prefs_tree.get_widget("checkbutton_security_visible").get_active()
    config['levels']['security_safe'] = prefs_tree.get_widget("checkbutton_security_safe").get_active()

    #Write refresh config
    #config['refresh'] = {}
    #config['refresh']['timer_minutes'] = int(prefs_tree.get_widget("timer_minutes").get_value())
    #config['refresh']['timer_hours'] = int(prefs_tree.get_widget("timer_hours").get_value())
    #config['refresh']['timer_days'] = int(prefs_tree.get_widget("timer_days").get_value())

    #Write update config
    config['update'] = {}
    config['update']['dist_upgrade'] = prefs_tree.get_widget("checkbutton_dist_upgrade").get_active()
    
    Write icons config
    config['icons'] = {}
    config['icons']['busy'] = icon_busy
    config['icons']['up2date'] = icon_up2date
    config['icons']['updates'] = icon_updates
    config['icons']['error'] = icon_error
    config['icons']['unknown'] = icon_unknown
    config['icons']['apply'] = icon_apply

    #Write blacklisted updates

    ignored_list = open("%s/mintupdate.ignored" % CONFIG_DIR, "w")
    treeview_blacklist = prefs_tree.get_widget("treeview_blacklist")
    model = treeview_blacklist.get_model()
    iter = model.get_iter_first()
    while iter is not None:
        pkg = model.get_value(iter, UPDATE_CHECKED)
        iter = model.iter_next(iter)
        ignored_list.writelines(pkg + "\n")
    ignored_list.close()
    """

    config.write()

    #prefs_tree.get_widget("window2").hide()
    #refresh = RefreshThread(treeview, statusIcon, wTree)
    #refresh.start()

#TOFU:
def save_ignore_list(listA):
    global log
    try:
        #Write blacklisted updates
        ignored_list = open("%s/mintupdate.ignored" % CONFIG_DIR, "w")
        for pkg in listA:
            ignored_list.writelines(pkg + "\n")
        ignored_list.close()

    except Exception, detail:
        print "Error: Cannot save file mintupdate.ignored."
        print detail
        log.writelines("-- Exception occured in main thread: " + str(detail) + "\n")
        log.flush()
        log.close()        


#def kernels_cancel(widget, tree):
#def history_cancel(widget, tree):
#def pref_cancel(widget, prefs_tree):


#TOFU:
#(c) Jan Andrejkovic
def try_set(val, default):
    try:
        return val()
    except:
        return default

def read_configuration():
    #global icon_busy
    #global icon_up2date
    #global icon_updates
    #global icon_error
    #global icon_unknown
    #global icon_apply

    config = ConfigObj("%s/mintUpdate.conf" % CONFIG_DIR)
    prefs = {}

    #Read refresh config
    prefs["timer_minutes"] = try_set(lambda: int(config['refresh']['timer_minutes']), 30)
    prefs["timer_hours"] = try_set(lambda: int(config['refresh']['timer_hours']), 0)
    prefs["timer_days"] = try_set(lambda: int(config['refresh']['timer_days']), 0)

    #Read update config
    prefs["dist_upgrade"] =  try_set(lambda: (config['update']['dist_upgrade'] == "True"), True)

    #Read icons config
    """
    try:
        icon_busy = config['icons']['busy']
        icon_up2date = config['icons']['up2date']
        icon_updates = config['icons']['updates']
        icon_error = config['icons']['error']
        icon_unknown = config['icons']['unknown']
        icon_apply = config['icons']['apply']
    except:
        icon_busy = "/usr/lib/linuxmint/mintUpdate/icons/base.svg"
        icon_up2date = "/usr/lib/linuxmint/mintUpdate/icons/base-apply.svg"
        icon_updates = "/usr/lib/linuxmint/mintUpdate/icons/base-info.svg"
        icon_error = "/usr/lib/linuxmint/mintUpdate/icons/base-error2.svg"
        icon_unknown = "/usr/lib/linuxmint/mintUpdate/icons/base.svg"
        icon_apply = "/usr/lib/linuxmint/mintUpdate/icons/base-exec.svg"
    """

    #Read levels config
    prefs["level1_visible"] = try_set(lambda: (config['levels']['level1_visible'] == "True"), True)
    prefs["level2_visible"] = try_set(lambda: (config['levels']['level2_visible'] == "True"), True)
    prefs["level3_visible"] = try_set(lambda: (config['levels']['level3_visible'] == "True"), True)
    prefs["level4_visible"] = try_set(lambda: (config['levels']['level4_visible'] == "True"), False)
    prefs["level5_visible"] = try_set(lambda: (config['levels']['level5_visible'] == "True"), False)
    prefs["level1_safe"] = try_set(lambda: (config['levels']['level1_safe'] == "True"), True)
    prefs["level2_safe"] = try_set(lambda: (config['levels']['level2_safe'] == "True"), True)
    prefs["level3_safe"] = try_set(lambda: (config['levels']['level3_safe'] == "True"), True)
    prefs["level4_safe"] = try_set(lambda: (config['levels']['level4_safe'] == "True"), False)
    prefs["level5_safe"] = try_set(lambda: (config['levels']['level5_safe'] == "True"), False)
    prefs["security_visible"] = try_set(lambda: (config['levels']['security_visible'] == "True"), True)
    prefs["security_safe"] = try_set(lambda: (config['levels']['security_safe'] == "True"), False)

    #Read columns config
    """
    try:
        prefs["type_column_visible"] = (config['visible_columns']['type'] == "True")
    except:
        prefs["type_column_visible"] = True
    try:
        prefs["level_column_visible"] = (config['visible_columns']['level'] == "True")
    except:
        prefs["level_column_visible"] = True
    try:
        prefs["package_column_visible"] = (config['visible_columns']['package'] == "True")
    except:
        prefs["package_column_visible"] = True
    try:
        prefs["old_version_column_visible"] = (config['visible_columns']['old_version'] == "True")
    except:
        prefs["old_version_column_visible"] = False
    try:
        prefs["new_version_column_visible"] = (config['visible_columns']['new_version'] == "True")
    except:
        prefs["new_version_column_visible"] = True
    try:
        prefs["size_column_visible"] = (config['visible_columns']['size'] == "True")
    except:
        prefs["size_column_visible"] = False
    try:
        prefs["descriptions_visible"] = (config['visible_columns']['description'] == "True")
    except:
        prefs["descriptions_visible"] = True

    #Read window dimensions
    try:
        prefs["dimensions_x"] = int(config['dimensions']['x'])
        prefs["dimensions_y"] = int(config['dimensions']['y'])
        prefs["dimensions_pane_position"] = int(config['dimensions']['pane_position'])
    except:
        prefs["dimensions_x"] = 790
        prefs["dimensions_y"] = 540
        prefs["dimensions_pane_position"] = 278
    """

    #Read package blacklist
    prefs["blacklisted_packages"] = try_set(lambda: config['blacklisted_packages'], [])
        #print prefs["blacklisted_packages"]
        #sys.exit(-222)


    #TOFU:
    #From open_preferences():
    prefs["level1_desc"]="Certified updates. Tested through Romeo or directly maintained by Linux Mint."
    prefs["level2_desc"]="Recommended updates. Tested and approved by Linux Mint."
    prefs["level3_desc"]="Safe updates. Not tested but believed to be safe."
    prefs["level4_desc"]="Unsafe updates. Could potentially affect the stability of the system."
    prefs["level5_desc"]="Dangerous updates. Known to affect the stability of the systems depending on certain specs or hardware."
    prefs["level1_origin"]="Linux Mint"
    prefs["level2_origin"]="Upstream"
    prefs["level3_origin"]="Upstream"
    prefs["level4_origin"]="Upstream"
    prefs["level5_origin"]="Upstream"
    prefs["level1_tested"]=True
    prefs["level2_tested"]=True
    prefs["level3_tested"]=False
    prefs["level4_tested"]=False
    prefs["level5_tested"]=False

    prefs["checkbutton_security_visible"]="Always show security updates"
    prefs["checkbutton_security_safe"]="Always select and trust security updates"
    prefs["checkbutton_dist_upgrade"]="Include updates which require the installation of new packages or the removal of installed packages"

    return prefs


def open_repositories():          #def open_repositories(widget): 
    if os.path.exists("/usr/bin/software-sources"):
        os.system("/usr/bin/software-sources &")
    elif os.path.exists("/usr/bin/software-properties-gtk"):
        os.system("/usr/bin/software-properties-gtk &")
    elif os.path.exists("/usr/bin/software-properties-kde"):
        os.system("/usr/bin/software-properties-kde &")

"""
def open_preferences(widget, treeview, statusIcon, wTree):
    global icon_busy
    global icon_up2date
    global icon_updates
    global icon_error
    global icon_unknown
    global icon_apply

    gladefile = "/usr/lib/linuxmint/mintUpdate/mintUpdate.glade"
    prefs_tree = gtk.glade.XML(gladefile, "window2")
    prefs_tree.get_widget("window2").set_title(_("Preferences") + " - " + _("Update Manager"))

    prefs_tree.get_widget("label37").set_text(_("Levels"))
    prefs_tree.get_widget("label36").set_text(_("Auto-Refresh"))
    prefs_tree.get_widget("label39").set_markup("<b>" + _("Level") + "</b>")
    prefs_tree.get_widget("label40").set_markup("<b>" + _("Description") + "</b>")
    prefs_tree.get_widget("label48").set_markup("<b>" + _("Tested?") + "</b>")
    prefs_tree.get_widget("label54").set_markup("<b>" + _("Origin") + "</b>")
    prefs_tree.get_widget("label41").set_markup("<b>" + _("Safe?") + "</b>")
    prefs_tree.get_widget("label42").set_markup("<b>" + _("Visible?") + "</b>")
    prefs_tree.get_widget("label43").set_text(_("Certified updates. Tested through Romeo or directly maintained by Linux Mint."))
    prefs_tree.get_widget("label44").set_text(_("Recommended updates. Tested and approved by Linux Mint."))
    prefs_tree.get_widget("label45").set_text(_("Safe updates. Not tested but believed to be safe."))
    prefs_tree.get_widget("label46").set_text(_("Unsafe updates. Could potentially affect the stability of the system."))
    prefs_tree.get_widget("label47").set_text(_("Dangerous updates. Known to affect the stability of the systems depending on certain specs or hardware."))
    prefs_tree.get_widget("label55").set_text(_("Linux Mint"))
    prefs_tree.get_widget("label56").set_text(_("Upstream"))
    prefs_tree.get_widget("label57").set_text(_("Upstream"))
    prefs_tree.get_widget("label58").set_text(_("Upstream"))
    prefs_tree.get_widget("label59").set_text(_("Upstream"))
    prefs_tree.get_widget("label81").set_text(_("Refresh the list of updates every:"))
    prefs_tree.get_widget("label82").set_text("<i>" + _("Note: The list only gets refreshed while the update manager window is closed (system tray mode).") + "</i>")
    prefs_tree.get_widget("label82").set_use_markup(True)
    prefs_tree.get_widget("label83").set_text(_("Update Method"))     
    prefs_tree.get_widget("label85").set_text(_("Icons"))
    prefs_tree.get_widget("label86").set_markup("<b>" + _("Icon") + "</b>")
    prefs_tree.get_widget("label87").set_markup("<b>" + _("Status") + "</b>")
    prefs_tree.get_widget("label95").set_markup("<b>" + _("New Icon") + "</b>")
    prefs_tree.get_widget("label88").set_text(_("Busy"))
    prefs_tree.get_widget("label89").set_text(_("System up-to-date"))
    prefs_tree.get_widget("label90").set_text(_("Updates available"))
    prefs_tree.get_widget("label99").set_text(_("Error"))
    prefs_tree.get_widget("label2").set_text(_("Unknown state"))
    prefs_tree.get_widget("label3").set_text(_("Applying updates"))    
    prefs_tree.get_widget("label1").set_text(_("Ignored updates"))

    prefs_tree.get_widget("checkbutton_dist_upgrade").set_label(_("Include updates which require the installation of new packages or the removal of installed packages"))

    prefs_tree.get_widget("window2").set_icon_from_file("/usr/lib/linuxmint/mintUpdate/icons/base.svg")
    prefs_tree.get_widget("window2").show()
    prefs_tree.get_widget("pref_button_cancel").connect("clicked", pref_cancel, prefs_tree)
    prefs_tree.get_widget("pref_button_apply").connect("clicked", pref_apply, prefs_tree, treeview, statusIcon, wTree)

    prefs_tree.get_widget("button_icon_busy").connect("clicked", change_icon, "busy", prefs_tree, treeview, statusIcon, wTree)
    prefs_tree.get_widget("button_icon_up2date").connect("clicked", change_icon, "up2date", prefs_tree, treeview, statusIcon, wTree)
    prefs_tree.get_widget("button_icon_updates").connect("clicked", change_icon, "updates", prefs_tree, treeview, statusIcon, wTree)
    prefs_tree.get_widget("button_icon_error").connect("clicked", change_icon, "error", prefs_tree, treeview, statusIcon, wTree)
    prefs_tree.get_widget("button_icon_unknown").connect("clicked", change_icon, "unknown", prefs_tree, treeview, statusIcon, wTree)
    prefs_tree.get_widget("button_icon_apply").connect("clicked", change_icon, "apply", prefs_tree, treeview, statusIcon, wTree)

    prefs = read_configuration()

    prefs_tree.get_widget("visible1").set_active(prefs["level1_visible"])
    prefs_tree.get_widget("visible2").set_active(prefs["level2_visible"])
    prefs_tree.get_widget("visible3").set_active(prefs["level3_visible"])
    prefs_tree.get_widget("visible4").set_active(prefs["level4_visible"])
    prefs_tree.get_widget("visible5").set_active(prefs["level5_visible"])
    prefs_tree.get_widget("safe1").set_active(prefs["level1_safe"])
    prefs_tree.get_widget("safe2").set_active(prefs["level2_safe"])
    prefs_tree.get_widget("safe3").set_active(prefs["level3_safe"])
    prefs_tree.get_widget("safe4").set_active(prefs["level4_safe"])
    prefs_tree.get_widget("safe5").set_active(prefs["level5_safe"])
    prefs_tree.get_widget("checkbutton_security_visible").set_active(prefs["security_visible"])
    prefs_tree.get_widget("checkbutton_security_safe").set_active(prefs["security_safe"])

    prefs_tree.get_widget("checkbutton_security_visible").set_label(_("Always show security updates"))
    prefs_tree.get_widget("checkbutton_security_safe").set_label(_("Always select and trust security updates"))

    prefs_tree.get_widget("timer_minutes_label").set_text(_("minutes"))
    prefs_tree.get_widget("timer_hours_label").set_text(_("hours"))
    prefs_tree.get_widget("timer_days_label").set_text(_("days"))
    prefs_tree.get_widget("timer_minutes").set_value(prefs["timer_minutes"])
    prefs_tree.get_widget("timer_hours").set_value(prefs["timer_hours"])
    prefs_tree.get_widget("timer_days").set_value(prefs["timer_days"])

    prefs_tree.get_widget("checkbutton_dist_upgrade").set_active(prefs["dist_upgrade"])

    prefs_tree.get_widget("image_busy").set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(icon_busy, 24, 24))
    prefs_tree.get_widget("image_up2date").set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(icon_up2date, 24, 24))
    prefs_tree.get_widget("image_updates").set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(icon_updates, 24, 24))
    prefs_tree.get_widget("image_error").set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(icon_error, 24, 24))
    prefs_tree.get_widget("image_unknown").set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(icon_unknown, 24, 24))
    prefs_tree.get_widget("image_apply").set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(icon_apply, 24, 24))

    # Blacklisted updates
    treeview_blacklist = prefs_tree.get_widget("treeview_blacklist")
    column1 = gtk.TreeViewColumn(_("Ignored updates"), gtk.CellRendererText(), text=0)
    column1.set_sort_column_id(0)
    column1.set_resizable(True)
    treeview_blacklist.append_column(column1)
    treeview_blacklist.set_headers_clickable(True)
    treeview_blacklist.set_reorderable(False)
    treeview_blacklist.show()

    model = gtk.TreeStore(str)
    model.set_sort_column_id( 0, gtk.SORT_ASCENDING )
    treeview_blacklist.set_model(model)

    if os.path.exists("%s/mintupdate.ignored" % CONFIG_DIR):
        ignored_list = open("%s/mintupdate.ignored" % CONFIG_DIR, "r") 
        for ignored_pkg in ignored_list:     
            iter = model.insert_before(None, None)
            model.set_value(iter, 0, ignored_pkg.strip())
        del model
        ignored_list.close()
    
    prefs_tree.get_widget("toolbutton_add").connect("clicked", add_blacklisted_package, treeview_blacklist)
    prefs_tree.get_widget("toolbutton_remove").connect("clicked", remove_blacklisted_package, treeview_blacklist)
"""

#def add_blacklisted_package(widget, treeview_blacklist):
#def remove_blacklisted_package(widget, treeview_blacklist):

#TOFU:
#def open_history(widget):
def get_history():
    """
    #Set the Glade file
    gladefile = "/usr/lib/linuxmint/mintUpdate/mintUpdate.glade"
    wTree = gtk.glade.XML(gladefile, "window4")
    treeview_update = wTree.get_widget("treeview_history")
    wTree.get_widget("window4").set_icon_from_file("/usr/lib/linuxmint/mintUpdate/icons/base.svg")

    wTree.get_widget("window4").set_title(_("History of updates") + " - " + _("Update Manager"))

    # the treeview
    column1 = gtk.TreeViewColumn(_("Date"), gtk.CellRendererText(), text=1)
    column1.set_sort_column_id(1)
    column1.set_resizable(True)
    column2 = gtk.TreeViewColumn(_("Package"), gtk.CellRendererText(), text=0)
    column2.set_sort_column_id(0)
    column2.set_resizable(True)
    column3 = gtk.TreeViewColumn(_("Old version"), gtk.CellRendererText(), text=2)
    column3.set_sort_column_id(2)
    column3.set_resizable(True)
    column4 = gtk.TreeViewColumn(_("New version"), gtk.CellRendererText(), text=3)
    column4.set_sort_column_id(3)
    column4.set_resizable(True)

    treeview_update.append_column(column1)
    treeview_update.append_column(column2)
    treeview_update.append_column(column3)
    treeview_update.append_column(column4)

    treeview_update.set_headers_clickable(True)
    treeview_update.set_reorderable(False)
    treeview_update.set_search_column(0)
    treeview_update.set_enable_search(True)
    treeview_update.show()

    model = gtk.TreeStore(str, str, str, str) # (packageName, date, oldVersion, newVersion)
    """

    packagesD={}
    
    if (os.path.exists("/var/log/dpkg.log")):
        updates = commands.getoutput("cat /var/log/dpkg.log /var/log/dpkg.log.? 2>/dev/null | egrep \"upgrade\"")
        updates = string.split(updates, "\n")
        i = 0
        for pkg in updates:
            values = string.split(pkg, " ") 
            if len(values) == 6:
                date = values[0]
                time = values[1]
                action = values[2]
                package = values[3]
                oldVersion = values[4]
                newVersion = values[5]

                if action != "upgrade":
                    continue

                if oldVersion == newVersion:
                    continue

                if ":" in package:
                    package = package.split(":")[0]

                """
                iter = model.insert_before(None, None)
                model.set_value(iter, 0, package)
                model.row_changed(model.get_path(iter), iter)
                model.set_value(iter, 1, "%s - %s" % (date, time))
                model.set_value(iter, 2, oldVersion)
                model.set_value(iter, 3, newVersion)
                """
                
                #package name cannot be the key because packages can be updated multiple times

                packagesD[i]={}
                packagesD[i]['name']=package
                packagesD[i]['dateTime']="%s - %s" % (date, time)
                packagesD[i]['oldVer']=oldVersion
                packagesD[i]['newVer']=newVersion
                i = i + 1

    """
    model.set_sort_column_id( 1, gtk.SORT_DESCENDING )
    treeview_update.set_model(model)
    ##del model
    wTree.get_widget("button_close").connect("clicked", history_cancel, wTree)
    """
    return packagesD

#def open_information(widget):
#def label_size_allocate(widget, rect):

"""
def install_kernel():   #def install_kernel(widget, selection, wTree, window): 
    (model, iter) = selection.get_selected()
    if (iter != None):
        (status, version, pkg_version, installed, used, recommended, installable) = model.get_value(iter, 7)
        installed = (installed == "1")
        used = (used == "1")
        installable = (installable == "1")
        if (installed):
            message = _("Are you sure you want to remove the %s kernel?") % version
        else:
            message = _("Are you sure you want to install the %s kernel?") % version
        image = gtk.Image()
        image.set_from_file("/usr/lib/linuxmint/mintUpdate/icons/warning.png")
        d = gtk.MessageDialog(window, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_YES_NO, message)
        image.show()
        d.set_image(image)
        d.set_default_response(gtk.RESPONSE_NO)
        r = d.run()
        d.hide()
        d.destroy()
        if r == gtk.RESPONSE_YES:
            thread = InstallKernelThread(version, wTree, installed)
            thread.start()
            window.hide()
"""
########
#TOFU:
def open_kernels(retControl):       #def open_kernels(widget):
    #global logFile
    #global pid

    """
    gladefile = "/usr/lib/linuxmint/mintUpdate/mintUpdate.glade"
    tree = gtk.glade.XML(gladefile, "window5")
    window = tree.get_widget("window5")
    window.set_title(_("Linux kernels") + " - " + _("Update Manager"))
    window.set_icon_from_file("/usr/lib/linuxmint/mintUpdate/icons/base.svg")
    tree.get_widget("close_button").connect("clicked", kernels_cancel, tree)

    tree.get_widget("label_warning").connect("size-allocate", label_size_allocate)
    tree.get_widget("label_contact").connect("size-allocate", label_size_allocate)
    """
    
    #kernD={}
    
    """
    tree.get_widget("title_warning").set_markup("<span foreground='black' font_weight='bold' size='large'>%s</span>" % _("Warning!"))
    tree.get_widget("label_warning").set_markup(_("The Linux kernel is a critical part of the system. Regressions can lead to lack of networking, lack of sound, lack of graphical environment or even the inability to boot the computer. Only install or remove kernels if you're experienced with kernels, drivers, dkms and you know how to recover a non-booting computer."))
    tree.get_widget("label_available").set_markup("%s" % _("The following kernels are available:"))
    tree.get_widget("label_more_info").set_text(_("More info..."))

    tree.get_widget("label_more_info_1").set_markup("<small>%s</small>" % _("Fixes can represent bug fixes, improvements in hardware support or security fixes."))
    #tree.get_widget("label_more_info_2").set_markup("<small>%s</small>" % _("Security fixes are important when local users represent a potential threat (in companies, libraries, schools or public places for instance) or when the computer can be threatened by remote attacks (servers for instance)."))
    tree.get_widget("label_more_info_3").set_markup("<small>%s</small>" % _("Bug fixes and hardware improvements are important if one of your devices isn't working as expected and the newer kernel addresses that problem."))
    tree.get_widget("label_more_info_4").set_markup("<small>%s</small>" % _("Regressions represent something which worked well and no longer works after an update. It is common in software development that a code change or even a bug fix introduces side effects and breaks something else. Because of regressions it is recommended to be selective when installing updates or newer kernels."))
    tree.get_widget("label_known_fixes").set_text(_("Fixes"))
    tree.get_widget("label_known_regressions").set_text(_("Regressions"))

    tree.get_widget("label_contact").set_markup("<span foreground='#3c3c3c' font_weight='bold' size='small'>%s</span>" % _("Note: Only known fixes and regressions are mentioned. If you are aware of additional fixes or regressions, please contact the development team."))
    """

    if (retControl=="get_texts"):
        return ({
            "title": _("Linux kernels") + " - " + _("Update Manager"),
            "title_warning": _("Warning!"),
            "label_warning": _("The Linux kernel is a critical part of the system. Regressions can lead to lack of networking, lack of sound, lack of graphical environment or even the inability to boot the computer. Only install or remove kernels if you're experienced with kernels, drivers, dkms and you know how to recover a non-booting computer."),
            "label_available": _("The following kernels are available:"),
            "label_more_info": _("More info..."),
            "label_more_info_1": _("Fixes can represent bug fixes, improvements in hardware support or security fixes."),
            "label_more_info_2": _("Security fixes are important when local users represent a potential threat (in companies, libraries, schools or public places for instance) or when the computer can be threatened by remote attacks (servers for instance)."),
            "label_more_info_3": _("Bug fixes and hardware improvements are important if one of your devices isn't working as expected and the newer kernel addresses that problem."),
            "label_more_info_4": _("Regressions represent something which worked well and no longer works after an update. It is common in software development that a code change or even a bug fix introduces side effects and breaks something else. Because of regressions it is recommended to be selective when installing updates or newer kernels."),
            "label_known_fixes": _("Fixes")
        })

    if (retControl!="get_kernels"):
        return (None)


    """
    output = krnD["title"] + "\n"
    + krnD["title_warning"] + "\n"
    + krnD["label_warning"] + "\n"
    + krnD["label_more_info"] + "\n"
    + krnD["label_more_info_1"] + "\n"
    + krnD["label_more_info_2"] + "\n"
    + krnD["label_more_info_3"] + "\n"
    + krnD["label_more_info_4"]
    print (output)
    """

    """
    # the treeview
    treeview_kernels = tree.get_widget("treeview_kernels")

    column1 = gtk.TreeViewColumn(_("Version"), gtk.CellRendererText(), markup=1)
    column1.set_sort_column_id(1)
    column1.set_resizable(True)
    column1.set_expand(True)
    column2 = gtk.TreeViewColumn(_("Loaded"), gtk.CellRendererPixbuf(), pixbuf=2)
    column2.set_sort_column_id(2)
    column2.set_resizable(True)
    column2.set_expand(False)
    column3 = gtk.TreeViewColumn(_("Recommended"), gtk.CellRendererPixbuf(), pixbuf=3)
    column3.set_sort_column_id(3)
    column3.set_resizable(True)
    column3.set_expand(False)
    column4 = gtk.TreeViewColumn(_("Installed"), gtk.CellRendererPixbuf(), pixbuf=4)
    column4.set_sort_column_id(4)
    column4.set_resizable(True)
    column4.set_expand(False)
    column5 = gtk.TreeViewColumn(_("Fixes"), gtk.CellRendererPixbuf(), pixbuf=5)
    column5.set_sort_column_id(5)
    column5.set_resizable(True)
    column5.set_expand(False)
    column6 = gtk.TreeViewColumn(_("Regressions"), gtk.CellRendererPixbuf(), pixbuf=6)
    column6.set_sort_column_id(6)
    column6.set_resizable(True)
    column6.set_expand(False)

    treeview_kernels.append_column(column1)
    treeview_kernels.append_column(column2)
    treeview_ke###rnels.append_column(column3)
    treeview_kernels.append_column(column4)
    treeview_kernels.append_column(column5)
    treeview_kernels.append_column(column6)

    treeview_kernels.set_headers_clickable(True)
    treeview_kernels.set_reorderable(False)
    treeview_kernels.set_search_column(1)
    treeview_kernels.set_enable_search(True)
    treeview_kernels.show()

    model = gtk.TreeStore(str, str, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, object) # (version, label, loaded, recommended, installed, fixes, regressions, values)
    """

    kernelsDD = {}
    kernels = commands.getoutput("/usr/lib/linuxmint/mintUpdate/checkKernels.py | grep \"###\"")
    kernels = kernels.split("\n")
    column = 2
    for kernel in kernels:
        values = string.split(kernel, "###")
        if len(values) == 7:
            status = values[0]
            if status != "KERNEL":
                continue
            (status, version, pkg_version, installed, used, recommended, installable) = values
            installed = (installed == "1")
            used = (used == "1")
            recommended = (recommended == "1")
            installable = (installable == "1")
            label = version

            ####tick = gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintUpdate/icons/tick.png")
            #pix_fixes = gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintUpdate/icons/fixes.png")
            #pix_bugs = gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mintUpdate/icons/regressions.png")

            #iter = model.insert_before(None, None)
            #model.set_value(iter, 0, version)
            #model.set_value(iter, 7, values)
            #model.row_changed(model.get_path(iter), iter)

            #TOFU:
            num_fixes = 0
            num_bugs = 0
            if os.path.exists("/usr/lib/linuxmint/mintUpdate/kernels/%s" % version):
                kernel_file = open("/usr/lib/linuxmint/mintUpdate/kernels/%s" % version)
                lines = kernel_file.readlines()
                #num_fixes = 0
                #num_bugs = 0
                for line in lines:
                    elements = line.split("---")
                    if len(elements) == 4:
                        (prefix, title, url, description) = elements
                        if prefix == "fix":
                            num_fixes += 1
                        elif prefix == "bug":
                            num_bugs += 1
                """
                if num_fixes > 0:
                    model.set_value(iter, 5, pix_fixes)
                if num_bugs > 0:
                    model.set_value(iter, 6, pix_bugs)
                """

            if os.path.exists("/usr/lib/linuxmint/mintUpdate/kernels/versions"):
                kernel_file = open("/usr/lib/linuxmint/mintUpdate/kernels/versions")
                lines = kernel_file.readlines()
                for line in lines:
                    elements = line.split("\t")
                    if len(elements) == 3:
                        (versions_version, versions_tag, versions_upstream) = elements
                        if versions_version == pkg_version:
                            label = "%s (%s)" % (version, versions_upstream.strip())

            """
            if installable and not installed:
                button = gtk.Button(_("Install"))
                button.connect("clicked", install_kernel, version, window, tree, False)

            elif installed and not used:
                button = gtk.Button(_("Remove"))
                button.connect("clicked", install_kernel, version, window, tree, True)

            if used:
                model.set_value(iter, 2, tick)
                label = "<b>%s</b>" % label
            if recommended:
                model.set_value(iter, 3, tick)
            if installed:
                model.set_value(iter, 4, tick)

            model.set_value(iter, 1, label)
            """

            #TOFU:
            kernelsDD.update({version: {
                'label': label,
                'installed': installed,
                'used': used,
                'recommended': recommended,
                'installable': installable,
                'num_fixes': num_fixes,
                'num_bugs': num_bugs
            }})

    """
    treeview_kernels.set_model(model)
    del model

    selection = treeview_kernels.get_selection()
    selection.connect("changed", display_selected_kernel, tree)

    button_install = tree.get_widget("button_install")
    button_install.connect('clicked', install_kernel, selection, tree, window)

    window.show_all()
    """

    return kernelsDD

#TOFU:
def get_kernel_info(version):          #def display_selected_kernel(selection, wTree):
    """
    button_install = wTree.get_widget("button_install")
    button_install.set_sensitive(False)
    button_install.set_tooltip_text("")
    """

    try:
        """
        scrolled_fixes = wTree.get_widget("scrolled_fixes")
        scrolled_regressions = wTree.get_widget("scrolled_regressions")
        for child in scrolled_fixes.get_children():
            scrolled_fixes.remove(child)
        for child in scrolled_regressions.get_children():
            scrolled_regressions.remove(child)
        (model, iter) = selection.get_selected()
        if (iter != None):
        """

        if (version != None):
            """
            (status, version, pkg_version, installed, used, recommended, installable) = model.get_value(iter, 7)
            installed = (installed == "1")
            used = (used == "1")
            installable = (installable == "1")
            if installed:
                button_install.set_label(_("Remove the %s kernel") % version)
                if used:
                    button_install.set_tooltip_text(_("This kernel cannot be removed because it is currently in use."))
                else:
                    button_install.set_sensitive(True)
            else:
                button_install.set_label(_("Install the %s kernel" % version))
                if not installable:
                    button_install.set_tooltip_text(_("This kernel is not installable."))
                else:
                    button_install.set_sensitive(True)
            """

            kernelInfoD = {
                'version':  version,
                'bugsAD':   [],  
                'fixesAD':  []
            }
            
            if os.path.exists("/usr/lib/linuxmint/mintUpdate/kernels/%s" % version):
                kernel_file = open("/usr/lib/linuxmint/mintUpdate/kernels/%s" % version)
                lines = kernel_file.readlines()
                """
                fixes_box = gtk.Table()
                fixes_box.set_row_spacings(3)
                bugs_box = gtk.Table()
                bugs_box.set_row_spacings(3)
                """

                #num_fixes = 0          #not needed - length of fixesAD = num_fixes
                #num_bugs = 0           #not needed - length of bugsAD = num_bugs

                for line in lines:
                    elements = line.split("---")
                    if len(elements) == 4:
                        (prefix, title, url, description) = elements
                        """
                        link = gtk.Label()
                        link.set_markup("<a href='%s'>%s</a>" % (url.strip(), title.strip()))
                        link.set_alignment(0, 0.5);
                        description_label = gtk.Label()
                        """
                        description = description.strip()
                        description = re.sub(r'CVE-(\d+)-(\d+)', r'<a href="http://cve.mitre.org/cgi-bin/cvename.cgi?name=\g<0>">\g<0></a>', description)
                        description = description.strip()
                        
                        """
                        description_label.set_markup("%s" % description.strip())
                        description_label.set_alignment(0, 0.5);
                        """
                        if prefix == "fix":
                            #fixes_box.attach(link, 0, 1, num_fixes, num_fixes+1, xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=3, ypadding=0)
                            #fixes_box.attach(description_label, 1, 2, num_fixes, num_fixes+1, xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
                            kernelInfoD['fixesAD'].append([{
                                'title':        title,
                                'url':          url,
                                'desc':         description
                            }]) 
                            #num_fixes += 1
                        elif prefix == "bug":
                            #bugs_box.attach(link, 0, 1, num_bugs, num_bugs+1, xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=3, ypadding=0)
                            #bugs_box.attach(description_label, 1, 2, num_bugs, num_bugs+1, xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=0, ypadding=0)
                            kernelInfoD['bugsAD'].append([{
                                'title':        title,
                                'url':          url,
                                'desc':         description
                            }])                            
                            #num_bugs += 1

                """
                scrolled_fixes.add_with_viewport(fixes_box)
                scrolled_regressions.add_with_viewport(bugs_box)
                fixes_box.show_all()
                bugs_box.show_all()
                """

            return kernelInfoD

    except Exception, detail:
        print detail

#def open_help(widget):
#def open_rel_upgrade(widget):
#def open_about(widget):
#def quit_cb(widget, window, vpaned, data = None):
#def popup_menu_cb(widget, button, time, data = None):
#def close_window(window, event, vpaned):
#def hide_window(widget, window):
#def activate_icon_cb(widget, data, wTree):
#def save_window_size(window, vpaned):

def clean_l10n_short_description(description):
        try:
            # Remove "Description-xx: " prefix
            value = re.sub(r'Description-(\S+): ', r'', description)
            # Only take the first line and trim it
            value = value.split("\n")[0].strip()
            # Capitalize the first letter
            value = value[:1].upper() + value[1:]
            # Add missing punctuation
            if len(value) > 0 and value[-1] not in [".", "!", "?"]:
                value = "%s." % value
            # Replace & signs with &amp; (because we pango it)
            value = value.replace('&', '&amp;')

            return value
        except Exception, detail:
            print detail
            return description

def clean_l10n_description(description):
        try:
            lines = description.split("\n")
            value = ""
            num = 0
            newline = False
            for line in lines:
                line = line.strip()
                if len(line) > 0:
                    if line == ".":
                        value = "%s\n" % (value)
                        newline = True
                    else:
                        if (newline):
                            value = "%s%s" % (value, line.capitalize())
                        else:
                            value = "%s %s" % (value, line)
                        newline = False
                    num += 1
            value = value.replace("  ", " ").strip()
            # Capitalize the first letter
            value = value[:1].upper() + value[1:]
            # Add missing punctuation
            if len(value) > 0 and value[-1] not in [".", "!", "?"]:
                value = "%s." % value
            return value
        except Exception, detail:
            print detail
            return description

def l10n_descriptions(package_update):
        package_name = package_update.name.replace(":i386", "").replace(":amd64", "")
        if package_descriptions.has_key(package_name):
            package_update.short_description = package_short_descriptions[package_name]
            package_update.description = package_descriptions[package_name]


#def display_selected_package(selection, wTree):
#def switch_page(notebook, page, page_num, Wtree, treeView):
#def celldatafunction_checkbox(column, cell, model, iter):
#def toggled(renderer, path, treeview, statusbar, context_id):

def size_to_string(size):
    strSize = str(size) + _("B")
    if (size >= 1024):
        strSize = str(size / 1024) + _("KB")
    if (size >= (1024 * 1024)):
        strSize = str(size / (1024 * 1024)) + _("MB")
    if (size >= (1024 * 1024 * 1024)):
        strSize = str(size / (1024 * 1024 * 1024)) + _("GB")
    return strSize

#def setVisibleColumn(checkmenuitem, column, configName):
#def setVisibleDescriptions(checkmenuitem, treeView, statusIcon, wTree, prefs):
#def menuPopup(widget, event, treeview_update, statusIcon, wTree):
#def menuPopup(widget, event, treeview_update, statusIcon, wTree):

def add_to_ignore_list(pkg):        #def add_to_ignore_list(widget, treeview_update, pkg, statusIcon, wTree): 
    os.system("echo \"%s\" >> %s/mintupdate.ignored" % (pkg, CONFIG_DIR))
    #refresh = RefreshThread(treeview_update, statusIcon, wTree)
    #refresh.start()

#TOFU:


def get_ignore_list():
    if hasATTR(get_ignore_list, 'ignore_listA'):
        ignored_list=get_ignore_list.ignore_listA
    else:
        ignored_list=[]
    if os.path.exists("%s/mintupdate.ignored" % CONFIG_DIR):
        blacklist_file = open("%s/mintupdate.ignored" % CONFIG_DIR, "r")
        for blacklist_line in blacklist_file:
            ignored_list.append(blacklist_line.strip())
        blacklist_file.close()

    get_ignore_list.ignore_listA=ignored_list
    
    return ignored_list
    
#TOFU:
def exec_log(cmd, log):

    p = Popen(cmd, shell=True, stderr=STDOUT, stdout=PIPE)
    #p = subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    #p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
 
    ## But do not wait till netstat finish, start displaying output immediately ##
    while True:
        out = p.stdout.read(1)
        if out == '' and p.poll() != None:
            break
        if out != '': 
            sys.stdout.write(out)
            sys.stdout.flush()
            log.writelines(out)
            #log.flush()

    log.flush()
    return p.wait()

#TOFU:
class Cli_handler:
    def __init__(self, log):   #, args):
        #global log
        self.log=log
        #update_args(args)
        self.args=type('', (), {})()    #empty object
        self.prefs=type('', (), {})()    #empty object

    def set_args(self, args):
        self.args=args

    def set_prefs(self, prefs):
        self.prefs=prefs

    def refresh(self):
        #ret=exec_log("sudo apt-get "+("","-s ")[self.args.simulate]+" update", self.log)       #Maybe in the future ;)
        if (self.args.simulate):
            print _("'apt-get update' does not support simulation, so exiting...")
            return

        #ret1=exec_log("sudo apt-get check", self.log)
        ret2=exec_log("sudo apt-get update", self.log)
        #if (ret1==0 and ret2==0):
        if (ret2==0):
            print _("Refresh successful.")
        else:
            print _("Refresh failed.")

    def check_update(self):
        refresh = RefreshThread()
        refresh.set_args(self.args)
        refresh.run()

    def update(self):
        refresh = RefreshThread()
        refresh.set_args(self.args)
        packagesA=refresh.run()
        install = InstallThread()
        install.set_args(self.args)
        install.set_packages(packagesA)
        install.run()

    def install(self):
        if (self.args.debug):
            print "Groups:"
            print self.args.groupsA
        refresh = RefreshThread()
        refresh.set_args(self.args)
        packagesA=refresh.run()

        install = InstallThread()
        install.set_args(self.args)
        install.set_packages(packagesA)
        install.run()

    def install_remove_kernel(self):
        if (self.args.debug):
            print "Kernels:"
            print self.args.kernel_name

        krnDD=open_kernels("get_kernels")

        """
        if (len(self.args.kernelsA) != len(set(self.args.kernelsA))):
            duplicates = "'"+"', '".join(set([x for x in self.args.kernelsA if self.args.kernelsA.count(x) > 1]))+"'"
            print (_("Error: Duplicate kernels specified: ") + duplicates)
            sys.exit(-1)
        """
     
        #print krnDD.keys()
        not_subsetS = set([self.args.kernel_name]) - set(krnDD.keys())
        if (len(not_subsetS)):
            print (_("Error: Unknown kernel specified: '") + "', '".join(not_subsetS)+"'")
            sys.exit(-2)

        removeF=self.args.command=='remove'
        install_kernel = InstallKernelThread(self.args.kernel_name, removeF)
        install_kernel.set_args(self.args)
        install_kernel.run()
        
    def show_kernels(self):
        textsD=open_kernels("get_texts")
        
        output = textsD["title"] + "\n" \
        + textsD["title_warning"] + "\n" \
        + textsD["label_warning"] + "\n\n" \
        + textsD["label_more_info"] + "\n" \
        + textsD["label_more_info_1"] + "\n" \
        + textsD["label_more_info_2"] + "\n\n" \
        + textsD["label_more_info_3"] + "\n\n" \
        + textsD["label_more_info_4"]
        print (output)

        print ""
        krnDD=open_kernels("get_kernels")
        #print krnDD

        pkgValD={
            'version':          _("Kernel version"),
            'loaded':           _("Loaded"),
            'recommended':      _("Recommended"),
            'installed':        _("Installed"),
            'fixes':            _("Fixes"),
            'regressions':      _("Regressions")
        }

        pkgMaxLenD={
            'version':         len(pkgValD['version'])
        }

        for version in krnDD:
            pkgMaxLenD['version']=max(pkgMaxLenD['version'], len(krnDD[version]['label']))

        pkgFrmAD=[
            {'version':         "{:<"+str(pkgMaxLenD['version'])+"s}"},
            {'loaded':          " {:^9s}"},
            {'recommended':     " {:^12s}"},
            {'installed':       " {:^9s}"},
            {'fixes':           " {:^7s}"},
            {'regressions':     " {:^10s}"}
        ]

        print_formatted(pkgFrmAD, pkgValD)

        #Yes/No right alignment formatting:
        yes=_("Yes")
        no=_("No")
        maxLen=max(len(yes), len(no))
        yes=("{:>"+str(maxLen)+"s}").format(yes)
        no=("{:>"+str(maxLen)+"s}").format(no)
        
        #version loaded recommended isntalled fixes regressions
        for version in sorted(krnDD):
            #print krnDD[key]
            pkgValD={
                'version':          krnDD[version]['label'],
                'loaded':           (no, yes)[krnDD[version]['used']],
                'recommended':      (no, yes)[krnDD[version]['recommended']],
                'installed':        (no, yes)[krnDD[version]['installed']],
                'fixes':            str((krnDD[version]['num_fixes'],"")[krnDD[version]['num_fixes']==0]),
                'regressions':      str((krnDD[version]['num_bugs'],"")[krnDD[version]['num_bugs']==0])
            }

            print_formatted(pkgFrmAD, pkgValD)

            if (self.args.verbosity >= 1):
                kernelInfoD=get_kernel_info(version)
                #print kernelInfoD
                if (len(kernelInfoD['fixesAD'])):
                    print (_("Fixes")+":")
                    for i, fixAD in enumerate(kernelInfoD['fixesAD']):
                        print (str(i+1)+": "+_("Title")+": "+fixAD[0]['title'])
                        print ("   "+_("Description")+": "+fixAD[0]['desc'])
                        if (self.args.verbosity >= 2):
                            print ("   "+_("URL")+": "+fixAD[0]['url'])

                if (len(kernelInfoD['bugsAD'])):
                    print (_("Bugs")+":")
                    for i, bugAD in enumerate(kernelInfoD['bugsAD']):
                        print (str(i+1)+": "+_("Title")+": "+bugAD[0]['title'])
                        print ("   "+_("Description")+": "+bugAD[0]['desc'])
                        if (self.args.verbosity >= 2):
                            print ("   "+_("URL")+": "+bugAD[0]['url'])

    #def list_p(self):
    #    print 'list'

    def show_options(self):
        if (self.args.debug): 
            print self.prefs

        print ("Linux Mint Update manager preferences:\n")

        pkgFrmAD=[                              #Formats
            {'level':   "{:^6s}"},              #level
            {'desc':    [58," {:<58s}"]},       #description
            {'tested':  " {:<8s}"},             #tested Y/N
            {'origin':  " {:<10s}"},
            {'safe':    " {:^8s}"},
            {'visible': " {:^8s}"}              #" {:<.3s}"
        ]

        pkgValD={                               #Header
            'level':    "Level",
            'desc':     "Description",
            'tested':   "Tested?",
            'origin':   "Origin",
            'safe':     "Safe?",
            'visible':  "Visible?"
        }

        print_formatted_multiline(pkgFrmAD, pkgValD)  

        for x in range(1, 6):
            pkgValD={
                'level':    str(x),
                'desc':     self.prefs["level"+str(x)+"_desc"],
                'tested':   ("No", "Yes")[self.prefs["level"+str(x)+"_tested"]],
                'origin':   self.prefs["level"+str(x)+"_origin"],
                'safe':     "["+(" ","X")[self.prefs["level"+str(x)+"_safe"]]+"]",
                'visible':  "["+(" ","X")[self.prefs["level"+str(x)+"_visible"]]+"]"
            }

            print_formatted_multiline(pkgFrmAD, pkgValD)


        print ("")
        print ("["+(" ","X")[self.prefs["security_visible"]]+"] - "+self.prefs["checkbutton_security_visible"])
        print ("["+(" ","X")[self.prefs["security_safe"]]+"] - "+self.prefs["checkbutton_security_safe"])
        print ("")
        print ("["+(" ","X")[self.prefs["dist_upgrade"]]+"] - "+self.prefs["checkbutton_dist_upgrade"])
        print ("")
        print (_("To change options, use '")+self.args.prog+_(" set-option --help' to see the names of options."))
        print ("")

    def set_option(self):
        trueA=['1', 'true', 'TRUE', 'True']
        falseA=['0', 'false', 'FALSE', 'False']

        value=None
        if (self.args.value in trueA): value=True
        if (self.args.value in falseA): value=False

        if (value==None):
            print _("Error: value needs to be either 0, 1, true or false.")
        else:
            if (self.prefs[self.args.option]==value):
                print (_("Option '")+self.args.option+_("' is already set to '")+self.args.value+"', no change.")
            else:
                self.prefs[self.args.option]=value
                pref_apply_CLI(self.prefs)
                print (_("Option '")+self.args.option+_("' is now set to '")+self.args.value+"'.")

    def show_ignored(self):
        ignore_listA=get_ignore_list()
        if (not len(ignore_listA)):
            print _("Ignore list is empty.")
        else:
            print _("Ignore list:")
            for pkg in ignore_listA:
                print pkg

    def add_ignored(self):
        ignore_listA=get_ignore_list()
        duplicatesA = list(set(self.args.ignoreA) & set(ignore_listA))
        if (len(duplicatesA)):
            print (_("Error: Package group(s) specified already in ignore list:")+" '" + "', '".join(duplicatesA)+"'")
            sys.exit(-4)

        refresh = RefreshThread()
        refresh.set_args(self.args)
        groupsA=refresh.run()
        not_subsetS = set(self.args.ignoreA) - set(groupsA)
        if (len(not_subsetS)):
            print (_("Error: Package group(s) specified not in refresh list:")+" '" + "', '".join(not_subsetS)+"'")
            sys.exit(-5)

        for pkg in self.args.ignoreA:
            add_to_ignore_list(pkg)

        print _("Ignore list updated.")


    def remove_ignored(self):
        ignore_listA=get_ignore_list()
        #print self.args.ignoreA
        #print ignore_listA
        not_subsetS = set(self.args.ignoreA) - set(ignore_listA)
        if (len(not_subsetS)):
            print (_("Error: Package group(s) specified not in ignore list:")+" '" + "', '".join(not_subsetS)+"'")
            sys.exit(-3)

        ignore_listA=list(set(ignore_listA)-set(self.args.ignoreA))
        #print ignore_listA
        save_ignore_list(ignore_listA)
        print _("Ignore list saved.")


    def show_history(self):
        print (_("History of updates:"))
        packagesD=get_history()

        pkgValD={
            'name':     _("Package name"),
            'dateTime': _("Date/Time"),            #Date + Time (string)
            'oldVer':   _("Old version"),          #current version of package
            'newVer':   _("New version")           #new version of package
        }

        pkgMaxLenD={
            'name':         len(pkgValD['name']),
            'dateTime':     len(pkgValD['dateTime']),
            'oldVer':       len(pkgValD['oldVer']),
            'newVer':       len(pkgValD['newVer'])
        }

        for package in packagesD.keys():
            #pkgMaxLenD['name']=max(pkgMaxLenD['name'], len(package))
            pkgMaxLenD['name']=max(pkgMaxLenD['name'], len(packagesD[package]['name']))
            pkgMaxLenD['dateTime']=max(pkgMaxLenD['dateTime'], len(packagesD[package]['dateTime']))
            pkgMaxLenD['oldVer']=max(pkgMaxLenD['oldVer'], len(packagesD[package]['oldVer']))
            pkgMaxLenD['newVer']=max(pkgMaxLenD['newVer'], len(packagesD[package]['newVer']))
                                                                      

        pkgFrmAD=[
            {'dateTime': "{:<"+str(pkgMaxLenD['dateTime'])+"s}"}, #package date/time
            {'name':     " {:>"+str(pkgMaxLenD['name'])+"s}"},     #package name
            {'newVer':   " {:>"+str(pkgMaxLenD['newVer'])+"s}"},   #current version of package
            {'oldVer':   " {:>"+str(pkgMaxLenD['oldVer'])+"s}"}    #new version of package  
        ]    

        print_formatted(pkgFrmAD, pkgValD)

        #for package in packagesD.keys():
        for package in sorted(packagesD.keys(), key=lambda x:(packagesD[x]['dateTime']), reverse=True):
            pkgValD={
                'dateTime':     packagesD[package]['dateTime'],
                'name':         packagesD[package]['name'],
                'newVer':       packagesD[package]['newVer'],
                'oldVer':       packagesD[package]['oldVer']
            }    
            print_formatted(pkgFrmAD, pkgValD)


def main(argv):

    #app_hidden
    global log
    global logFile
    global pid
    #global statusbar
    #global context_id

    #app_hidden = True

    # prepare the log
    pid = os.getpid()
    logdir = "/tmp/mintUpdate/"

    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
        os.system("chmod a+rwx " + logdir)

    log = tempfile.NamedTemporaryFile(prefix = logdir, delete=False)
    logFile = log.name
    try:
        os.system("chmod a+rw %s" % log.name)
    except Exception, detail:
        print detail

    log.writelines("++ Launching mintUpdate CLI \n")
    log.flush()

    if (not os.path.exists(CONFIG_DIR)):
        os.system("mkdir -p %s" % CONFIG_DIR)
        log.writelines("++ Creating %s directory\n" % CONFIG_DIR)
        log.flush()

    try:
        prefs = read_configuration()

        #TOFU:
        #MAIN:

        version='v0.1'
        cli=Cli_handler(log)
        cli.set_prefs(prefs)
        prog=os.path.basename(sys.argv[0])
        parser = argparse.ArgumentParser(description='Linux Mint Update manager CLI '+version+', (c) 2015 Jan Andrejkovic', prog=prog)
        parser.set_defaults(prog=prog)

        parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
        parser.add_argument('--version', action='version', version='%(prog)s version: '+version+', (c) Jan Andrejkovic 2015')
        parser.add_argument('-v', '--verbosity', action='count', help=_('increase output verbosity'))
        #parser.add_argument('-s', '--simulate', '--just-print', '--dry-run', '--recon', '--no-act', action='store_true', help=_('Passed to apt-get - No action; perform a simulation of events that would occur but do not actually change the system.'))
        parser.add_argument('-s', '--simulate', action='store_true', help=_('Passed to apt-get = No action; perform a simulation of events that would occur but do not actually change the system.'))
        subparsers = parser.add_subparsers(help=_('commands'))

        parser_refresh_sources = subparsers.add_parser('refresh', help=_('calls apt-get update to refresh package sources'))
        parser_refresh_sources.set_defaults(func=cli.refresh)

        parser_check_update = subparsers.add_parser('list', help=_('display all Linux Mint updates'))
        parser_check_update.set_defaults(func=cli.check_update)

        parser_update = subparsers.add_parser('update', help=_('update all available groups of packages'))
        parser_update.set_defaults(func=cli.update)

        parser_install = subparsers.add_parser('install', help=_('install specified group(s) of packages'))
        parser_install.add_argument('groupsA', metavar='package_group', nargs='+', help=_('name of the package group'))
        parser_install.set_defaults(func=cli.install)

        #parser_list_p = subparsers.add_parser('list', help='list all install pacakges in the system (dpkg -l)')
        #parser_list_p.set_defaults(func=cli.list_p)

        parser_show_kernels = subparsers.add_parser('show-kernels', help=_('display available and installed kernels'))
        parser_show_kernels.set_defaults(func=cli.show_kernels)

        parser_install_kernel = subparsers.add_parser('install-kernel', help=_('install specified kernel'))
        parser_install_kernel.add_argument('kernel_name', type=str, help=_('name of kernel to be installed'))
        parser_install_kernel.set_defaults(func=cli.install_remove_kernel, command='install')

        parser_remove_kernel = subparsers.add_parser('remove-kernel', help='remove specified kernel')
        parser_remove_kernel.add_argument('kernel_name', type=str, help=_('name of kernel to be removed'))
        parser_remove_kernel.set_defaults(func=cli.install_remove_kernel, command='remove')

        parser_show_options = subparsers.add_parser('show-options', help=_('show mintupdate options'))
        parser_show_options.set_defaults(func=cli.show_options)

        parser_set_option = subparsers.add_parser('set-option', help=_('set mintupdate option'), epilog="Example: "+prog+' set-option level4_visible 1')
        parser_set_option.add_argument('option', type=str, choices=['security_visible', 'security_safe', 'dist_upgrade', 
                                        'level1_visible', 'level2_visible', 'level3_visible', 'level4_visible', 'level5_visible',
                                        'level1_safe', 'level2_safe', 'level3_safe', 'level4_safe', 'level5_safe'], help=_('name of the option to set'))
        parser_set_option.add_argument('value', type=str, help='option value - 0/1 or true/false') #Example: %(prog) set-option level4_visible 1')
        parser_set_option.set_defaults(func=cli.set_option)

        parser_show_ignored = subparsers.add_parser('show-ignored', help=_('shows ignored package group(s)'))
        parser_show_ignored.set_defaults(func=cli.show_ignored)

        parser_add_ignored = subparsers.add_parser('add-ignored', help=_('add ignored package group(s)'))
        parser_add_ignored.add_argument('ignoreA', metavar='package_group', nargs='+', help='name of the package group(a)')
        parser_add_ignored.set_defaults(func=cli.add_ignored, command='add-ignored', supressRefreshDisplay=True)

        parser_remove_ignored = subparsers.add_parser('remove-ignored', help=_('remove ignored package group(s)'))
        parser_remove_ignored.add_argument('ignoreA', metavar='package_group', nargs='+', help=_('name of the package group(a)'))
        parser_remove_ignored.set_defaults(func=cli.remove_ignored)

        parser_show_history = subparsers.add_parser('show-history', help=_('shows history of updates'))
        parser_show_history.set_defaults(func=cli.show_history)

        args = parser.parse_args(argv)
        cli.set_args(args)
        #args.func(args)
        args.func()     #calling cli.command

        if (args.verbosity==None): args.verbosity=0

        if (args.debug):
            print "Args: "
            pprint (vars(args))
            print "Verbosity: "+str(args.verbosity)

        if (args.debug):
            print 'Logfile: '+logFile+':'
            print open(logFile, "r").read()

    except Exception, detail:
        print detail
        log.writelines("-- Exception occured in main thread: " + str(detail) + "\n")
        log.flush()
        log.close()
        raise           #For debug purpose #TOFU:

if __name__ == "__main__":
    if (len(sys.argv[1:]) >0 ):
        main(sys.argv[1:])
    else:
        #args='remove-ignored bind9'
        #args='add-ignored bind9'
        #args='show-ignored'
        #args='--debug show-options'
        #args='list'
        #args='show-options'
        #args='-v list'
        #args='-vv show-kernels'
        #args='list'
        args='--help'
        main(args.split())
 
