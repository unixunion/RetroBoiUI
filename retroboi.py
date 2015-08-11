#!/usr/bin/env python
# encoding: utf-8

'''

RetroBoi is a simple light weight python interface for retropi like projects.

Configuring

1. Set the romdir variable
2. Add a default.cfg in each "system" directory within the romdir. e.g. romdir/snes/default.cfg

[default]
command = /usr/bin/retroarch -L /path/to/libretro.core -c /path/to/global.conf --appendconfig /path/to/megadrive.cfg %s

%s is passed the rom path and filename (sh_escaped)

'''

import os
import subprocess
import logging
logging.basicConfig(filename='retroboi.log',level=logging.DEBUG)
import ConfigParser
import npyscreen, curses

# variables

# top level romdir with SYSTEM subdirs
romdir = '/Users/keghol/Development/retroboi/roms'

# button mappings for interface ( arrow keys for nav assumed )
a_button = "a"
b_button = "b"
start_button = "o"
select_button = "i"

# the config file name to look for per SYSTEM romdir
system_config_file = "default.cfg"

# State vars
# place to store callback functions
cb = {}
systems = []

# main app class
class RetroBoiApp(npyscreen.NPSAppManaged):
    name = "Main"
    def onStart(self):
        logging.debug("starting RetroBoiApp")
        for system in systems:
            logging.debug("adding form for system: %s" % system)
            self.addForm(system.upper(), MainForm, name=system)

    def change_form(self, name):
        logging.debug("switching to system %s" % name)
        self.switchForm(name)
        self.resetHistory()

    def onCleanExit(self):
        npyscreen.notify_wait("Goodbye!")

class MainForm(npyscreen.FormWithMenus):

    def create(self):
        # load system config
        logging.debug("requsting system config for %s" % self.name)
        self.config = getSystemConfig(self.name)

        logging.debug("adding %s roms to UI" % self.name)
        for rom in getSystemRoms(self.name):
            # setup the callback function with the command
            cb[rom] = runGame(self.config.get('default', 'command') % sh_escape(getSystemRomDir(self.name) + "/" + rom))
            self.add(RomButtonPress, name=rom, when_pressed_function=cb[rom])

        # input handler
        logging.debug("binding %s to system_select" % select_button)
        self.add_handlers({select_button: self.change_forms})

        self.m1 = self.new_menu(name="Menu", shortcut=start_button)# TODO FIXME COMPLAIN ABOUT THIS!
        self.m1.addItemsFromList([
            ("Shutdown", self.shutdown, "e"),
            ("Reboot", self.reboot, "e"),
            ("Exit Application", self.exit_application, "é"),
        ])

    def on_ok(self):
        # Exit the application if the OK button is pressed.
        self.parentApp.switchForm(None)

    def change_forms(self, *args, **keywords):
        if systems.index(self.name) < len(systems)-1:
            change_to = systems[systems.index(self.name)+1].upper()
            logging.debug("setting system to %s" % change_to)
        else:
            change_to = systems[0].upper()
            logging.debug("setting system to %s" % change_to)

        self.parentApp.change_form(change_to)

    def shutdown(self):
        logging.debug("shutdown")
        curses.beep()

    def reboot(self):
        logging.debug("reboot")
        curses.beep()

    def exit_application(self):
        logging.debug("quit")
        curses.beep()
        self.parentApp.setNextForm(None)
        self.editing = False
        self.parentApp.switchFormNow()


class RomButtonPress(npyscreen.wgbutton.MiniButton):

    def __init__(self, screen, when_pressed_function=None, *args, **keywords):
        super(RomButtonPress, self).__init__(screen, *args, **keywords)
        self.when_pressed_function = when_pressed_function

    def set_up_handlers(self):
        super(RomButtonPress, self).set_up_handlers()

        self.handlers.update({
                curses.ascii.NL: self.h_toggle,
                curses.ascii.CR: self.h_toggle,
                a_button: self.h_toggle,
            })

    def destroy(self):
        self.when_pressed_function = None
        del self.when_pressed_function

    def h_toggle(self, ch):
        self.value = True
        self.display()
        if self.when_pressed_function:
            self.when_pressed_function()
        else:
            self.whenPressed()
        self.value = False
        self.display()

    def whenPressed(self):
        pass

"""
return the roms in the SYSTEM directory
"""
def getSystemRoms(name):
    roms = []
    tmpdir = "%s/%s" % (romdir, name)
    logging.debug("searching for roms in %s" % tmpdir)
    for dirname, dirnames, filenames in os.walk(tmpdir):
        for f in filenames:
            logging.debug("found rom: %s" % f)
            roms.append(f)
        break
    logging.debug("returning roms list %s" % roms)
    return roms

"""
return the full path to the SYSTEM
"""
def getSystemRomDir(name):
    tmpdir = "%s/%s" % (romdir, name)
    return tmpdir

"""
return a instance of ConfigParser with the config populated
"""
def getSystemConfig(name):
    tmpdir = "%s/%s/%s" % (romdir, name, system_config_file)
    logging.debug("getting config file: %s" % tmpdir)
    config = ConfigParser.ConfigParser()
    config.read(tmpdir)
    return config

"""
create a tmp function and return it ( un-invoked ) for later calling
"""
def runGame(emulator):
    """
    create a tmp function and return a pointer
    """
    def tmp():
        try:
            logging.debug("calling process %s" % emulator)
            subprocess.call(emulator, shell=True)
        except:
            npyscreen.notify_wait("Error launching game, check config")
    return tmp

"""
escape slashes, spaces and whatnot
"""
def sh_escape(s):
   return s.replace("(","\\(").replace(")","\\)").replace(" ","\\ ")


if __name__ == '__main__':
    logging.info("Starting")
    # scan for systems
    for dirname, dirnames, filenames in os.walk(romdir):
        print("adding systems in: " + dirname )
        for d in dirnames:
            print(d)
            systems.append(d)
        break

    logging.info("Detected Systems: " + str(systems))

    App = RetroBoiApp()
    App.run()
